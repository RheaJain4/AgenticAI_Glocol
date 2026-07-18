"""
Tests for ShakeAlert MQTT Listener
====================================
Tests XML parsing, deduplication, magnitude filtering, and callback behavior.
"""

import unittest
from unittest.mock import MagicMock, patch

from services.mqtt_listener import parse_shakealert_xml, ShakeAlertMQTTListener


# ---------------------------------------------------------------------------
# Sample XML Messages
# ---------------------------------------------------------------------------
SAMPLE_XML_M6 = """<?xml version="1.0"?>
<event_message version="3" category="live" timestamp="2026-07-18T10:00:00Z">
  <core_info>
    <orig_time>2026-07-18T09:58:30Z</orig_time>
    <mag>6.2</mag>
    <lat>34.12</lat>
    <lon>-118.45</lon>
    <depth>10.5</depth>
  </core_info>
</event_message>"""

SAMPLE_XML_M3 = """<?xml version="1.0"?>
<event_message version="1" category="live" timestamp="2026-07-18T10:05:00Z">
  <core_info>
    <orig_time>2026-07-18T10:04:00Z</orig_time>
    <mag>3.1</mag>
    <lat>35.50</lat>
    <lon>-117.80</lon>
    <depth>5.0</depth>
  </core_info>
</event_message>"""

SAMPLE_XML_INVALID = """<broken><xml>"""

SAMPLE_XML_MISSING_TIME = """<?xml version="1.0"?>
<event_message version="1">
  <core_info>
    <mag>5.0</mag>
    <lat>34.00</lat>
    <lon>-118.00</lon>
  </core_info>
</event_message>"""


class TestParseShakeAlertXML(unittest.TestCase):
    """Tests for the XML parser."""

    def test_parse_valid_message(self):
        """TC-M01: Valid XML parses correctly."""
        result = parse_shakealert_xml(SAMPLE_XML_M6)
        self.assertIsNotNone(result)
        self.assertEqual(result["orig_time"], "2026-07-18T09:58:30Z")
        self.assertAlmostEqual(result["magnitude"], 6.2)
        self.assertAlmostEqual(result["latitude"], 34.12)
        self.assertAlmostEqual(result["longitude"], -118.45)
        self.assertAlmostEqual(result["depth"], 10.5)
        self.assertEqual(result["version"], "3")

    def test_parse_low_magnitude(self):
        """TC-M02: Low magnitude XML parses correctly."""
        result = parse_shakealert_xml(SAMPLE_XML_M3)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["magnitude"], 3.1)

    def test_parse_invalid_xml(self):
        """TC-M03: Invalid XML returns None."""
        result = parse_shakealert_xml(SAMPLE_XML_INVALID)
        self.assertIsNone(result)

    def test_parse_missing_orig_time(self):
        """TC-M04: Missing orig_time returns None."""
        result = parse_shakealert_xml(SAMPLE_XML_MISSING_TIME)
        self.assertIsNone(result)


class TestDeduplication(unittest.TestCase):
    """Tests for the deduplication logic."""

    def setUp(self):
        self.listener = ShakeAlertMQTTListener()

    def test_first_message_not_duplicate(self):
        """TC-M05: First occurrence is not a duplicate."""
        fields = parse_shakealert_xml(SAMPLE_XML_M6)
        self.assertFalse(self.listener._is_duplicate(fields))

    def test_same_message_is_duplicate(self):
        """TC-M06: Same message repeated is a duplicate."""
        fields = parse_shakealert_xml(SAMPLE_XML_M6)
        self.listener._is_duplicate(fields)  # First time
        self.assertTrue(self.listener._is_duplicate(fields))  # Second time

    def test_different_event_not_duplicate(self):
        """TC-M07: Different event is not a duplicate."""
        fields1 = parse_shakealert_xml(SAMPLE_XML_M6)
        fields2 = parse_shakealert_xml(SAMPLE_XML_M3)
        self.listener._is_duplicate(fields1)
        self.assertFalse(self.listener._is_duplicate(fields2))


class TestMagnitudeFiltering(unittest.TestCase):
    """Tests for magnitude threshold filtering in the on_message flow."""

    def test_above_threshold_triggers_callback(self):
        """TC-M08: M6.2 alert triggers pipeline callback."""
        callback = MagicMock()
        listener = ShakeAlertMQTTListener(on_alert_callback=callback)

        # Simulate on_message
        mock_msg = MagicMock()
        mock_msg.payload = SAMPLE_XML_M6.encode("utf-8")
        mock_msg.topic = "eew/sys/gm-contour/data"

        listener._on_message(None, None, mock_msg)
        callback.assert_called_once()

        # Verify the parsed fields
        alert = callback.call_args[0][0]
        self.assertAlmostEqual(alert["magnitude"], 6.2)

    def test_below_threshold_discarded(self):
        """TC-M09: M3.1 alert does NOT trigger pipeline callback."""
        callback = MagicMock()
        listener = ShakeAlertMQTTListener(on_alert_callback=callback)

        mock_msg = MagicMock()
        mock_msg.payload = SAMPLE_XML_M3.encode("utf-8")
        mock_msg.topic = "eew/sys/gm-contour/data"

        listener._on_message(None, None, mock_msg)
        callback.assert_not_called()

    def test_store_callback_always_called(self):
        """TC-M10: Store callback fires even for below-threshold events."""
        store_cb = MagicMock()
        alert_cb = MagicMock()
        listener = ShakeAlertMQTTListener(
            on_alert_callback=alert_cb, on_store_callback=store_cb
        )

        mock_msg = MagicMock()
        mock_msg.payload = SAMPLE_XML_M3.encode("utf-8")
        mock_msg.topic = "eew/sys/gm-contour/data"

        listener._on_message(None, None, mock_msg)
        store_cb.assert_called_once()  # Stored
        alert_cb.assert_not_called()   # Not triggered


if __name__ == "__main__":
    unittest.main()
