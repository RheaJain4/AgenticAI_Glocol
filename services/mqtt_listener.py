"""
ShakeAlert MQTT Listener
=========================
Subscribes to the ShakeAlert MQTT broker for real-time earthquake alerts.
Parses XML messages, filters by magnitude threshold, stores in DynamoDB,
and triggers the agent pipeline via callback.

Based on the reference implementation in alert-shakealert-sript (Copy).py.txt
"""

import ssl
import sys
import time
import threading
import logging
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER_URL,
    MQTT_BROKER_PORT,
    MQTT_TOPIC,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_CLIENT_ID,
    MQTT_TLS_ENABLED,
    MQTT_MESSAGE_TIMEOUT,
    MAGNITUDE_THRESHOLD,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MQTTListener] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# XML Message Parser
# ---------------------------------------------------------------------------
def parse_shakealert_xml(xml_message: str) -> Optional[Dict[str, Any]]:
    """
    Parse a ShakeAlert XML message into a dictionary.

    Expected XML fields: orig_time, mag, lat, lon, depth, version (attribute).
    Returns None if parsing fails or required fields are missing.
    """
    try:
        root = ET.fromstring(xml_message)
        fields = {
            "orig_time": root.findtext(".//orig_time"),
            "magnitude": root.findtext(".//mag"),
            "latitude": root.findtext(".//lat"),
            "longitude": root.findtext(".//lon"),
            "depth": root.findtext(".//depth"),
            "version": root.attrib.get("version", "0"),
        }

        # Validate required fields
        if not fields["orig_time"]:
            logger.warning("XML message missing orig_time — skipping.")
            return None

        # Convert numeric fields
        try:
            fields["magnitude"] = float(fields["magnitude"]) if fields["magnitude"] else None
            fields["latitude"] = float(fields["latitude"]) if fields["latitude"] else None
            fields["longitude"] = float(fields["longitude"]) if fields["longitude"] else None
            fields["depth"] = float(fields["depth"]) if fields["depth"] else None
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse numeric fields: %s", e)
            return None

        return fields

    except ET.ParseError as e:
        logger.error("XML ParseError: %s | Raw: %s", e, xml_message[:200])
        return None


