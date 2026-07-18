# Agentic AI Emergency Intelligence Platform

An AI-powered multi-agent emergency intelligence system that combines **real-time hazard alerts**, **geospatial research**, **live occupancy intelligence**, **risk assessment**, **crowd surge prediction**, and **automated report generation** to support emergency response and situational awareness.

The project was developed as part of the **Practice School-I internship at Glocol Networks Pvt. Ltd.** under the **PeopleSense.ai** platform.

---

## Overview

During an emergency, responders often need to gather information from multiple independent sources before making decisions.

This project automates that workflow using six specialized AI agents that collaborate through a shared JSON state. The system features a centralized **Pipeline Orchestrator** to handle source selection, message deduplication, and pipeline tracking.

Instead of relying on a single large prompt, every agent performs one well-defined task and passes structured information to the next agent, making the pipeline modular, explainable, and extensible.

---

## New Features (v2.0)

1. **Event-driven MQTT ShakeAlert Integration**: Automatically ingests live USGS ShakeAlert messages via MQTT and persists them to DynamoDB.
2. **Real-time React Dashboard**: A modern, glassmorphism UI built with Vite/React that visualizes live pipeline progress, event coordinates, occupancy, and risk scores via WebSockets.
3. **Sensorless Occupancy Fallback**: Uses LLM-based estimation using infrastructure, population density, and time-of-day proxies when live PeopleSense sensors are unavailable.
4. **HeyGen AI Video Integration**: Agent 6 now generates broadcast-ready TTS scripts that can be seamlessly passed to HeyGen for AI avatar video generation.
5. **Enhanced Orchestrator**: Gracefully handles API filtering, deduplicates identical alerts, and broadcasts granular progress updates.

---

## System Architecture

```
        USGS REST / MQTT ShakeAlert
                      │
                      ▼
          Agent 1 ─ Emergency Alert Ingestion
                      │
                      ▼
       Agent 2 ─ Geographic Research Agent
                      │
                      ▼
       Agent 3 ─ Occupancy Intelligence Agent (Sensor + Fallback)
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
  Executive / Technical / News / Broadcast Scripts
```

---

## Agents

### Agent 1 — Emergency Alert Ingestion
- Listens to MQTT ShakeAlerts or polls USGS.
- Validates and normalizes alerts.
- Discards minor events (magnitude < 4.5).

### Agent 2 — Geographic Research
- Queries OpenStreetMap / Overpass API to discover nearby hospitals, schools, and transit stations.
- Estimates baseline resident population.

### Agent 3 — Occupancy Intelligence
- Retrieves live sensor information from the PeopleSense API.
- If sensors are missing or offline, dynamically switches to a context-aware **LLM estimation fallback** to predict human occupancy, providing a confidence score.

### Agent 4 — Risk Assessment
- Combines hazard severity, population, and infrastructure.
- Computes an operational risk score (0-100) and risk level.

### Agent 5 — Crowd Surge Prediction
- Predicts likely crowd movement following the emergency.
- Outputs congestion hotspots and probabilities.

### Agent 6 — Report Generation
- Combines outputs of all agents into structured natural-language reports.
- Generates: Executive Summary, Technical Report, News Report, Video Script, and a TTS-optimized Broadcast Script.

---

## Project Structure

```
AgenticAI_Glocol/
├── agents/            # 6 AI Agents
├── api/               # FastAPI Backend & WebSockets
├── frontend/          # Vite/React Real-time Dashboard
├── prompts/           # LLM Instruction Templates
├── reports/           # Generated pipeline outputs
├── schemas/           # Agent JSON I/O validation schemas
├── services/          # MQTT listener, HeyGen Client, DynamoDB Store
├── tests/             # Pytest Suites (MQTT, Occupancy, etc.)
├── orchestrator.py    # Pipeline Orchestration logic
├── config.py          # Centralized configuration
└── main.py            # CLI Entrypoint
```

---

## Running the Project

1. **Clone and Install**
   ```bash
   git clone https://github.com/RheaJain4/AgenticAI_Glocol.git
   pip install -r requirements.txt
   cd frontend && npm install
   ```

2. **Environment Variables**
   Create a `.env` file in the root (see `.env.example` for details) and add your API keys:
   ```env
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=...
   GEMINI_API_KEY=...
   ```

3. **Running the Dashboard (Frontend + Backend)**
   You need two terminal windows:
   ```bash
   # Terminal 1: Start the FastAPI backend
   python -m api.server
   
   # Terminal 2: Start the React frontend
   cd frontend && npm run dev
   ```
   Open `http://localhost:5173` to view the dashboard.

4. **Running MQTT Background Mode**
   To listen for live ShakeAlerts passively:
   ```bash
   python main.py --mode mqtt
   ```
