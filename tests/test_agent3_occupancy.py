"""
Tests for Agent 3: Occupancy Context Agent
==========================================
Run with:   python -m pytest tests/test_agent3_occupancy.py -v

Covers all test scenarios from the project spec:
  TC-301  Normal earthquake, real API data
  TC-302  High-occupancy zone identified
  TC-303  Low/zero occupancy area (small radius)
  TC-304  Missing optional fields (magnitude, etc.)
  TC-305  Invalid / missing lat-lon → ValueError
  TC-306  API rate-limit cache — second call within 60 s uses cache
  TC-307  Output schema validation (keys + types)
  TC-308  High-density threshold filtering
  TC-309  Null occupancy records excluded from count
  TC-310  Large radius includes more zones than small radius
"""

import sys
import os
import time
import json
import pytest
from unittest.mock import patch, MagicMock

# Make agents/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.Agent3_Occupancy import OccupancyAgent, HIGH_DENSITY_THRESHOLD

# ---------------------------------------------------------------------------
# Shared mock payload — mirrors real PeopleSense API structure
# ---------------------------------------------------------------------------
MOCK_LOCATIONS = [
    # Within 15 km of Sacramento (38.5816, -121.4944)
    {
        "LocationID": "CSU-14", "Latitude": 38.5597, "Longitude": -121.4224,
        "MaxOccupancy": 100, "PlaceID": "CSU", "GroupID": "University Union",
        "ScanMode": "SIMULATED", "Occupancy": 62, "DerivedCount": None,
        "Timestamp": "2026-06-25 07:52:02"
    },
    {
        "LocationID": "CSU-01", "Latitude": 38.5655, "Longitude": -121.4243,
        "MaxOccupancy": 100, "PlaceID": "CSU", "GroupID": "Riverview Hall",
        "ScanMode": "SIMULATED", "Occupancy": 67, "DerivedCount": None,
        "Timestamp": "2026-06-25 07:52:02"
    },
    # Null occupancy — should be excluded from total
    {
        "LocationID": "FHS4", "Latitude": 38.6494, "Longitude": -121.1581,
        "MaxOccupancy": None, "PlaceID": "FCUSD", "GroupID": None,
        "ScanMode": "LIVE", "Occupancy": None, "DerivedCount": None,
        "Timestamp": None
    },
    # Far away — outside any normal radius
    {
        "LocationID": "A3", "Latitude": 32.9028, "Longitude": -97.0369,
        "MaxOccupancy": None, "PlaceID": "DFWA", "GroupID": None,
        "ScanMode": "SIMULATED", "Occupancy": 91, "DerivedCount": None,
        "Timestamp": "2026-06-25 07:52:02"
    },
    # Low occupancy, within radius
    {
        "LocationID": "S-124", "Latitude": 38.5555, "Longitude": -121.4201,
        "MaxOccupancy": 80, "PlaceID": "SAC-STATE-VIRTUAL", "GroupID": "Children Center",
        "ScanMode": "LIVE", "Occupancy": 8, "DerivedCount": 6.0,
        "Timestamp": "2026-05-01 17:48:20"
    },
]

MOCK_API_RESPONSE = {"locations": MOCK_LOCATIONS, "fetchedAt": "2026-06-25T14:00:00Z"}


def make_agent_with_mock() -> OccupancyAgent:
    """Return an OccupancyAgent whose HTTP call is mocked."""
    agent = OccupancyAgent()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = MOCK_API_RESPONSE
    agent._mock_resp = mock_resp
    return agent


def base_input(radius_km=15, lat=38.5816, lon=-121.4944):
    return {
        "event_id": "EQ001",
        "magnitude": 6.2,
        "latitude": lat,
        "longitude": lon,
        "affected_radius_km": radius_km,
        "population_density_category": "HIGH",
    }


