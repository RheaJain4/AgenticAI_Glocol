import json #lets python understand json files
from pathlib import Path #makes it easier to work with file paths


class ReportAgent:

    def __init__(self): #python constructor method, initializes the class
        print("Report Agent Initialized")
        self.input_data = {} #create an empty dictionary to hold the input data (memory for agent)
        self.data_path = Path("data/samples/earthquake_sample_data.json") #path to the input data file


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
    
    
    def validate_input(self): #method 2 to validate the input data
        print("\nValidating input data...")
        required_sections = ["event", "research","occupancy","risk","surge"]

        for section in required_sections:

            if section not in self.input_data:

                print(f"ERROR: Missing section '{section}'")
                return False

        print("Input validation successful!")

        return True



def main():
    agent = ReportAgent()
    if agent.load_input():
        if agent.validate_input():
            print("\nInput data is valid. Ready to generate report.")
#only run the main function if this script is executed directly, not imported as a module
if __name__ == "__main__": 
    main()