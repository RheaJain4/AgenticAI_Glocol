"""
Agent 3: Occupancy Context Agent
=================================
Queries the PeopleSense Occupancy API to retrieve live crowd/occupancy data
for locations within the earthquake's affected radius.

Flow:
  Agent 2 output  →  OccupancyAgent.run()  →  Agent 4 input

Output JSON (strict schema, do NOT modify — consumed by Agent 4):
{
    "event_id": str,
    "estimated_population": int,
    "high_density_zones": [str, ...]
}

Rate-limit note: PeopleSense API is polled at most once per 60 seconds.
Credentials are loaded from the project-root .env file (never hard-coded).
"""

import os
import math
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [Agent3] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Load .env (project root, one level up from agents/)
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PEOPLESENSE_API_URL: str = os.getenv(
    "PEOPLESENSE_API_URL",
    "https://w8bdwhaps0.execute-api.us-west-2.amazonaws.com/v1/occupancy",
)
PEOPLESENSE_API_KEY: str = os.getenv("PEOPLESENSE_API_KEY", "")
CACHE_TTL_SECONDS: int = 60          # honour API rate limit
HIGH_DENSITY_THRESHOLD: int = 50     # occupancy count to flag a zone as high-density


# ---------------------------------------------------------------------------
# Haversine helper
# ---------------------------------------------------------------------------
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two lat/lon points."""
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# OccupancyAgent
# ---------------------------------------------------------------------------
class OccupancyAgent:
    """
    Calls PeopleSense API, filters locations within the event radius,
    and returns aggregated occupancy data for downstream agents.
    """

    def __init__(self) -> None:
        self._cache_data: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: float = 0.0

    # ------------------------------------------------------------------
    # API fetch (with caching)
    # ------------------------------------------------------------------
    def _fetch_all_locations(self) -> List[Dict[str, Any]]:
        """
        Fetch all PeopleSense locations. Returns cached data if fetched
        within the last CACHE_TTL_SECONDS seconds to respect rate limits.
        """
        now = time.time()
        if self._cache_data is not None and (now - self._cache_timestamp) < CACHE_TTL_SECONDS:
            logger.info("Returning cached PeopleSense data (%.0fs old).",
                        now - self._cache_timestamp)
            return self._cache_data

        if not PEOPLESENSE_API_KEY:
            raise EnvironmentError(
                "PEOPLESENSE_API_KEY is not set. "
                "Add it to the .env file in the project root."
            )

        headers = {"x-api-key": PEOPLESENSE_API_KEY}
        params = {"filter": "ALL"}

        logger.info("Fetching live data from PeopleSense API …")
        try:
            response = requests.get(
                PEOPLESENSE_API_URL,
                headers=headers,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            logger.error("PeopleSense API request failed: %s", exc)
            # Return cached data if available, even if stale
            if self._cache_data is not None:
                logger.warning("Using stale cached data due to API error.")
                return self._cache_data
            raise

        payload = response.json()
        # PeopleSense API wraps results in a "data" key
        locations: List[Dict[str, Any]] = (
            payload.get("data")
            or payload.get("locations")
            or (payload if isinstance(payload, list) else [])
        )

        self._cache_data = locations
        self._cache_timestamp = now
        logger.info("Fetched %d locations from PeopleSense.", len(locations))
        return locations

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------
    def _filter_by_radius(
        self,
        locations: List[Dict[str, Any]],
        epicenter_lat: float,
        epicenter_lon: float,
        radius_km: float,
    ) -> List[Dict[str, Any]]:
        """Return only locations that fall within the affected radius."""
        nearby: List[Dict[str, Any]] = []
        for loc in locations:
            lat = loc.get("Latitude")
            lon = loc.get("Longitude")
            if lat is None or lon is None:
                continue
            dist = _haversine_km(epicenter_lat, epicenter_lon, lat, lon)
            if dist <= radius_km:
                loc["_distance_km"] = round(dist, 2)
                nearby.append(loc)
        return nearby

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------
    def _aggregate(
        self, nearby: List[Dict[str, Any]]
    ) -> Tuple[int, List[str]]:
        """
        Return:
          - total estimated population (sum of valid Occupancy values)
          - list of high-density zone names (sorted by occupancy desc)
        """
        total_population = 0
        high_density: List[Tuple[str, int]] = []

        for loc in nearby:
            occupancy = loc.get("Occupancy")
            if occupancy is None:
                # Fall back to DerivedCount if available
                occupancy = loc.get("DerivedCount")
            if occupancy is None:
                continue

            occupancy = int(occupancy)
            total_population += occupancy

            zone_name = loc.get("LocationID", "Unknown")
            group = loc.get("GroupID")
            place = loc.get("PlaceID", "")
            if group:
                label = f"{group} ({place})"
            else:
                label = f"{zone_name} ({place})"

            if occupancy >= HIGH_DENSITY_THRESHOLD:
                high_density.append((label, occupancy))

        # Sort high-density zones by occupancy descending
        high_density.sort(key=lambda x: x[1], reverse=True)
        high_density_zones = [name for name, _ in high_density]

        return total_population, high_density_zones

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def run(self, research_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accepts Agent 2's output and returns Agent 3's output.

        Required fields from Agent 2:
          - event_id          (str)
          - affected_radius_km (int)
          - latitude/longitude available on the original event; Agent 2
            passes them through, OR we derive epicenter from Agent 2's
            school_locations[0] neighbourhood (fallback).

        Note: The original earthquake lat/lon must be present in the
        research_output dict (Agent 2 currently passes event_id only).
        We accept them here directly so the pipeline can pass the merged
        event dict without schema breakage.

        Output (strict — do NOT change without coordinating with Agent 4):
        {
            "event_id": str,
            "estimated_population": int,
            "high_density_zones": [str, ...]
        }
        """
        event_id: str = research_output.get("event_id", "UNKNOWN")
        affected_radius_km: float = float(research_output.get("affected_radius_km", 15))

        # Epicenter coordinates — injected from merged event context
        latitude: Optional[float] = research_output.get("latitude")
        longitude: Optional[float] = research_output.get("longitude")

        if latitude is None or longitude is None:
            raise ValueError(
                "OccupancyAgent.run() requires 'latitude' and 'longitude' in the input. "
                "Merge the original event dict with Agent 2's output before calling Agent 3."
            )

        logger.info(
            "Running Occupancy Agent for event=%s | epicenter=(%.4f, %.4f) | radius=%.1f km",
            event_id, latitude, longitude, affected_radius_km,
        )

        # 1. Fetch live data (cached if within TTL)
        all_locations = self._fetch_all_locations()

        # 2. Filter to affected radius
        nearby = self._filter_by_radius(
            all_locations, latitude, longitude, affected_radius_km
        )
        logger.info("Locations within %.1f km: %d", affected_radius_km, len(nearby))

        # 3. Aggregate
        estimated_population, high_density_zones = self._aggregate(nearby)
        logger.info(
            "Estimated population in affected zone: %d | High-density zones: %s",
            estimated_population, high_density_zones,
        )

        # 4. Return — exact schema required by Agent 4
        return {
            "event_id": event_id,
            "estimated_population": estimated_population,
            "high_density_zones": high_density_zones,
            "sensor_count": len(nearby)
        }


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Simulates what the pipeline orchestrator passes after merging
    # Agent 1 event + Agent 2 output.
    sample_input = {
        # From Agent 1 (event fields preserved through pipeline)
        "event_id": "EQ001",
        "magnitude": 6.2,
        "latitude": 38.5816,   # Sacramento, CA — near SAC-STATE-VIRTUAL zones
        "longitude": -121.4944,

        # From Agent 2
        "affected_radius_km": 15,
        "schools": 2,
        "hospitals": 2,
        "transit_stations": 2,
        "population_density_category": "HIGH",
    }

    agent = OccupancyAgent()
    result = agent.run(sample_input)

    import json
    print("\n=== Agent 3 Output ===")
    print(json.dumps(result, indent=2))
