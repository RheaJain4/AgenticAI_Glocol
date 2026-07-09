from agents.Agent1_Ingestion import Agent1Ingestion
from agents.Agent2_Research import Agent2Research
from agents.Agent3_Occupancy import OccupancyAgent
from agents.Agent4_RiskAssesment import RiskAssessmentAgent
from agents.Agent5_CrowdSurgePrediction import CrowdSurgePredictionAgent
from agents.Agent6_Report import ReportAgent
import json

def main():

    print("Starting Emergency Intelligence Pipeline...")

    agent1 = Agent1Ingestion()
    agent2 = Agent2Research()
    agent3 = OccupancyAgent()
    agent4 = RiskAssessmentAgent()
    agent5 = CrowdSurgePredictionAgent()

    state = agent1.process(source="USGS")

    state = agent2.process(state)

    agent3_input = {
        "event_id": state["event"]["event_id"],
        "latitude": state["event"]["latitude"],
        "longitude": state["event"]["longitude"],
        "affected_radius_km": state["research"]["affected_radius_km"]
    }

    state["occupancy"] = agent3.run(agent3_input)

    state["risk"] = agent4.assess_risk(
        state["event"],
        state["research"],
        state["occupancy"]
    )
    state = agent5.run(state)

    agent6 = ReportAgent(state)

    agent6.generate_executive_summary()
    agent6.generate_technical_report()
    agent6.generate_news_report()
    agent6.generate_video_script()

    agent6.save_reports()


    print("\n========== EXECUTIVE SUMMARY ==========\n")
    print(agent6.executive_summary)

    print("\n========== TECHNICAL REPORT ==========\n")
    print(agent6.technical_report)

    print("\n========== NEWS REPORT ==========\n")
    print(agent6.news_report)

    print("\n========== VIDEO SCRIPT ==========\n")
    print(agent6.video_script)

if __name__ == "__main__":
    main()