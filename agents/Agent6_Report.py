#run using  python -m agents.Agent6_Report

import json #lets python understand json files
from pathlib import Path #makes it easier to work with file paths
from utils.llm import generate_text #so agent 6 can talk to gemini

class ReportAgent:

    def __init__(self): #python constructor method, initializes the class
        print("Report Agent Initialized")
        self.input_data = {} #create an empty dictionary to hold the input data (memory for agent)
        self.situation = {} #what the agent understands
        self.data_path = Path("data/samples/earthquake_sample_data.json") #path to the input data file
        self.technical_report = ""
        self.news_report = ""
        self.executive_summary = ""
        self.report_directory = Path("reports") #path to the directory where reports will be saved

#--------------------------------------------------------------------------------

    def load_input(self): #method 1 to just read json
        print("\nLoading input data...")

        try:
            with open(self.data_path, "r") as file: #if you open file with "with" instead 
            #of just writing file = whatever then python will automatically close the file when done
                self.input_data = json.load(file) #load the json data into a python dictionary 

        except FileNotFoundError:
            print("Error: Input data not found")
            return False
        
        except json.JSONDecodeError:
            print("Error: Invalid JSON format")
            return False
        
        return True


#--------------------------------------------------------------------------------
    
    def validate_input(self): #method 2 to validate the input data
        print("\nValidating input data...")
        required_sections = ["event", "research","occupancy","risk","surge"]

        for section in required_sections:

            if section not in self.input_data:

                print(f"ERROR: Missing section '{section}'")
                return False

        print("Input validation successful!")

        return True
    

#--------------------------------------------------------------------------------
    
    def normalize_input(self): #method 3 to normalize the input data
        print("\nNormalizing input data...")
        event = self.input_data["event"]
        research = self.input_data["research"]
        occupancy = self.input_data["occupancy"]
        risk = self.input_data["risk"]
        surge = self.input_data["surge"]

        if event["magnitude"] is not None:
            hazard_metric = f"Magnitude {event['magnitude']}"

        elif event["intensity"] is not None:
            hazard_metric = f"Intensity {event['intensity']}"

        else:
            hazard_metric = "Unknown"

        self.situation = {
            # -----------------------------
            # Event Information
            # -----------------------------
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "location": event["location"],
            "latitude": event["latitude"],
            "longitude": event["longitude"],
            "coordinates": f"{event['latitude']}, {event['longitude']}",
            "hazard_metric": hazard_metric,
            "severity": event["severity"],

            # -----------------------------
            # Research
            # -----------------------------
            "affected_radius": research["affected_radius_km"],
            "schools": research["schools"],
            "hospitals": research["hospitals"],
            "transit_stations": research["transit_stations"],
            "infrastructure_count": research["infrastructure_count"],
            "estimated_population": research["estimated_resident_population"],
            "population_density": research["population_density_category"],

            # -----------------------------
            # Occupancy
            # -----------------------------
            "estimated_occupancy": occupancy["estimated_population"],
            "high_density_zones": occupancy["high_density_zones"],

            # -----------------------------
            # Risk
            # -----------------------------
            "risk_level": risk["risk_level"],
            "risk_score": risk["risk_score"],
            "priority_area": risk["priority_area"],
            "people_at_risk": risk["estimated_people_at_risk"],

            # -----------------------------
            # Crowd Surge Prediction
            # -----------------------------
            "predicted_hotspots": surge["predicted_hotspots"],
            "prediction_window": surge["time_window_minutes"],
            "prediction_model": surge["prediction_model"],
            "prediction_confidence": surge["confidence"],
            #"congestion_probability": surge["congestion_probability"]

    }

        print("Input normalized successfully!")


#--------------------------------------------------------------------------------

    def generate_technical_analysis(self):
        print("\nGenerating technical analysis...")
        prompt_file = Path("prompts/technical_prompt.txt")
        prompt = self.build_prompt(prompt_file)
        analysis = generate_text(prompt)
        return analysis
    

#--------------------------------------------------------------------------------

    def build_executive_summary(self):
        summary = f"""
EXECUTIVE SUMMARY 
A {self.situation["severity"]} severity {self.situation["event_type"]} has been detected near {self.situation["location"]}. Estimated occupancy within the affected area is 
{self.situation["estimated_occupancy"]} people. Current operational risk level is {self.situation["risk_level"]}.
        """
        return summary.strip()  # Remove leading/trailing whitespace
    

#--------------------------------------------------------------------------------
    
    def generate_executive_summary(self):
        print("\nGenerating executive summary...")
        prompt_file = Path("prompts/executive_summary.txt")
        prompt = self.build_prompt(prompt_file)
        response = generate_text(prompt)
        self.executive_summary = response.strip()  # Remove leading/trailing whitespace
        print("\nExecutive summary generated successfully!")
        return self.executive_summary
    

#-------------------------------------------------------------------------------- 
    
    def generate_news_report(self):
        print("\nGenerating news report...")
        prompt_file = Path("prompts/news_report_prompt.txt")
        prompt = self.build_prompt(prompt_file)
        response = generate_text(prompt)
        self.news_report = response.strip()  # Remove leading/trailing whitespace
        print("\nNews report generated successfully!")
        return self.news_report
    

