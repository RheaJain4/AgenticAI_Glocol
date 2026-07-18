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
    # Sensorless Estimation Fallback
    # ------------------------------------------------------------------
    def _estimate_without_sensors(
        self, research_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimate occupancy when no PeopleSense sensors are within range.

        Uses a layered approach:
        1. Population density baseline from Agent 2
        2. Infrastructure proximity multipliers
        3. Time-of-day adjustment
        4. LLM contextual refinement (Gemini)

        Returns the same schema as the sensor path, plus estimation metadata.
        """
        from datetime import datetime
        import json as _json
        from pathlib import Path

        research = research_output.get("research", {})
        event = research_output.get("event", {})

        # --- Layer 1: Population density baseline ---
        resident_pop = research.get("estimated_resident_population", 0)
        density_category = research.get("population_density_category", "MEDIUM")
        density_per_sq_km = research.get("population_density_per_sq_km", 350)

        # --- Layer 2: Infrastructure proximity scoring ---
        schools = research.get("schools", 0)
        hospitals = research.get("hospitals", 0)
        transit_stations = research.get("transit_stations", 0)
        infrastructure_count = research.get("infrastructure_count", 0)

        now = datetime.now()
        hour = now.hour
        is_weekday = now.weekday() < 5
        day_name = now.strftime("%A")
        time_str = now.strftime("%H:%M")

        # School occupancy: ~500 avg during school hours
        school_pop = 0
        if is_weekday and 8 <= hour <= 15:
            school_pop = schools * 500

        # Hospital occupancy: ~200 avg, 24/7
        hospital_pop = hospitals * 200

        # Transit: rush hour vs off-peak
        transit_pop = 0
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            transit_pop = transit_stations * 1000  # Rush hour
        elif 6 <= hour <= 22:
            transit_pop = transit_stations * 200   # Daytime off-peak
        else:
            transit_pop = transit_stations * 50    # Night

        infrastructure_estimate = school_pop + hospital_pop + transit_pop

        # --- Layer 3: Time-of-day multiplier on residential population ---
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            time_multiplier = 0.4  # Many people commuting, fewer at home
        elif 9 <= hour <= 17:
            time_multiplier = 0.3  # Most at work/school
        elif 22 <= hour or hour <= 6:
            time_multiplier = 0.9  # Most at home/sleeping
        else:
            time_multiplier = 0.6  # Evening, mixed

        residential_present = int(resident_pop * time_multiplier)
        rule_based_estimate = residential_present + infrastructure_estimate

        # --- Layer 4: LLM contextual refinement ---
        estimated_population = rule_based_estimate
        confidence = 0.5
        high_density_zones: List[str] = []
        estimation_factors = ["population_density", "infrastructure_proximity", "time_of_day"]

        try:
            from utils.llm import generate_json as llm_generate_json

            prompt_path = Path("prompts/occupancy_estimation_prompt.txt")
            if prompt_path.exists():
                template = prompt_path.read_text(encoding="utf-8")
                prompt = template.format(
                    event_type=event.get("event_type", "earthquake"),
                    severity=event.get("severity", "MEDIUM"),
                    latitude=research_output.get("latitude", 0),
                    longitude=research_output.get("longitude", 0),
                    affected_radius_km=research_output.get("affected_radius_km", 15),
                    schools=schools,
                    hospitals=hospitals,
                    transit_stations=transit_stations,
                    infrastructure_count=infrastructure_count,
                    estimated_resident_population=resident_pop,
                    population_density_per_sq_km=density_per_sq_km,
                    population_density_category=density_category,
                    current_time=time_str,
                    day_of_week=day_name,
                )

                schema = {
                    "type": "OBJECT",
                    "properties": {
                        "estimated_occupancy": {"type": "INTEGER"},
                        "confidence": {"type": "NUMBER"},
                        "reasoning": {"type": "STRING"},
                        "high_density_locations": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                    },
                    "required": [
                        "estimated_occupancy",
                        "confidence",
                        "reasoning",
                        "high_density_locations",
                    ],
                }

                llm_response = llm_generate_json(prompt, schema)
                if llm_response:
                    llm_data = _json.loads(llm_response)
                    estimated_population = int(llm_data.get("estimated_occupancy", rule_based_estimate))
                    confidence = float(llm_data.get("confidence", 0.5))
                    high_density_zones = llm_data.get("high_density_locations", [])
                    estimation_factors.append("llm_reasoning")
                    logger.info(
                        "LLM estimation: %d people, confidence %.2f",
                        estimated_population, confidence,
                    )

        except Exception as e:
            logger.warning("LLM estimation failed, using rule-based: %s", e)
            # Fall back to rule-based estimate
            estimated_population = rule_based_estimate
            confidence = 0.4

            # Generate high-density zones from infrastructure
            if schools > 0 and is_weekday and 8 <= hour <= 15:
                high_density_zones.append("School Zone (estimated)")
            if hospitals > 0:
                high_density_zones.append("Hospital Zone (estimated)")
            if transit_stations > 0 and (7 <= hour <= 9 or 17 <= hour <= 19):
                high_density_zones.append("Transit Hub (estimated)")

        return {
            "event_id": research_output.get("event_id", "UNKNOWN"),
            "estimated_population": max(estimated_population, 0),
            "high_density_zones": high_density_zones,
            "sensor_count": 0,
            "estimation_method": "estimated",
            "confidence_score": round(confidence, 2),
            "estimation_factors": estimation_factors,
        }

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

        Output schema:
        {
            "event_id": str,
            "estimated_population": int,
            "high_density_zones": [str, ...],
            "sensor_count": int,
            "estimation_method": "sensor" | "estimated",
            "confidence_score": float (0.0-1.0),
            "estimation_factors": [str, ...]
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

        sensor_count = len(nearby)

        # 4. If no sensors found, use estimation fallback
        if sensor_count == 0:
            logger.info(
                "No PeopleSense sensors in range — using sensorless estimation."
            )
            return self._estimate_without_sensors(research_output)

        # 5. Return sensor-based data with full schema
        return {
            "event_id": event_id,
            "estimated_population": estimated_population,
            "high_density_zones": high_density_zones,
            "sensor_count": sensor_count,
            "estimation_method": "sensor",
            "confidence_score": 1.0,
            "estimation_factors": ["peoplesense_sensors"],
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
