import json
from urllib import response
import requests
from typing import Dict, Any, Optional

from config import MAGNITUDE_THRESHOLD

"""
Agent 1

Receives emergency alerts from USGS, CAP and FEMA,
validates them and converts them into the common event
schema used by downstream agents.
"""

class Agent1Ingestion:
    def __init__(self):
        self.agent_name = "Agent 1 - Emergency Alert Ingestion"
        self.usgs_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
        self.cap_url = "https://api.weather.gov/alerts/active"
        self.fema_url = ""

    def validate_payload(self, payload: Dict[str, Any]) -> None:
        required_fields = [
            "event_id",
            "event_type",
            "latitude",
            "longitude"
        ]

        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")

        # At least one of magnitude or severity should exist
        if payload.get("magnitude") is None and payload.get("severity") is None:
            raise ValueError("Either magnitude or severity must be provided.")

    def calculate_severity(self, magnitude: float) -> str:
        """
        Used only when severity is not already supplied.
        """

        if magnitude < 4.0:
            return "LOW"
        elif magnitude < 5.5:
            return "MEDIUM"
        elif magnitude < 7.0:
            return "HIGH"
        else:
            return "CRITICAL"

    def normalize_severity(self, severity: str) -> str:
        """
        Converts CAP/FEMA severity values into our schema.
        """

        severity = severity.upper()

        mapping = {
            "MINOR": "LOW",
            "MODERATE": "MEDIUM",
            "SEVERE": "HIGH",
            "EXTREME": "CRITICAL",
            "LOW": "LOW",
            "MEDIUM": "MEDIUM",
            "HIGH": "HIGH",
            "CRITICAL": "CRITICAL"
        }

        return mapping.get(severity, "MEDIUM")

    def normalize_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:

        magnitude = payload.get("magnitude")
        severity = payload.get("severity")

        if severity is None:
            severity = self.calculate_severity(magnitude)
        else:
            severity = self.normalize_severity(severity)

        event = {
            "event_id": payload["event_id"],
            "event_type": payload["event_type"],
            "magnitude": magnitude,
            "intensity": payload.get("intensity"),
            "latitude": payload["latitude"],
            "longitude": payload["longitude"],
            "location": payload.get("location", "Unknown"),
            "severity": severity
        }

        return event

    def process(self, payload: Dict[str, Any]=None,source:str=None) -> Optional[Dict[str, Any]]:
        if payload is None:

            if source == "USGS":
                payload = self.fetch_usgs()

            elif source == "CAP":
                payload = self.fetch_cap()

            elif source == "FEMA":
                payload = self.fetch_fema()

            elif source == "MQTT":
                raise ValueError("MQTT source requires a payload. Use fetch_mqtt() to build one.")

            else:
                raise ValueError("Provide either payload or source.")

        self.validate_payload(payload)

        # Magnitude threshold filter — discard events below threshold or without magnitude
        magnitude = payload.get("magnitude")
        if magnitude is None:
            print("[Agent 1] Event missing magnitude — discarding.")
            return None
            
        if magnitude < MAGNITUDE_THRESHOLD:
            print(f"[Agent 1] Event M{magnitude} below threshold {MAGNITUDE_THRESHOLD} — discarding.")
            return None

        event = self.normalize_event(payload)

        return {
            "event": event,
            "meta": {
                "agent": self.agent_name,
                "source": payload.get("source", "Unknown")
            }
        }

    def fetch_mqtt(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accepts pre-parsed MQTT ShakeAlert fields and converts
        them into the common ingestion payload format.

        Expected alert_data keys: orig_time, magnitude, latitude, longitude, depth, version
        """
        orig_time = alert_data.get("orig_time", "UNKNOWN")
        magnitude = alert_data.get("magnitude")
        latitude = alert_data.get("latitude")
        longitude = alert_data.get("longitude")

        return {
            "source": "MQTT_ShakeAlert",
            "event_id": f"SA_{orig_time}",
            "event_type": "earthquake",
            "magnitude": magnitude,
            "latitude": latitude,
            "longitude": longitude,
            "location": f"({latitude}, {longitude})",
        }
    def fetch_usgs(self) -> Dict[str, Any]:

        response = requests.get(self.usgs_url, timeout=30)
        response.raise_for_status()

        data = response.json()

        feature = data["features"][0]

        return {
            "source": "USGS",
            "event_id": feature["id"],
            "event_type": "earthquake",
            "magnitude": feature["properties"]["mag"],
            "latitude": feature["geometry"]["coordinates"][1],
            "longitude": feature["geometry"]["coordinates"][0],
            "location": feature["properties"]["place"]
        }
    def fetch_cap(self) -> Dict[str, Any]:

        headers = {
            "User-Agent": "PeopleSenseDisasterAgent/1.0"
        }

        response = requests.get(
            self.cap_url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        if not data["features"]:
            raise ValueError("No active CAP alerts found.")

        alert = data["features"][0]["properties"]

        geometry = data["features"][0].get("geometry")

        latitude = None
        longitude = None

    # Take the first coordinate if geometry exists
        if geometry and geometry["type"] == "Polygon":
            longitude, latitude = geometry["coordinates"][0][0]

        return {
            "source": "CAP",
            "event_id": alert.get("id", "UNKNOWN"),
            "event_type": alert.get("event", "Unknown"),
            "severity": alert.get("severity", "Moderate"),
            "latitude": latitude,
            "longitude": longitude,
            "location": alert.get("areaDesc", "Unknown")
        }
    def fetch_fema(self):

        raise NotImplementedError(
            "FEMA API endpoint not configured."
        )


if __name__ == "__main__":

    # Example 1 : USGS Earthquake

    usgs_alert = {
        "source": "USGS",
        "event_id": "EQ001",
        "event_type": "earthquake",
        "magnitude": 6.2,
        "latitude": 34.12,
        "longitude": -118.45,
        "location": "California"
    }

    # Example 2 : CAP Flood

    cap_alert = {
        "source": "CAP",
        "event_id": "FL001",
        "event_type": "flood",
        "severity": "Severe",
        "latitude": 28.61,
        "longitude": 77.20,
        "location": "New Delhi"
    }

    # Example 3 : FEMA Wildfire

    fema_alert = {
        "source": "FEMA",
        "event_id": "WF001",
        "event_type": "wildfire",
        "severity": "Extreme",
        "latitude": 36.77,
        "longitude": -119.41,
        "location": "California"
    }

    agent = Agent1Ingestion()

    output = agent.process(source="USGS")

    print(json.dumps(output, indent=2))