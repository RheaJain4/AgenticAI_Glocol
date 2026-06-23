from typing import Dict, Any


class RiskAssessmentAgent:

    def __init__(self):
        pass

    def calculate_risk_score(
        self,
        magnitude: float,
        occupancy: int,
        population_density: str
    ) -> int:

        score = 0

        if magnitude >= 7.0:
            score += 4
        elif magnitude >= 6.0:
            score += 3
        elif magnitude >= 5.0:
            score += 2

        if occupancy >= 5000:
            score += 3
        elif occupancy >= 2000:
            score += 2
        elif occupancy >= 500:
            score += 1

        if population_density == "HIGH":
            score += 2
        elif population_density == "MEDIUM":
            score += 1

        return score

    def determine_risk_level(self, score: int) -> str:

        if score >= 8:
            return "CRITICAL"
        elif score >= 6:
            return "HIGH"
        elif score >= 3:
            return "MEDIUM"
        else:
            return "LOW"

    def assess_risk(
        self,
        event_data: Dict[str, Any],
        research_data: Dict[str, Any],
        occupancy_data: Dict[str, Any]
    ) -> Dict[str, Any]:

        magnitude = event_data.get("magnitude", 0)

        occupancy = occupancy_data.get(
            "estimated_population",
            0
        )

        population_density = research_data.get(
            "population_density_category",
            "LOW"
        )

        risk_score = self.calculate_risk_score(
            magnitude,
            occupancy,
            population_density
        )

        risk_level = self.determine_risk_level(
            risk_score
        )

        people_at_risk = int(
            occupancy * 0.4
        )

        high_density_zones = occupancy_data.get(
            "high_density_zones",
            []
        )

        priority_area = (
            high_density_zones[0]
            if high_density_zones
            else "Unknown"
        )

        return {
            "event_id": event_data.get("event_id"),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "estimated_people_at_risk": people_at_risk,
            "priority_area": priority_area,
            "risk_factors": [
                "earthquake_magnitude",
                "occupancy",
                "population_density"
            ],
            "recommended_action":
                "Immediate evacuation and emergency response"
                if risk_level in ["HIGH", "CRITICAL"]
                else "Continue monitoring",
            "assessment_summary":
                f"Risk assessed as {risk_level} based on magnitude, occupancy and population density."
        }
