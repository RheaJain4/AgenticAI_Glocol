from typing import Dict, Any


class RiskAssessmentAgent:
    """
    Agent 4: Risk Assessment Agent

    Combines:
    - Event severity/magnitude
    - Population
    - Occupancy
    - Infrastructure

    Returns a final risk assessment.
    """

    def __init__(self):
        pass

    def severity_to_score(self, severity: str, magnitude: float) -> float:
        """
        Converts severity or magnitude into a score out of 100.
        """

        if severity == "CRITICAL":
            return 100
        elif severity == "HIGH":
            return 80
        elif severity == "MEDIUM":
            return 60
        elif severity == "LOW":
            return 40

        # If severity is unavailable, use magnitude
        if magnitude >= 7:
            return 100
        elif magnitude >= 6:
            return 80
        elif magnitude >= 5:
            return 60
        else:
            return 40

    def normalize_population(self, population: int) -> float:
        return min((population / 100000) * 100, 100)

    def normalize_occupancy(self, occupancy: int) -> float:
        return min((occupancy / 5000) * 100, 100)

    def normalize_infrastructure(self, infrastructure: int) -> float:
        return min((infrastructure / 20) * 100, 100)

    def calculate_risk_score(
        self,
        severity_score: float,
        population_score: float,
        occupancy_score: float,
        infrastructure_score: float,
    ) -> float:

        score = (
            0.30 * severity_score
            + 0.25 * population_score
            + 0.30 * occupancy_score
            + 0.15 * infrastructure_score
        )

        return round(score, 2)

    def determine_risk_level(self, risk_score: float) -> str:

        if risk_score >= 80:
            return "CRITICAL"
        elif risk_score >= 60:
            return "HIGH"
        elif risk_score >= 40:
            return "MEDIUM"
        else:
            return "LOW"

    def assess_risk(
        self,
        event: Dict[str, Any],
        research: Dict[str, Any],
        occupancy: Dict[str, Any],
    ) -> Dict[str, Any]:

        severity_score = self.severity_to_score(
            event.get("severity", ""),
            event.get("magnitude", 0),
        )

        population_score = self.normalize_population(
            research.get("estimated_resident_population", 0)
        )

        occupancy_score = self.normalize_occupancy(
            occupancy.get("estimated_population", 0)
        )

        infrastructure_score = self.normalize_infrastructure(
            research.get("infrastructure_count", 0)
        )

        risk_score = self.calculate_risk_score(
            severity_score,
            population_score,
            occupancy_score,
            infrastructure_score,
        )

        risk_level = self.determine_risk_level(risk_score)

        high_density = occupancy.get("high_density_zones", [])

        priority_area = (
            high_density[0]
            if high_density
            else "Unknown"
        )

        estimated_people_at_risk = int(
            occupancy.get("estimated_population", 0) * 0.4
        )

        return {
            "risk_level": risk_level,
            "priority_area": priority_area,
            "estimated_people_at_risk": estimated_people_at_risk,
            "risk_score": risk_score,
        }
