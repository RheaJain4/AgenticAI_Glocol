"""
Agent 2: Research / Exposure Enrichment Agent

This agent receives an emergency event from Agent 1 and enriches it with
nearby schools, hospitals, transit stations, public places, population exposure,
and infrastructure risk.

Currently uses mock data so the pipeline can run without paid APIs.
Later, this can be connected to OpenStreetMap, Google Places, FEMA, Census, etc.
"""

from typing import Dict, List, Any


class ResearchAgent:
    def __init__(self):
        pass

    def calculate_affected_radius(self, magnitude: float) -> int:
        if magnitude < 5.0:
            return 5
        elif magnitude < 6.0:
            return 10
        elif magnitude < 7.0:
            return 15
        else:
            return 25

    def get_nearby_schools(self, latitude: float, longitude: float, radius_km: int) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Central High School",
                "distance_km": 2.1,
                "latitude": latitude + 0.01,
                "longitude": longitude + 0.01
            },
            {
                "name": "North Valley Public School",
                "distance_km": 4.3,
                "latitude": latitude - 0.02,
                "longitude": longitude + 0.02
            }
        ]

    def get_nearby_hospitals(self, latitude: float, longitude: float, radius_km: int) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Metro General Hospital",
                "distance_km": 3.4,
                "latitude": latitude + 0.015,
                "longitude": longitude - 0.015
            },
            {
                "name": "City Trauma Center",
                "distance_km": 6.8,
                "latitude": latitude - 0.025,
                "longitude": longitude - 0.02
            }
        ]

    def get_transit_stations(self, latitude: float, longitude: float, radius_km: int) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Station A",
                "type": "Metro Station",
                "distance_km": 1.8
            },
            {
                "name": "Central Bus Terminal",
                "type": "Bus Station",
                "distance_km": 5.2
            }
        ]

    def get_public_places(self, latitude: float, longitude: float, radius_km: int) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Mall B",
                "type": "Shopping Mall",
                "distance_km": 2.5
            },
            {
                "name": "City Market",
                "type": "Market Area",
                "distance_km": 3.9
            }
        ]

    def estimate_population_exposure(self, magnitude: float, radius_km: int) -> Dict[str, Any]:
        estimated_population = radius_km * 5000

        if estimated_population > 80000:
            density_category = "HIGH"
        elif estimated_population > 30000:
            density_category = "MEDIUM"
        else:
            density_category = "LOW"

        return {
            "estimated_resident_population": estimated_population,
            "population_density_category": density_category
        }

    def get_critical_infrastructure(self, latitude: float, longitude: float, radius_km: int) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Highway Interchange",
                "type": "Transport Infrastructure",
                "distance_km": 4.7
            },
            {
                "name": "Power Substation",
                "type": "Energy Infrastructure",
                "distance_km": 5.5
            },
            {
                "name": "Bridge near Station A",
                "type": "Bridge",
                "distance_km": 2.2
            }
        ]

    def run(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_id = event.get("event_id")
        magnitude = event.get("magnitude")
        latitude = event.get("latitude")
        longitude = event.get("longitude")

        if magnitude is None or latitude is None or longitude is None:
            raise ValueError("Event must contain magnitude, latitude, and longitude.")

        affected_radius_km = self.calculate_affected_radius(magnitude)

        schools = self.get_nearby_schools(latitude, longitude, affected_radius_km)
        hospitals = self.get_nearby_hospitals(latitude, longitude, affected_radius_km)
        transit_stations = self.get_transit_stations(latitude, longitude, affected_radius_km)
        public_places = self.get_public_places(latitude, longitude, affected_radius_km)
        population = self.estimate_population_exposure(magnitude, affected_radius_km)
        infrastructure = self.get_critical_infrastructure(latitude, longitude, affected_radius_km)

        output = {
            "event_id": event_id,
            "affected_radius_km": affected_radius_km,

            "schools": len(schools),
            "school_locations": schools,

            "hospitals": len(hospitals),
            "hospital_locations": hospitals,

            "transit_stations": len(transit_stations),
            "transit_station_locations": transit_stations,

            "major_public_places": public_places,

            "estimated_resident_population": population["estimated_resident_population"],
            "population_density_category": population["population_density_category"],

            "critical_infrastructure": infrastructure,

            "research_summary": (
                "The affected zone contains schools, hospitals, transit stations, "
                "public gathering areas, and critical infrastructure. These locations "
                "should be passed to the Occupancy Agent for live crowd estimation."
            )
        }

        return output


if __name__ == "__main__":
    sample_event = {
        "event_id": "EQ001",
        "event_type": "earthquake",
        "magnitude": 6.2,
        "latitude": 34.12,
        "longitude": -118.45,
        "severity": "HIGH"
    }

    agent = ResearchAgent()
    result = agent.run(sample_event)

    print(result)