export default function EventTimeline({ events, selectedEventId, onSelect }) {
  if (!events || events.length === 0) {
    return (
      <div className="sidebar">
        <div className="sidebar-title">Event History</div>
        <div className="empty-state">
          <div className="empty-icon">🌍</div>
          <div className="empty-text">No events processed yet. Trigger the pipeline to get started.</div>
        </div>
      </div>
    );
  }

  const getSeverityClass = (severity) => {
    const s = (severity || '').toLowerCase();
    if (s === 'critical') return 'badge-critical';
    if (s === 'high') return 'badge-high';
    if (s === 'medium') return 'badge-medium';
    return 'badge-low';
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="sidebar">
      <div className="sidebar-title">Event History ({events.length})</div>
      {events.map((event, index) => (
        <div
          key={event.event_id || index}
          className={`event-item animate-slide-up ${
            selectedEventId === event.event_id ? 'active' : ''
          }`}
          style={{ animationDelay: `${index * 50}ms` }}
          onClick={() => onSelect(event.event_id)}
        >
          <div className="event-item-header">
            <span className="event-item-mag">
              M{event.magnitude != null ? Number(event.magnitude).toFixed(1) : '?'}
            </span>
            <span className={`badge ${getSeverityClass(event.severity)}`}>
              {event.severity || 'N/A'}
            </span>
          </div>
          <div className="event-item-location">
            {event.location || `(${event.latitude?.toFixed(2)}, ${event.longitude?.toFixed(2)})`}
          </div>
          <div className="event-item-time">{formatTime(event.timestamp)}</div>
        </div>
      ))}
    </div>
  );
}
