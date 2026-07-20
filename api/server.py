"""
FastAPI Server
===============
REST API + WebSocket backend for the frontend dashboard.
Serves pipeline status, event data, reports, and real-time updates.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgenticAI Glocol API",
    description="Emergency Intelligence Pipeline — REST API & WebSocket",
    version="2.0.0",
)

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _capture_loop():
    global _event_loop
    _event_loop = asyncio.get_event_loop()

# ---------------------------------------------------------------------------
# In-memory state (shared with orchestrator via callbacks)
# ---------------------------------------------------------------------------
pipeline_status: Dict[str, Any] = {
    "pipeline_state": "idle",
    "current_agent": None,
    "progress": 0,
    "event_id": None,
    "error": None,
}

pipeline_results: List[Dict[str, Any]] = []  # History of completed runs
active_websockets: Set[WebSocket] = set()
mqtt_status: Dict[str, Any] = {"running": False, "connected": False}


# ---------------------------------------------------------------------------
# WebSocket broadcast
# ---------------------------------------------------------------------------
async def broadcast_to_clients(message: Dict[str, Any]):
    """Send a message to all connected WebSocket clients."""
    if not active_websockets:
        return
    data = json.dumps(message, default=str)
    disconnected = set()
    for ws in active_websockets:
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.add(ws)
    active_websockets.difference_update(disconnected)


_event_loop = None  # Will be set on startup

def on_pipeline_state_change(status: Dict[str, Any]):
    """Callback for the orchestrator — bridges sync→async via thread-safe scheduling."""
    global pipeline_status
    pipeline_status = status

    # Schedule async broadcast from the worker thread
    if _event_loop and _event_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            broadcast_to_clients({"type": "pipeline_status", "data": status}),
            _event_loop,
        )


def store_pipeline_result(state: Dict[str, Any]):
    """Store a completed pipeline result for the API."""
    # Create a serializable summary (strip large report text for the list view)
    summary = {
        "event_id": state.get("event", {}).get("event_id", "UNKNOWN"),
        "event_type": state.get("event", {}).get("event_type", "unknown"),
        "magnitude": state.get("event", {}).get("magnitude"),
        "severity": state.get("event", {}).get("severity"),
        "latitude": state.get("event", {}).get("latitude"),
        "longitude": state.get("event", {}).get("longitude"),
        "location": state.get("event", {}).get("location"),
        "risk_level": state.get("risk", {}).get("risk_level"),
        "risk_score": state.get("risk", {}).get("risk_score"),
        "estimated_people_at_risk": state.get("risk", {}).get("estimated_people_at_risk"),
        "occupancy_method": state.get("occupancy", {}).get("estimation_method", "sensor"),
        "occupancy_confidence": state.get("occupancy", {}).get("confidence_score", 1.0),
        "timestamp": time.time(),
    }
    pipeline_results.insert(0, summary)

    # Keep only the last 50 results
    if len(pipeline_results) > 50:
        pipeline_results.pop()

    # Persist the full state to disk for the frontend
    event_id = state.get("event", {}).get("event_id")
    if event_id:
        reports_dir = Path("reports") / event_id
        reports_dir.mkdir(parents=True, exist_ok=True)
        state_file = reports_dir / "pipeline_state.json"
        try:
            state_file.write_text(json.dumps(state, default=str), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save pipeline_state.json: {e}")


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/status")
async def get_status():
    """Current pipeline status."""
    return JSONResponse(content={
        "pipeline": pipeline_status,
        "mqtt": mqtt_status,
        "total_events_processed": len(pipeline_results),
    })


@app.get("/api/events")
async def list_events():
    """List all processed events (summaries)."""
    return JSONResponse(content={"events": pipeline_results})


@app.get("/api/events/latest")
async def get_latest_event():
    """Get the latest processed event with full details."""
    if not pipeline_results:
        raise HTTPException(status_code=404, detail="No events processed yet.")

    latest = pipeline_results[0]
    event_id = latest["event_id"]

    # Try to load full pipeline state from reports directory
    full_state = _load_event_data(event_id)
    if full_state:
        return JSONResponse(content=full_state)

    return JSONResponse(content=latest)


@app.get("/api/events/{event_id}")
async def get_event(event_id: str):
    """Get full pipeline state for a specific event."""
    full_state = _load_event_data(event_id)
    if full_state:
        return JSONResponse(content=full_state)

    # Search in memory
    for result in pipeline_results:
        if result["event_id"] == event_id:
            return JSONResponse(content=result)

    raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")


@app.get("/api/events/{event_id}/reports")
async def get_event_reports(event_id: str):
    """Get generated reports for a specific event."""
    reports_dir = Path("reports") / event_id
    if not reports_dir.exists():
        raise HTTPException(status_code=404, detail=f"No reports found for event {event_id}.")

    reports = {}
    for report_file in reports_dir.glob("*.txt"):
        reports[report_file.stem] = report_file.read_text(encoding="utf-8")

    return JSONResponse(content={"event_id": event_id, "reports": reports})


@app.post("/api/trigger")
async def trigger_pipeline(body: dict = None):
    """Manually trigger the pipeline in a background thread for live updates."""
    source = (body or {}).get("source", "USGS")

    # Import here to avoid circular imports
    from orchestrator import PipelineOrchestrator

    def _run():
        orchestrator = PipelineOrchestrator(on_state_change=on_pipeline_state_change)
        return orchestrator.run_pipeline(source=source)

    try:
        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(None, _run)
        if state:
            store_pipeline_result(state)
            # Broadcast completion with event data
            await broadcast_to_clients({
                "type": "pipeline_completed",
                "data": {"event_id": state["event"]["event_id"]},
            })
            return JSONResponse(content={
                "status": "completed",
                "event_id": state["event"]["event_id"],
            })
        else:
            return JSONResponse(content={
                "status": "filtered",
                "message": "Event was filtered (below threshold or duplicate).",
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------
@app.websocket("/ws/live")
async def websocket_endpoint(ws: WebSocket):
    """Real-time pipeline updates via WebSocket."""
    await ws.accept()
    active_websockets.add(ws)
    logger.info("WebSocket client connected. Total: %d", len(active_websockets))

    # Send current status on connect
    await ws.send_text(json.dumps({
        "type": "initial_state",
        "data": {
            "pipeline": pipeline_status,
            "mqtt": mqtt_status,
            "events": pipeline_results[:10],  # Last 10 events
        },
    }, default=str))

    try:
        while True:
            # Keep connection alive, wait for client messages (ping/pong)
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        active_websockets.discard(ws)
        logger.info("WebSocket client disconnected. Total: %d", len(active_websockets))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_event_data(event_id: str) -> Optional[Dict[str, Any]]:
    """Load event data from reports directory."""
    reports_dir = Path("reports") / event_id
    if not reports_dir.exists():
        return None

    data: Dict[str, Any] = {"event_id": event_id, "reports": {}}

    for report_file in reports_dir.glob("*.txt"):
        data["reports"][report_file.stem] = report_file.read_text(encoding="utf-8")

    # Also check for pipeline state JSON
    state_file = reports_dir / "pipeline_state.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            data.update(state)
        except json.JSONDecodeError:
            pass

    return data


# ---------------------------------------------------------------------------
# Server startup
# ---------------------------------------------------------------------------
def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI server."""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    from config import API_HOST, API_PORT
    start_server(host=API_HOST, port=API_PORT)
