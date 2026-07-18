"""
Pipeline Orchestrator
======================
Smart orchestrator that replaces the procedural main() logic.
Handles source selection, validation gates, deduplication,
sequential agent execution, and state tracking with event emission.
"""

import time
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from config import MAGNITUDE_THRESHOLD, is_mqtt_enabled

from agents.Agent1_Ingestion import Agent1Ingestion
from agents.Agent2_Research import Agent2Research
from agents.Agent3_Occupancy import OccupancyAgent
from agents.Agent4_RiskAssesment import RiskAssessmentAgent
from agents.Agent5_CrowdSurgePrediction import CrowdSurgePredictionAgent
from agents.Agent6_Report import ReportAgent

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the 6-agent pipeline with:
    - Source selection (MQTT → USGS → CAP)
    - Magnitude validation gate (≥ 4.5)
    - Event deduplication (30-minute window)
    - Sequential agent execution with error handling
    - State tracking and event emission for frontend updates
    """

    def __init__(
        self,
        on_state_change: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Args:
            on_state_change: Callback fired whenever pipeline status changes.
                             Used by WebSocket to push updates to the frontend.
        """
        self._on_state_change = on_state_change
        self._processed_events: Dict[str, float] = {}  # event_id → timestamp
        self._dedup_window: int = 1800  # 30 minutes
        self._current_status: Dict[str, Any] = {
            "pipeline_state": "idle",
            "current_agent": None,
            "progress": 0,
            "event_id": None,
            "error": None,
        }
        self._latest_result: Optional[Dict[str, Any]] = None

        # Initialize agents
        self._agent1 = Agent1Ingestion()
        self._agent2 = Agent2Research()
        self._agent3 = OccupancyAgent()
        self._agent4 = RiskAssessmentAgent()
        self._agent5 = CrowdSurgePredictionAgent()

    # ------------------------------------------------------------------
    # Status Management
    # ------------------------------------------------------------------
    def _update_status(
        self,
        pipeline_state: str,
        current_agent: Optional[str] = None,
        progress: int = 0,
        event_id: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self._current_status = {
            "pipeline_state": pipeline_state,
            "current_agent": current_agent,
            "progress": progress,
            "event_id": event_id or self._current_status.get("event_id"),
            "error": error,
            "timestamp": time.time(),
        }
        logger.info(
            "Pipeline status: %s | Agent: %s | Progress: %d%%",
            pipeline_state,
            current_agent or "-",
            progress,
        )
        if self._on_state_change:
            try:
                self._on_state_change(self._current_status.copy())
            except Exception as e:
                logger.error("State change callback failed: %s", e)

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Return current pipeline status for API/frontend."""
        return self._current_status.copy()

    def get_latest_result(self) -> Optional[Dict[str, Any]]:
        """Return the latest completed pipeline result."""
        return self._latest_result

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------
    def _is_recently_processed(self, event_id: str) -> bool:
        """Check if this event was already processed within the dedup window."""
        now = time.time()

        # Cleanup old entries
        stale = [k for k, t in self._processed_events.items() if now - t > self._dedup_window]
        for k in stale:
            del self._processed_events[k]

        if event_id in self._processed_events:
            logger.info("Event %s already processed recently — skipping.", event_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Source Selection
    # ------------------------------------------------------------------
    def _select_source(self, preferred_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Try sources in priority order: preferred → USGS → CAP.
        Returns the Agent 1 output (state with event + meta).
        """
        sources = []
        if preferred_source:
            sources.append(preferred_source)
        sources.extend(["USGS", "CAP"])
        # Remove duplicates while preserving order
        seen = set()
        sources = [s for s in sources if not (s in seen or seen.add(s))]

        last_error = None
        for source in sources:
            try:
                logger.info("Trying source: %s", source)
                result = self._agent1.process(source=source)
                if result is not None:
                    return result
                else:
                    logger.info("Source %s successfully processed but filtered event (below threshold).", source)
                    return None
            except NotImplementedError:
                logger.warning("Source %s not implemented.", source)
                continue
            except Exception as e:
                logger.warning("Source %s failed: %s", source, e)
                last_error = e
                continue

        raise RuntimeError(
            f"All sources failed. Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # Pipeline Execution
    # ------------------------------------------------------------------
    def run_pipeline(
        self,
        alert_data: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute the full 6-agent pipeline.

        Args:
            alert_data: Pre-parsed MQTT alert fields (if triggered by MQTT).
            source: Preferred data source ("USGS", "CAP", "MQTT").

        Returns:
            Full pipeline state dict, or None if event was filtered/deduplicated.
        """
        self._update_status("starting", progress=0)

        try:
            # -----------------------------------------------------------
            # Agent 1: Ingestion
            # -----------------------------------------------------------
            self._update_status("running", current_agent="Agent 1 - Ingestion", progress=10)

            if alert_data:
                # MQTT path: convert alert_data to payload, then process
                payload = self._agent1.fetch_mqtt(alert_data)
                state = self._agent1.process(payload=payload)
            elif source:
                state = self._select_source(preferred_source=source)
            else:
                state = self._select_source()

            if state is None:
                self._update_status("filtered", progress=100)
                logger.info("Event filtered (below magnitude threshold).")
                return None

            event_id = state["event"]["event_id"]
            self._update_status(
                "running", current_agent="Agent 1 - Ingestion",
                progress=15, event_id=event_id,
            )

            # Deduplication
            if self._is_recently_processed(event_id):
                self._update_status("deduplicated", progress=100, event_id=event_id)
                return None

            logger.info("Processing event: %s", event_id)

            # -----------------------------------------------------------
            # Agent 2: Research
            # -----------------------------------------------------------
            self._update_status("running", current_agent="Agent 2 - Research", progress=25, event_id=event_id)
            state = self._agent2.process(state)

            # -----------------------------------------------------------
            # Agent 3: Occupancy
            # -----------------------------------------------------------
            self._update_status("running", current_agent="Agent 3 - Occupancy", progress=40, event_id=event_id)
            agent3_input = {
                "event_id": state["event"]["event_id"],
                "latitude": state["event"]["latitude"],
                "longitude": state["event"]["longitude"],
                "affected_radius_km": state["research"]["affected_radius_km"],
                # Pass research data for sensorless estimation fallback
                "research": state.get("research", {}),
                "event": state.get("event", {}),
            }
            state["occupancy"] = self._agent3.run(agent3_input)

            # -----------------------------------------------------------
            # Agent 4: Risk Assessment
            # -----------------------------------------------------------
            self._update_status("running", current_agent="Agent 4 - Risk Assessment", progress=55, event_id=event_id)
            state["risk"] = self._agent4.assess_risk(
                state["event"],
                state["research"],
                state["occupancy"],
            )

            # -----------------------------------------------------------
            # Agent 5: Crowd Surge Prediction
            # -----------------------------------------------------------
            self._update_status("running", current_agent="Agent 5 - Crowd Surge", progress=70, event_id=event_id)
            state = self._agent5.run(state)

            # -----------------------------------------------------------
            # Agent 6: Report Generation
            # -----------------------------------------------------------
            self._update_status("running", current_agent="Agent 6 - Reports", progress=85, event_id=event_id)
            agent6 = ReportAgent(state)
            agent6.generate_executive_summary()
            agent6.generate_technical_report()
            agent6.generate_news_report()
            agent6.generate_video_script()
            agent6.save_reports()

            # Attach reports to state
            state["reports"] = {
                "executive_summary": agent6.executive_summary,
                "technical_report": agent6.technical_report,
                "news_report": agent6.news_report,
                "video_script": agent6.video_script,
            }

            # Mark as processed
            self._processed_events[event_id] = time.time()
            self._latest_result = state
            self._update_status("completed", current_agent=None, progress=100, event_id=event_id)

            return state

        except Exception as e:
            logger.error("Pipeline failed: %s", e, exc_info=True)
            self._update_status("error", error=str(e), progress=0)
            raise

    # ------------------------------------------------------------------
    # MQTT Integration Helper
    # ------------------------------------------------------------------
    def handle_mqtt_alert(self, alert_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Callback for the MQTT listener. Runs the full pipeline
        with the parsed alert data.
        """
        logger.info(
            "MQTT alert received: M%.1f at (%.4f, %.4f)",
            alert_data.get("magnitude", 0),
            alert_data.get("latitude", 0),
            alert_data.get("longitude", 0),
        )
        return self.run_pipeline(alert_data=alert_data)