# ---------------------------------------------------------------------------
# ShakeAlert MQTT Listener
# ---------------------------------------------------------------------------
class ShakeAlertMQTTListener:
    """
    Connects to the ShakeAlert MQTT broker, receives earthquake alerts,
    and triggers the pipeline when a valid alert above the magnitude
    threshold is received.
    """

    def __init__(
        self,
        on_alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_store_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
    ):
        """
        Args:
            on_alert_callback: Called when a valid alert above threshold is received.
                               Receives the parsed alert dict.
            on_store_callback: Called to persist every valid (deduplicated) alert.
                               Receives (topic, raw_xml, parsed_fields).
        """
        self._on_alert = on_alert_callback
        self._on_store = on_store_callback
        self._last_message_time: float = time.time()
        self._dedup_cache: Dict[str, Dict[str, Any]] = {}
        self._dedup_ttl: int = 900  # 15 minutes, matching reference script
        self._running: bool = False
        self._client: Optional[mqtt.Client] = None
        self._watchdog_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------
    def _is_duplicate(self, fields: Dict[str, Any]) -> bool:
        """
        Check if this alert is a duplicate (same orig_time + unchanged fields).
        Cleans up stale cache entries older than _dedup_ttl.
        """
        now = time.time()
        orig_time = fields["orig_time"]

        # Cleanup stale entries
        stale_keys = [
            k for k, v in self._dedup_cache.items()
            if now - v["last_seen"] > self._dedup_ttl
        ]
        for key in stale_keys:
            logger.debug("Removing stale cache entry for OrigTime %s", key)
            del self._dedup_cache[key]

        # Build comparison state (core fields only)
        current_state = {
            "magnitude": fields["magnitude"],
            "latitude": fields["latitude"],
            "longitude": fields["longitude"],
            "depth": fields["depth"],
        }

        entry = self._dedup_cache.get(orig_time)
        if entry and entry["fields"] == current_state:
            # Same event, same data — duplicate
            self._dedup_cache[orig_time]["last_seen"] = now
            logger.info(
                "Duplicate alert for OrigTime %s (Version %s) — skipping.",
                orig_time, fields["version"],
            )
            return True

        # New or updated event
        self._dedup_cache[orig_time] = {"fields": current_state, "last_seen": now}
        return False

    # ------------------------------------------------------------------
    # MQTT Callbacks
    # ------------------------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info("Connected to MQTT broker at %s:%d", MQTT_BROKER_URL, MQTT_BROKER_PORT)
            client.subscribe(MQTT_TOPIC, qos=0)
            logger.info("Subscribed to topic: %s", MQTT_TOPIC)
        else:
            logger.error("MQTT connection failed (rc=%d)", rc)

    def _on_message(self, client, userdata, msg):
        self._last_message_time = time.time()
        raw_xml = msg.payload.decode("utf-8", errors="replace")
        topic = msg.topic
        logger.info("Received MQTT message on topic %s", topic)

        # 1. Parse XML
        fields = parse_shakealert_xml(raw_xml)
        if fields is None:
            return

        # 2. Deduplicate
        if self._is_duplicate(fields):
            return

        # 3. Store (always, before filtering)
        if self._on_store:
            try:
                self._on_store(topic, raw_xml, fields)
            except Exception as e:
                logger.error("Store callback failed: %s", e)

        # 4. Magnitude filter
        if fields["magnitude"] is not None and fields["magnitude"] < MAGNITUDE_THRESHOLD:
            logger.info(
                "Alert M%.1f below threshold %.1f — discarding.",
                fields["magnitude"], MAGNITUDE_THRESHOLD,
            )
            return

        # 5. Trigger pipeline
        logger.info(
            "Valid alert: M%.1f at (%.4f, %.4f) — triggering pipeline.",
            fields["magnitude"] or 0,
            fields["latitude"] or 0,
            fields["longitude"] or 0,
        )
        if self._on_alert:
            try:
                self._on_alert(fields)
            except Exception as e:
                logger.error("Alert callback failed: %s", e)

    def _on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        logger.info("Subscribed (MID=%s, QoS=%s)", mid, granted_qos)

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        if rc != 0:
            logger.warning("Unexpected disconnect (rc=%d). Will auto-reconnect.", rc)

    # ------------------------------------------------------------------
    # Watchdog
    # ------------------------------------------------------------------
    def _watchdog_loop(self):
        """Reconnects if no message received within MESSAGE_TIMEOUT."""
        while self._running:
            time.sleep(60)
            elapsed = time.time() - self._last_message_time
            if elapsed > MQTT_MESSAGE_TIMEOUT:
                logger.warning(
                    "No message in %d seconds. Reconnecting...",
                    int(elapsed),
                )
                try:
                    if self._client:
                        self._client.reconnect()
                    self._last_message_time = time.time()
                except Exception as e:
                    logger.error("Watchdog reconnect failed: %s", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the MQTT listener (non-blocking)."""
        if self._running:
            logger.warning("Listener already running.")
            return

        self._client = mqtt.Client(
            client_id=MQTT_CLIENT_ID,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_subscribe = self._on_subscribe
        self._client.on_disconnect = self._on_disconnect

        # Credentials
        if MQTT_USERNAME and MQTT_PASSWORD:
            self._client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        # TLS
        if MQTT_TLS_ENABLED:
            self._client.tls_set(
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2,
            )
            self._client.tls_insecure_set(True)

        try:
            logger.info("Connecting to %s:%d ...", MQTT_BROKER_URL, MQTT_BROKER_PORT)
            self._client.connect(MQTT_BROKER_URL, MQTT_BROKER_PORT, 60)
        except Exception as e:
            logger.error("Failed to connect to MQTT broker: %s", e)
            raise

        self._running = True
        self._client.loop_start()

        # Start watchdog
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True, name="mqtt-watchdog"
        )
        self._watchdog_thread.start()
        logger.info("MQTT listener started.")

    def stop(self) -> None:
        """Stop the MQTT listener."""
        self._running = False
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("MQTT listener stopped.")

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to the broker."""
        return self._client is not None and self._client.is_connected()

    def get_status(self) -> Dict[str, Any]:
        """Return listener status for API/frontend."""
        return {
            "running": self._running,
            "connected": self.is_connected,
            "broker": f"{MQTT_BROKER_URL}:{MQTT_BROKER_PORT}",
            "topic": MQTT_TOPIC,
            "last_message_age_seconds": int(time.time() - self._last_message_time),
            "cached_events": len(self._dedup_cache),
        }
