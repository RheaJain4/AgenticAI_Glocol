from typing import Dict, Any
import math


class RiskAssessmentAgent:
    """
    Agent 4: Risk Assessment Agent

    Combines:
    - Event severity
    - Population density
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

        severity = str(severity).upper()

        if severity == "CRITICAL":
            return 100
        elif severity == "HIGH":
            return 80
        elif severity == "MEDIUM":
            return 60
        elif severity == "LOW":
            return 40

        # Fallback using magnitude
        if magnitude >= 7:
            return 100
        elif magnitude >= 6:
            return 80
        elif magnitude >= 5:
            return 60
        else:
            return 40

    def normalize_population(
        self,
        population: int,
        affected_radius_km: float,
    ) -> float:
        """
        Normalize population using population density.
        """

        if affected_radius_km <= 0:
            affected_radius_km = 1

        area = math.pi * (affected_radius_km ** 2)
        density = population / area

        if density >= 1000:
            return 100
        elif density >= 500:
            return 80
        elif density >= 200:
            return 60
        elif density >= 100:
            return 40
        else:
            return 20

    def normalize_occupancy(self, occupancy: int) -> float:
        """
        Normalize occupancy to a score out of 100.
        """

        if occupancy >= 5000:
            return 100
        elif occupancy >= 3000:
            return 80
        elif occupancy >= 1500:
            return 60
        elif occupancy >= 500:
            return 40
        else:
            return 20

    def normalize_infrastructure(self, infrastructure: int) -> float:
        """
        Normalize infrastructure count to a score out of 100.
        """

        if infrastructure >= 20:
            return 100
        elif infrastructure >= 15:
            return 80
        elif infrastructure >= 10:
            return 60
        elif infrastructure >= 5:
            return 40
        else:
            return 20

    def calculate_risk_score(
        self,
        severity_score: float,
        population_score: float,
        occupancy_score: float,
        infrastructure_score: float,
    ) -> float:
        """
        Weighted risk score.
        """

        score = (
            (0.40 * severity_score)
            + (0.20 * population_score)
            + (0.30 * occupancy_score)
            + (0.10 * infrastructure_score)
        )

        return round(score, 2)

    def determine_risk_level(self, risk_score: float) -> str:
        """
        Converts numerical risk score to categorical level.
        """

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
        """
        Generates the final risk assessment.
        """

        severity_score = self.severity_to_score(
            event.get("severity"),
            event.get("magnitude", 0),
        )

        population_score = self.normalize_population(
            research.get("estimated_resident_population", 0),
            research.get("affected_radius_km", 1),
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

        estimated_population = occupancy.get(
            "estimated_population",
            0,
        )

        if risk_level == "LOW":
            factor = 0.20
        elif risk_level == "MEDIUM":
            factor = 0.40
        elif risk_level == "HIGH":
            factor = 0.60
        else:
            factor = 0.80

        estimated_people_at_risk = int(
            estimated_population * factor
        )

        return {
            "risk_level": risk_level,
            "priority_area": priority_area,
            "estimated_people_at_risk": estimated_people_at_risk,
            "risk_score": risk_score,
        }
