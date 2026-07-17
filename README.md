# Agentic AI Emergency Intelligence Platform

An AI-powered multi-agent emergency intelligence system that combines **real-time hazard alerts**, **geospatial research**, **live occupancy intelligence**, **risk assessment**, **crowd surge prediction**, and **automated report generation** to support emergency response and situational awareness.

The project was developed as part of the **Practice School-I internship at Glocol Networks Pvt. Ltd.** under the **PeopleSense.ai** platform.

---

## Overview

During an emergency, responders often need to gather information from multiple independent sources before making decisions.

This project automates that workflow using six specialized AI agents that collaborate through a shared JSON state.

Instead of relying on a single large prompt, every agent performs one well-defined task and passes structured information to the next agent, making the pipeline modular, explainable, and extensible.

---

## System Architecture

```
              USGS / CAP Alerts
                     │
                     ▼
         Agent 1 ─ Emergency Alert Ingestion
                     │
                     ▼
      Agent 2 ─ Geographic Research Agent
                     │
                     ▼
      Agent 3 ─ Occupancy Intelligence Agent
                     │
                     ▼
       Agent 4 ─ Risk Assessment Agent
                     │
                     ▼
    Agent 5 ─ Crowd Surge Prediction Agent
                     │
                     ▼
      Agent 6 ─ Report Generation Agent
                     │
                     ▼
 Executive Summary
 Technical Report
 News Report
 Video Script
```

---

# Agents

## Agent 1 — Emergency Alert Ingestion

Retrieves and normalizes emergency alerts from trusted sources.

### Responsibilities

- Fetch live earthquake alerts from USGS
- Support CAP-compatible alerts
- Validate incoming payloads
- Normalize heterogeneous alert formats
- Assign severity levels
- Produce a common event schema

### Output

```json
{
  "event": {
      "event_id": "...",
      "magnitude": 6.1,
      "latitude": ...,
      "longitude": ...,
      "severity": "HIGH"
  }
}
```

---

## Agent 2 — Geographic Research

Enriches the event with geographic context using OpenStreetMap.

### Responsibilities

- Query Overpass API
- Discover nearby hospitals
- Schools
- Transit stations
- Critical infrastructure
- Estimate affected radius
- Estimate resident population

---

## Agent 3 — Occupancy Intelligence

Uses the PeopleSense Occupancy API to estimate real-time human occupancy.

### Responsibilities

- Retrieve live sensor information
- Filter sensors within the affected radius
- Estimate occupancy
- Identify high-density zones

Example output

```json
{
    "estimated_population": 3125,
    "high_density_zones": [
        "University Union",
        "Library"
    ]
}
```

---

## Agent 4 — Risk Assessment

Combines information from previous agents to estimate operational risk.

### Inputs

- Hazard severity
- Population
- Occupancy
- Infrastructure

### Outputs

- Risk score
- Risk level
- Priority area
- Estimated people at risk

---

## Agent 5 — Crowd Surge Prediction

Predicts likely crowd movement following the emergency.

Uses

- Occupancy estimates
- Risk score
- High-density locations
- Gemini reasoning

Outputs

- Congestion hotspots
- Prediction confidence
- Congestion probability
- Prediction window

---

## Agent 6 — Report Generation

Agent 6 combines the outputs of all previous agents into structured natural-language reports.

Generated reports include

- Executive Summary
- Technical Report
- News Report
- Emergency Video Script

Rather than sending raw event data directly to the LLM, Agent 6 constructs a comprehensive prompt containing the complete emergency context, ensuring accurate and consistent report generation.

---

# Project Structure

```
AgenticAI_Glocol/

│
├── agents/
│   ├── Agent1_Ingestion.py
│   ├── Agent2_Research.py
│   ├── Agent3_Occupancy.py
│   ├── Agent4_RiskAssessment.py
│   ├── Agent5_CrowdSurgePrediction.py
│   └── Agent6_Report.py
│
├── prompts/
│   ├── executive_summary.txt
│   ├── technical_report.txt
│   ├── news_report.txt
│   └── video_script.txt
│
├── reports/
│
├── utils/
│
├── main.py
│
└── README.md
```

---

# Technologies Used

- Python
- Google Gemini 2.5 Flash
- PeopleSense Occupancy API
- USGS Earthquake API
- OpenStreetMap
- Overpass API
- JSON
- Git

---

# Data Sources

| Source | Purpose |
|---------|----------|
| USGS | Live earthquake alerts |
| OpenStreetMap | Geographic information |
| Overpass API | Infrastructure discovery |
| PeopleSense API | Live occupancy estimation |
| Gemini API | Report generation & reasoning |

---

# Running the Project

Clone the repository

```bash
git clone https://github.com/RheaJain4/AgenticAI_Glocol.git
```

Install dependencies

```bash
pip install -r requirements.txt
```

Set your environment variables

```text
GEMINI_API_KEY=YOUR_API_KEY
PEOPLESENSE_API_KEY=YOUR_API_KEY
```

Run

```bash
python main.py
```

---

# Example Pipeline

```
USGS Alert
      ↓

Agent 1
Normalize Event

      ↓

Agent 2
Infrastructure Analysis

      ↓

Agent 3
Live Occupancy

      ↓

Agent 4
Risk Assessment

      ↓

Agent 5
Crowd Prediction

      ↓

Agent 6
Generate Reports
```

---

# Generated Outputs

The pipeline automatically generates

```
reports/

└── <event_id>/
    ├── executive_summary.txt
    ├── technical_report.txt
    ├── news_report.txt
    └── video_script.txt
```

---

# Future Improvements

- Support FEMA integration
- Multi-hazard support (floods, cyclones, wildfires)
- Real-time dashboard
- Shelter recommendation agent
- Evacuation route optimization
- Live traffic integration
- Digital twin visualization
- Historical event analytics


---

# License

This repository was developed as part of an academic internship project. Please contact the contributors before using the project for commercial purposes.
