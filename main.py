import sys
import argparse
import logging
import json

from orchestrator import PipelineOrchestrator
from config import is_mqtt_enabled

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_poll_mode(source: str = "USGS"):
    """One-shot pipeline execution (original behavior)."""
    print("Starting Emergency Intelligence Pipeline (poll mode)...")

    orchestrator = PipelineOrchestrator()
    state = orchestrator.run_pipeline(source=source)

    if state is None:
        print("No actionable event found (filtered or deduplicated).")
        return

    print("\n========== EXECUTIVE SUMMARY ==========\n")
    print(state.get("reports", {}).get("executive_summary", "N/A"))

    print("\n========== TECHNICAL REPORT ==========\n")
    print(state.get("reports", {}).get("technical_report", "N/A"))

    print("\n========== NEWS REPORT ==========\n")
    print(state.get("reports", {}).get("news_report", "N/A"))

    print("\n========== VIDEO SCRIPT ==========\n")
    print(state.get("reports", {}).get("video_script", "N/A"))


def run_mqtt_mode():
    """Event-driven mode: listen for MQTT alerts and trigger pipeline."""
    from services.mqtt_listener import ShakeAlertMQTTListener
    from services.alert_store import create_alert_store

    print("Starting Emergency Intelligence Pipeline (MQTT mode)...")

    if not is_mqtt_enabled():
        print("ERROR: MQTT credentials not configured in .env")
        print("Set MQTT_USERNAME and MQTT_PASSWORD to enable MQTT mode.")
        sys.exit(1)

    # Create alert store (DynamoDB or local fallback)
    alert_store = create_alert_store()

    # Create orchestrator
    orchestrator = PipelineOrchestrator()

    # Create MQTT listener
    listener = ShakeAlertMQTTListener(
        on_alert_callback=orchestrator.handle_mqtt_alert,
        on_store_callback=alert_store.save_alert,
    )

    listener.start()

    print("MQTT listener running. Press Ctrl+C to stop.")
    print(f"Broker: {listener.get_status()['broker']}")
    print(f"Topic: {listener.get_status()['topic']}")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        listener.stop()
        print("Done.")


def main():
    parser = argparse.ArgumentParser(
        description="AgenticAI Glocol — Emergency Intelligence Pipeline"
    )
    parser.add_argument(
        "--mode",
        choices=["poll", "mqtt"],
        default="poll",
        help="Execution mode: 'poll' for one-shot USGS polling, 'mqtt' for real-time ShakeAlert (default: poll)",
    )
    parser.add_argument(
        "--source",
        choices=["USGS", "CAP"],
        default="USGS",
        help="Data source for poll mode (default: USGS)",
    )

    args = parser.parse_args()

    if args.mode == "mqtt":
        run_mqtt_mode()
    else:
        run_poll_mode(source=args.source)


if __name__ == "__main__":
    main()