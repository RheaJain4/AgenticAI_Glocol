import json
import math
from typing import Any, Dict, List, Optional

import requests


class Agent2Research:
    def __init__(self):
        self.overpass_servers = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter",
        ]
        self.user_agent = "PeopleSenseDisasterAgent/2.0"

    def calculate_affected_radius(self, magnitude: float) -> float:
        if magnitude < 5.0:
            return 5.0
        elif magnitude < 6.0:
            return 10.0
        elif magnitude < 7.0:
            return 15.0
        return 25.0

    def query_overpass(self, lat: float, lon: float, radius_km: float) -> Dict[str, Any]:
        radius_m = int(radius_km * 1000)

        query = f"""
        [out:json][timeout:60];
        (
          node["amenity"="school"](around:{radius_m},{lat},{lon});
          way["amenity"="school"](around:{radius_m},{lat},{lon});

          node["amenity"="hospital"](around:{radius_m},{lat},{lon});
          way["amenity"="hospital"](around:{radius_m},{lat},{lon});

          node["railway"="station"](around:{radius_m},{lat},{lon});
          way["railway"="station"](around:{radius_m},{lat},{lon});

          node["public_transport"="station"](around:{radius_m},{lat},{lon});
          way["public_transport"="station"](around:{radius_m},{lat},{lon});
        );
        out center tags;
        """

        for server in self.overpass_servers:
            try:
                print(f"Trying Overpass server: {server}")

                response = requests.post(
                    server,
                    data={"data": query},
                    headers={"User-Agent": self.user_agent},
                    timeout=90,
                )

                response.raise_for_status()

                print("Connected successfully.")
                return response.json()

            except requests.RequestException as error:
                print(f"Server failed: {server}")
                print(error)
                continue

        print("All Overpass servers failed.")
        return {"elements": []}

    def extract_location(self, element: Dict[str, Any]) -> Optional[Dict[str, float]]:
        if "lat" in element and "lon" in element:
            return {"latitude": element["lat"], "longitude": element["lon"]}

        if "center" in element:
            return {
                "latitude": element["center"].get("lat"),
                "longitude": element["center"].get("lon"),
            }

        return None

    def format_place(self, element: Dict[str, Any]) -> Dict[str, Any]:
        tags = element.get("tags", {})
        location = self.extract_location(element)

        return {
            "id": str(element.get("id", "unknown")),
            "name": tags.get("name", "Unnamed"),
            "latitude": location["latitude"] if location else None,
            "longitude": location["longitude"] if location else None,
        }

    def categorize_places(self, elements: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        schools = []
        hospitals = []
        transit_stations = []
        seen_ids = set()

        for element in elements:
            element_id = element.get("id")

            if element_id in seen_ids:
                continue

            seen_ids.add(element_id)

            tags = element.get("tags", {})
            amenity = tags.get("amenity")
            railway = tags.get("railway")
            public_transport = tags.get("public_transport")

            place = self.format_place(element)

            if amenity == "school":
                schools.append(place)
            elif amenity == "hospital":
                hospitals.append(place)
            elif railway == "station" or public_transport == "station":
                transit_stations.append(place)

        return {
            "schools": schools,
            "hospitals": hospitals,
            "transit_stations": transit_stations,
        }

    def estimate_population(
        self,
        schools_count: int,
        hospitals_count: int,
        stations_count: int,
        radius_km: float,
    ) -> Dict[str, Any]:
        area_sq_km = math.pi * (radius_km**2)

        estimated_population = (
            schools_count * 5000
            + hospitals_count * 15000
            + stations_count * 8000
        )

        if estimated_population == 0:
            estimated_population = int(area_sq_km * 300)

        density_per_sq_km = estimated_population / area_sq_km

        if density_per_sq_km < 200:
            density_category = "LOW"
        elif density_per_sq_km < 1500:
            density_category = "MEDIUM"
        else:
            density_category = "HIGH"

        return {
            "estimated_resident_population": int(estimated_population),
            "population_density_per_sq_km": round(density_per_sq_km, 2),
            "population_density_category": density_category,
        }

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = payload.get("event", {})

        event_id = event.get("event_id", "UNKNOWN")
        magnitude = event.get("magnitude")
        latitude = event.get("latitude")
        longitude = event.get("longitude")

        if magnitude is None:
            raise ValueError("Missing required field: magnitude")

        if latitude is None or longitude is None:
            raise ValueError("Missing required fields: latitude and longitude")

        affected_radius_km = self.calculate_affected_radius(magnitude)

        osm_data = self.query_overpass(latitude, longitude, affected_radius_km)

        elements = osm_data.get("elements", [])
        categorized = self.categorize_places(elements)

        schools = categorized["schools"]
        hospitals = categorized["hospitals"]
        transit_stations = categorized["transit_stations"]

        population = self.estimate_population(
            schools_count=len(schools),
            hospitals_count=len(hospitals),
            stations_count=len(transit_stations),
            radius_km=affected_radius_km,
        )

        research = {
            "affected_radius_km": affected_radius_km,
            "schools": len(schools),
            "hospitals": len(hospitals),
            "transit_stations": len(transit_stations),
            "infrastructure_count": len(schools) + len(hospitals) + len(transit_stations),
            "estimated_resident_population": population["estimated_resident_population"],
            "population_density_per_sq_km": population["population_density_per_sq_km"],
            "population_density_category": population["population_density_category"],
        }

        return {
            "event": event,
            "research": research,
            "meta": {
                "agent": "Agent 2 - Research Agent",
                "data_source": "OpenStreetMap Overpass API",
                "event_id": event_id,
                "schools": schools,
                "hospitals": hospitals,
                "transit_stations": transit_stations,
            },
        }


if __name__ == "__main__":
    test_payload = {
        "event": {
            "event_id": "EQ001",
            "event_type": "earthquake",
            "magnitude": 6.2,
            "latitude": 34.12,
            "longitude": -118.45,
            "location": "California",
            "severity": "HIGH",
        }
    }

    agent = Agent2Research()
    output = agent.process(test_payload)

    print(json.dumps(output, indent=2))