#--------------------------------------------------------------------------------    

    def generate_technical_report(self):
        print("\nGenerating technical report...")

        report = f"""
                EMERGENCY SITUATION TECHNICAL REPORT
                
--------------------------------------------------------

EVENT INFORMATION

Event ID: {self.situation["event_id"]}
Disaster Type: {self.situation["event_type"]}
Location: {self.situation["location"]}
Coordinates: {self.situation["coordinates"]}
{self.situation["hazard_metric"]}
Severity: {self.situation["severity"]}

--------------------------------------------------------

AREA ASSESSMENT

Affected Radius: {self.situation["affected_radius"]} km 
Estimated Population: {self.situation["estimated_population"]}
Population Density: {self.situation["population_density"]}
Schools: {self.situation["schools"]} 
Hospitals: {self.situation["hospitals"]}
Transit Stations: {self.situation["transit_stations"]}
Infrastructure Count: {self.situation["infrastructure_count"]}

--------------------------------------------------------

OCCUPANCY ASSESSMENT

Estimated Occupancy: {self.situation["estimated_occupancy"]}
High Density Zones: {", ".join(self.situation["high_density_zones"])} 

--------------------------------------------------------

RISK ASSESSMENT 
Risk Level: {self.situation["risk_level"]}
Risk Score: {self.situation["risk_score"]} 
Priority Area: {self.situation["priority_area"]}
Estimated People At Risk: {self.situation["people_at_risk"]}
Predicted Hotspots:{", ".join(self.situation["predicted_hotspots"])}
Prediction Confidence: {self.situation["prediction_confidence"]}
"""
        
        analysis = self.generate_technical_analysis()

        report += f"""

--------------------------------------------------------

ANALYST OBSERVATIONS

{analysis}

"""
        
        self.technical_report = report
        print("\n Report successfully generated")   
        return self.technical_report.strip()  # Remove leading/trailing whitespace   


#--------------------------------------------------------------------------------  

    def build_context(self):

        context = f"""
==================================================
EMERGENCY EVENT INFORMATION
==================================================

EVENT

Event ID:
{self.situation["event_id"]}

Event Type:
{self.situation["event_type"]}

Location:
{self.situation["location"]}

Coordinates:
{self.situation["coordinates"]}

Hazard Metric:
{self.situation["hazard_metric"]}

Severity:
{self.situation["severity"]}


==================================================
AREA INFORMATION
==================================================

Affected Radius:
{self.situation["affected_radius"]} km

Estimated Resident Population:
{self.situation["estimated_population"]}

Population Density:
{self.situation["population_density"]}


==================================================
INFRASTRUCTURE
==================================================

Schools:
{self.situation["schools"]}

Hospitals:
{self.situation["hospitals"]}

Transit Stations:
{self.situation["transit_stations"]}

Infrastructure Count:
{self.situation["infrastructure_count"]}


==================================================
OCCUPANCY
==================================================

Estimated Occupancy:
{self.situation["estimated_occupancy"]}

High Density Zones:
{", ".join(self.situation["high_density_zones"])}



==================================================
RISK
==================================================

Risk Level:
{self.situation["risk_level"]}

Risk Score:
{self.situation["risk_score"]}

Priority Area:
{self.situation["priority_area"]}

Estimated People At Risk:
{self.situation["people_at_risk"]}


==================================================
CROWD SURGE PREDICTION
==================================================

Predicted Hotspots:
{", ".join(self.situation["predicted_hotspots"])}

Prediction Window:
{self.situation["prediction_window"]} minutes

Prediction Model:
{self.situation["prediction_model"]}

Prediction Confidence:
{self.situation["prediction_confidence"]}
"""
        return context


#--------------------------------------------------------------------------------

    def build_prompt(self, prompt_file):

        # Read the prompt template
        with open(prompt_file, "r", encoding="utf-8") as file:
            template = file.read()

        # Build the factual context
        context = self.build_context()

        # Combine them
        prompt = template + "\n\n" + context

        return prompt
    

#--------------------------------------------------------------------------------

    def save_reports(self):

        event_folder = self.report_directory / self.situation["event_id"]

        event_folder.mkdir(parents=True, exist_ok=True)

        with open(event_folder / "executive_summary.txt", "w", encoding="utf-8") as file:
            file.write(self.executive_summary)

        with open(event_folder / "technical_report.txt", "w", encoding="utf-8") as file:
            file.write(self.technical_report)

        with open(event_folder / "news_report.txt", "w", encoding="utf-8") as file:
            file.write(self.news_report)

        print("\nReports saved successfully.")
#--------------------------------------------------------------------------------
    

def main():
    agent = ReportAgent()
    if agent.load_input():
        if agent.validate_input():
            agent.normalize_input()
            print()
            #agent.build_context()
            
            news = agent.generate_news_report()
            exec_summary = agent.generate_executive_summary()
            technical_report = agent.generate_technical_report()
            print(exec_summary)
            print(technical_report)
            print()
            print("News Report:")
            print(news)
            agent.save_reports()

#only run the main function if this script is executed directly, not imported as a module
if __name__ == "__main__": 
    main()