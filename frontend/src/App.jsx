import { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useApi } from './hooks/useApi';
import Header from './components/Header';
import EventTimeline from './components/EventTimeline';
import AlertHero from './components/AlertHero';
import PipelineTracker from './components/PipelineTracker';
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
    } else if (lastMessage.type === 'pipeline_completed') {
      // Pipeline finished — set completed, then reset to idle after 3s
      setPipelineStatus(prev => ({ ...prev, pipeline_state: 'completed', progress: 100 }));
      refreshEvents();
      if (lastMessage.data?.event_id) {
        loadEventDetails(lastMessage.data.event_id);
      }
      setTimeout(() => {
        setPipelineStatus(prev => ({ ...prev, pipeline_state: 'idle', progress: 0, current_agent: null }));
      }, 3000);
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
