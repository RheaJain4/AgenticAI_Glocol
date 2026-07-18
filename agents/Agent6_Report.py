#run using  python -m agents.Agent6_Report

import json #lets python understand json files
from multiprocessing import context
from pathlib import Path #makes it easier to work with file paths
from utils.llm import generate_text #so agent 6 can talk to gemini

class ReportAgent:

    def __init__(self, state): #python constructor method, initializes the class
        print("Report Agent Initialized")
        self.input_data = state #create an empty dictionary to hold the input data (memory for agent)
        self.technical_report = ""
        self.news_report = ""
        self.executive_summary = ""
        self.video_script = ""
        self.broadcast_script = ""
        self.report_directory = Path("reports") #path to the directory where reports will be saved


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

    def generate_technical_analysis(self):
        print("\nGenerating technical analysis...")
        prompt_file = Path("prompts/technical_prompt.txt")
        prompt = self.build_prompt(prompt_file)
        analysis = generate_text(prompt)
        return analysis
    

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
        prompt_file = "prompts/news_report_prompt.txt"
        prompt = self.build_prompt(prompt_file)
        self.news_report = generate_text(prompt)
        print("\nNews report generated successfully!")

#--------------------------------------------------------------------------------   
    
    def generate_video_script(self):
        print("\nGenerating video script...")
        prompt_file = Path("prompts/video_script_prompt.txt")
        prompt = self.build_prompt(prompt_file)
        response = generate_text(prompt)
        self.video_script = response.strip()
        print("\nVideo script generated successfully!")
        return self.video_script
    

#--------------------------------------------------------------------------------    

    def generate_technical_report(self):
        print("\nGenerating technical report...")

        prompt_file = "prompts/technical_prompt.txt"

        prompt = self.build_prompt(prompt_file)

        self.technical_report = generate_text(prompt)

        print("\nTechnical report generated successfully!") 


#--------------------------------------------------------------------------------  

    def generate_broadcast_script(self):
        """
        Generate a TTS-optimized broadcast script for HeyGen video generation.
        This is plain spoken narration without scene descriptions.
        """
        print("\nGenerating broadcast script...")
        prompt_file = Path("prompts/broadcast_script_prompt.txt")
        prompt = self.build_prompt(prompt_file)
        response = generate_text(prompt)
        self.broadcast_script = response.strip()
        print("\nBroadcast script generated successfully!")
        return self.broadcast_script

#--------------------------------------------------------------------------------  

    def generate_video(self):
        """
        Generate an AI video using HeyGen from the broadcast script.
        In stub mode, saves the script as a text file.
        """
        from services.heygen_client import HeyGenClient

        if not self.broadcast_script:
            self.generate_broadcast_script()

        event_id = self.input_data.get("event", {}).get("event_id", "UNKNOWN")
        output_dir = str(self.report_directory / event_id)

        client = HeyGenClient()
        result = client.generate_and_save(
            script=self.broadcast_script,
            output_dir=output_dir,
        )
        print(f"\nVideo generation result: {result.get('status', 'unknown')}")
        return result

#--------------------------------------------------------------------------------

    def build_context(self):

        context = f"""
The following JSON contains the complete output of the Emergency Intelligence Pipeline.

This data has already been processed by specialized AI agents.

Instructions:

- Treat every field as factual.
- Do NOT invent information.
- If a value is missing, explicitly state that it is unavailable.
- Base all reasoning only on the provided data.

=========================================================
PIPELINE OUTPUT
=========================================================

{json.dumps(self.input_data, indent=4)}

=========================================================
END OF PIPELINE OUTPUT
=========================================================
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
        # print(prompt)

        return prompt
    

#--------------------------------------------------------------------------------

    def save_reports(self):

        event_id = self.input_data["event"]["event_id"]

        event_folder = self.report_directory / event_id

        event_folder.mkdir(parents=True, exist_ok=True)

        with open(event_folder / "executive_summary.txt", "w", encoding="utf-8") as file:
            file.write(self.executive_summary)

        with open(event_folder / "technical_report.txt", "w", encoding="utf-8") as file:
            file.write(self.technical_report)

        with open(event_folder / "news_report.txt", "w", encoding="utf-8") as file:
            file.write(self.news_report)
        
        with open(event_folder / "video_script.txt", "w", encoding="utf-8") as file:
            file.write(self.video_script)

        # Save broadcast script if generated
        if self.broadcast_script:
            with open(event_folder / "broadcast_script.txt", "w", encoding="utf-8") as file:
                file.write(self.broadcast_script)

        print("\nReports saved successfully.")
#--------------------------------------------------------------------------------
    

