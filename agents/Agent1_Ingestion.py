import json
from typing import Dict, Any

"""
Agent 1

Receives emergency alerts from USGS, CAP and FEMA,
validates them and converts them into the common event
schema used by downstream agents.
"""

class Agent1Ingestion:
    def __init__(self):
        self.agent_name = "Agent 1 - Emergency Alert Ingestion"

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

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:

        self.validate_payload(payload)

        event = self.normalize_event(payload)

        return {
            "event": event,
            "meta": {
                "agent": self.agent_name,
                "source": payload.get("source", "Unknown")
            }
        }


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

    output = agent.process(fema_alert)

    print(json.dumps(output, indent=2))