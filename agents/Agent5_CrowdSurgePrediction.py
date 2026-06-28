import json
import os

class CrowdSurgePredictionAgent:
    def __init__(self, model_type="XGBoost"):
        self.model_type = model_type

    def run(self, current_state: dict) -> dict:
        """
        Takes the accumulated JSON data from Agents 1-4 and predicts
        future crowd movement and congestion hotspots.
        """
        # Extract necessary fields from previous agents safely
        # Handle both nested and flattened structures
        event_data = current_state.get("event", current_state)
        occupancy_data = current_state.get("occupancy", current_state)
        risk_data = current_state.get("risk", current_state)
        
        # Pull high density zones identified by Agent 3
        high_density_zones = occupancy_data.get("high_density_zones", [])
        priority_area = risk_data.get("priority_area", "")
        severity = event_data.get("severity", "MEDIUM")

        # --- Crowd Dynamics & Prediction Logic ---
        import json
        
        # Try to use LLM for true AI prediction
        prompt = f"""
        You are an expert crowd dynamics AI for emergency response. 
        Based on the following disaster situation, predict the most likely crowd congestion hotspots (specific exits, routes, or choke points) and a congestion probability (0.0 to 1.0).
        
        Event: {severity} severity {event_data.get('event_type', 'Unknown event')}
        Known High Density Zones: {high_density_zones}
        Priority Risk Area: {priority_area}
        Risk Score: {risk_data.get("risk_score", 50)}/100
        
        Respond ONLY with a valid JSON object in this exact format, with no markdown formatting or extra text:
        {{
            "predicted_hotspots": ["Specific Choke Point 1", "Evacuation Route A", "Main Exit"],
            "congestion_probability": 0.85
        }}
        """
        
        predicted_hotspots = []
        congestion_probability = 0.50
        used_model = "Rule-based Fallback"
        
        try:
            # We import locally here to avoid circular imports if any, and because it's only needed for this step
            from utils.llm import generate_text
            llm_response = generate_text(prompt)
            if llm_response:
                clean_json = llm_response.replace('```json', '').replace('```', '').strip()
                ai_data = json.loads(clean_json)
                
                predicted_hotspots = ai_data.get("predicted_hotspots", [])
                congestion_probability = float(ai_data.get("congestion_probability", 0.50))
                used_model = "Gemini-2.5-Flash AI"
        except Exception as e:
            print(f"[Agent 5] LLM Prediction failed, using fallback. Error: {e}")
            
        # --- Fallback Rule-based Logic (if LLM fails or is empty) ---
        if not predicted_hotspots:
            for zone in high_density_zones:
                predicted_hotspots.extend([f"{zone} - Main Exits", f"{zone} - Evacuation Routes"])
            
            if not predicted_hotspots:
                if priority_area and priority_area != "Unknown":
                    predicted_hotspots = [f"{priority_area} - Main Exits", f"{priority_area} - Evacuation Routes"]
                else:
                    predicted_hotspots = ["Emergency Exit 1", "Main Assembly Point"]
            
            predicted_hotspots = list(set(predicted_hotspots))
            
            risk_score = risk_data.get("risk_score", 50)
            base_probability = 0.50
            if severity == "CRITICAL": base_probability += 0.35
            elif severity == "HIGH": base_probability += 0.25
            elif severity == "MEDIUM": base_probability += 0.15
            
            if risk_score > 80: base_probability += 0.12
            congestion_probability = min(round(base_probability, 2), 1.0)
            
        # Determine time window based on severity
        if severity == "CRITICAL": time_window_minutes = 10
        elif severity == "HIGH": time_window_minutes = 15
        elif severity == "MEDIUM": time_window_minutes = 30
        else: time_window_minutes = 60
        
        risk_score = risk_data.get("risk_score", 50)
        confidence_level = "HIGH" if risk_score > 70 else "MEDIUM"
        
        # Override self.model_type for output
        self.model_type = used_model

        # Build Agent 5's required output structure
        surge_output = {
            "predicted_hotspots": predicted_hotspots,
            "time_window_minutes": time_window_minutes,
            "prediction_model": self.model_type,
            "confidence": confidence_level,
            "congestion_probability": congestion_probability
        }

        # Append your result to the global pipeline state
        current_state["surge"] = surge_output
        return current_state

# Quick self-test block to verify it runs without crashing
if __name__ == "__main__":
    # Mocking sample data matching the exact output chain from Agents 1-4
    sample_pipeline_input = {
        "event": {
            "event_id": "EQ001",
            "event_type": "Earthquake",
            "magnitude": 6.2,
            "intensity": None,
            "latitude": 34.12,
            "longitude": -118.45,
            "location": "California",
            "severity": "HIGH"
        },
        "research": {
            "affected_radius_km": 15,
            "schools": 2,
            "hospitals": 2,
            "transit_stations": 2,
            "infrastructure_count": 17,
            "estimated_resident_population": 75000,
            "population_density_category": "MEDIUM"
        },
        "occupancy": {
            "estimated_population": 3200,
            "high_density_zones": ["Station A", "Mall B"]
        },
        "risk": {
            "risk_level": "CRITICAL",
            "priority_area": "Station A",
            "estimated_people_at_risk": 1200,
            "risk_score": 92
        }
    }

    agent = CrowdSurgePredictionAgent()
    final_output = agent.run(sample_pipeline_input)
    
    print("--- AGENT 5 OUTPUT VERIFICATION ---")
    print(json.dumps(final_output, indent=2))