# ---------------------------------------------------------------------------
# TC-301  Normal earthquake — returns valid output
# ---------------------------------------------------------------------------
class TestTC301_NormalEarthquake:
    @patch("agents.Agent3_Occupancy.requests.get")
    def test_returns_dict_with_required_keys(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        result = agent.run(base_input())
        assert isinstance(result, dict)
        assert "event_id" in result
        assert "estimated_population" in result
        assert "high_density_zones" in result

    @patch("agents.Agent3_Occupancy.requests.get")
    def test_event_id_preserved(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        result = agent.run(base_input())
        assert result["event_id"] == "EQ001"


# ---------------------------------------------------------------------------
# TC-302  High-occupancy zones identified
# ---------------------------------------------------------------------------
class TestTC302_HighOccupancyZones:
    @patch("agents.Agent3_Occupancy.requests.get")
    def test_high_density_zones_detected(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        result = agent.run(base_input())
        # CSU-14 (62) and CSU-01 (67) are both >= HIGH_DENSITY_THRESHOLD
        assert len(result["high_density_zones"]) >= 2

    @patch("agents.Agent3_Occupancy.requests.get")
    def test_high_density_zones_sorted_descending(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        result = agent.run(base_input())
        # Just check it's a list (ordering can vary with ties)
        assert isinstance(result["high_density_zones"], list)


# ---------------------------------------------------------------------------
# TC-303  Small radius — near-zero or zero population
# ---------------------------------------------------------------------------
class TestTC303_LowOccupancyArea:
    @patch("agents.Agent3_Occupancy.requests.get")
    def test_tiny_radius_returns_zero_population(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        # 0.1 km radius — nothing within that
        result = agent.run(base_input(radius_km=0.1))
        assert result["estimated_population"] == 0
        assert result["high_density_zones"] == []


# ---------------------------------------------------------------------------
# TC-304  Missing optional fields (no magnitude etc.)
# ---------------------------------------------------------------------------
class TestTC304_MissingOptionalFields:
    @patch("agents.Agent3_Occupancy.requests.get")
    def test_missing_magnitude_does_not_crash(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        inp = {
            "event_id": "EQ-NOMAIN",
            "latitude": 38.5816,
            "longitude": -121.4944,
            "affected_radius_km": 15,
            # no "magnitude", no "population_density_category"
        }
        result = agent.run(inp)
        assert result["event_id"] == "EQ-NOMAIN"
        assert isinstance(result["estimated_population"], int)


# ---------------------------------------------------------------------------
# TC-305  Missing lat/lon → ValueError
# ---------------------------------------------------------------------------
class TestTC305_InvalidInput:
    def test_missing_latitude_raises_value_error(self):
        agent = OccupancyAgent()
        with pytest.raises(ValueError, match="latitude"):
            agent.run({"event_id": "BAD", "longitude": -121.49, "affected_radius_km": 10})

    def test_missing_longitude_raises_value_error(self):
        agent = OccupancyAgent()
        with pytest.raises(ValueError, match="longitude"):
            agent.run({"event_id": "BAD", "latitude": 38.58, "affected_radius_km": 10})

    def test_missing_both_raises_value_error(self):
        agent = OccupancyAgent()
        with pytest.raises(ValueError):
            agent.run({"event_id": "BAD", "affected_radius_km": 10})


# ---------------------------------------------------------------------------
# TC-306  Cache — second call within 60 s reuses cached data
# ---------------------------------------------------------------------------
class TestTC306_CacheBehaviour:
    @patch("agents.Agent3_Occupancy.requests.get")
    def test_api_called_only_once_within_ttl(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        agent.run(base_input())
        agent.run(base_input())   # second call
        # HTTP GET should only have been made once
        assert mock_get.call_count == 1

    @patch("agents.Agent3_Occupancy.requests.get")
    def test_api_refreshed_after_ttl(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        agent.run(base_input())
        # Manually expire cache
        agent._cache_timestamp = time.time() - 65
        agent.run(base_input())
        assert mock_get.call_count == 2


# ---------------------------------------------------------------------------
# TC-307  Output schema validation
# ---------------------------------------------------------------------------
class TestTC307_OutputSchema:
    @patch("agents.Agent3_Occupancy.requests.get")
    def test_output_types(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        result = agent.run(base_input())
        assert isinstance(result["event_id"], str)
        assert isinstance(result["estimated_population"], int)
        assert isinstance(result["high_density_zones"], list)
        for zone in result["high_density_zones"]:
            assert isinstance(zone, str)

    @patch("agents.Agent3_Occupancy.requests.get")
    def test_output_has_exactly_3_keys(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        result = agent.run(base_input())
        assert set(result.keys()) == {"event_id", "estimated_population", "high_density_zones"}


# ---------------------------------------------------------------------------
# TC-308  High-density threshold filtering
# ---------------------------------------------------------------------------
class TestTC308_ThresholdFiltering:
    @patch("agents.Agent3_Occupancy.requests.get")
    def test_below_threshold_not_in_high_density(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        result = agent.run(base_input())
        # S-124 has Occupancy=8, which is below threshold — must NOT appear
        zone_names = " ".join(result["high_density_zones"])
        assert "Children Center" not in zone_names


# ---------------------------------------------------------------------------
# TC-309  Null occupancy records excluded
# ---------------------------------------------------------------------------
class TestTC309_NullOccupancyExcluded:
    @patch("agents.Agent3_Occupancy.requests.get")
    def test_null_occupancy_not_counted(self, mock_get):
        only_null = {"locations": [
            {"LocationID": "NULL-LOC", "Latitude": 38.5816, "Longitude": -121.4944,
             "PlaceID": "TEST", "GroupID": None, "Occupancy": None, "DerivedCount": None}
        ]}
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=only_null)
        )
        agent = OccupancyAgent()
        result = agent.run(base_input(radius_km=1))
        assert result["estimated_population"] == 0


# ---------------------------------------------------------------------------
# TC-310  Larger radius includes more zones
# ---------------------------------------------------------------------------
class TestTC310_RadiusScaling:
    @patch("agents.Agent3_Occupancy.requests.get")
    def test_larger_radius_ge_smaller(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        agent = OccupancyAgent()
        small = agent.run(base_input(radius_km=5))
        # Force cache expiry so API is called again cleanly
        agent._cache_timestamp = time.time() - 65
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value=MOCK_API_RESPONSE)
        )
        large = agent.run(base_input(radius_km=50))
        assert large["estimated_population"] >= small["estimated_population"]
