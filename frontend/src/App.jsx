import { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useApi } from './hooks/useApi';
import Header from './components/Header';
import EventTimeline from './components/EventTimeline';
import AlertHero from './components/AlertHero';
import PipelineTracker from './components/PipelineTracker';
import RiskGauge from './components/RiskGauge';
import OccupancyPanel from './components/OccupancyPanel';
import SurgeHotspots from './components/SurgeHotspots';
import ReportTabs from './components/ReportTabs';
import './App.css';

function App() {
  const [pipelineStatus, setPipelineStatus] = useState({
    pipeline_state: 'idle',
    current_agent: null,
    progress: 0,
    event_id: null,
  });
  const [events, setEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [mqttStatus, setMqttStatus] = useState({ running: false, connected: false });

  const wsUrl = `ws://${window.location.hostname}:8000/ws/live`;
  const { lastMessage, isConnected: wsConnected } = useWebSocket(wsUrl);
  const { fetchData, triggerPipeline, loading } = useApi();

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === 'initial_state') {
      setPipelineStatus(lastMessage.data.pipeline || {});
      setMqttStatus(lastMessage.data.mqtt || {});
      if (lastMessage.data.events?.length > 0) {
        setEvents(lastMessage.data.events);
        if (!selectedEvent) {
          loadEventDetails(lastMessage.data.events[0].event_id);
        }
      }
    } else if (lastMessage.type === 'pipeline_status') {
      setPipelineStatus(lastMessage.data);
      // Refresh events list when pipeline completes
      if (lastMessage.data.pipeline_state === 'completed') {
        refreshEvents();
      }
    }
  }, [lastMessage]);

  // Initial data load
  useEffect(() => {
    refreshEvents();
  }, []);

  const refreshEvents = async () => {
    const data = await fetchData('/events');
    if (data?.events) {
      setEvents(data.events);
      if (data.events.length > 0 && !selectedEvent) {
        loadEventDetails(data.events[0].event_id);
      }
    }
  };

  const loadEventDetails = async (eventId) => {
    const data = await fetchData(`/events/${eventId}`);
    if (data) {
      setSelectedEvent(data);
    }
    // Also load reports
    const reports = await fetchData(`/events/${eventId}/reports`);
    if (reports) {
      setSelectedEvent(prev => prev ? { ...prev, reports: reports.reports } : null);
    }
  };

  const handleTrigger = async (source) => {
    const result = await triggerPipeline(source);
    if (result) {
      refreshEvents();
    }
  };

  const handleEventSelect = (eventId) => {
    loadEventDetails(eventId);
  };

  return (
    <div className="app-layout">
      <Header
        pipelineStatus={pipelineStatus}
        mqttStatus={mqttStatus}
        wsConnected={wsConnected}
        onTrigger={handleTrigger}
        loading={loading}
      />
      <aside className="app-sidebar">
        <EventTimeline
          events={events}
          selectedEventId={selectedEvent?.event_id}
          onSelect={handleEventSelect}
        />
      </aside>
      <main className="app-main">
        <div className="dashboard-grid">
          <div className="dashboard-hero">
            <AlertHero event={selectedEvent} />
          </div>
          <div className="dashboard-metrics">
            <RiskGauge
              riskScore={selectedEvent?.risk?.risk_score}
              riskLevel={selectedEvent?.risk?.risk_level}
              dataQuality={selectedEvent?.risk?.data_quality}
            />
            <OccupancyPanel occupancy={selectedEvent?.occupancy} />
            <SurgeHotspots surge={selectedEvent?.surge} />
          </div>
          <div className="dashboard-pipeline">
            <PipelineTracker status={pipelineStatus} />
          </div>
          <div className="dashboard-reports">
            <ReportTabs reports={selectedEvent?.reports} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
