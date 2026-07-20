export default function AlertHero({ event }) {
  if (!event || !event.event_id) {
    return (
      <div className="alert-hero severity-low">
        <div className="empty-state">
          <div className="empty-icon">🛰️</div>
          <div className="empty-text">No earthquake event loaded. Run the pipeline or select an event from the timeline.</div>
        </div>
      </div>
    );
  }

  const ev = event.event || event;
  const severity = (ev.severity || 'medium').toLowerCase();
  const magnitude = ev.magnitude != null ? Number(ev.magnitude).toFixed(1) : '?';

  return (
    <div className={`alert-hero severity-${severity} animate-slide-up`}>
      <div className="hero-top">
        <div>
          <div className={`hero-magnitude severity-${severity}`}>
            M{magnitude}
          </div>
          <div className="hero-label">{ev.event_type || 'Earthquake'}</div>
        </div>
        <div className="flex flex-col items-center gap-sm">
          <span className={`badge badge-${severity}`}>
            ● {(ev.severity || 'UNKNOWN').toUpperCase()}
          </span>
          {event.risk?.data_quality === 'estimated' && (
            <span className="badge badge-estimated">⚠ Estimated Data</span>
          )}
        </div>
      </div>

      <div className="hero-details">
        <div className="hero-detail">
          <span className="hero-detail-label">Location</span>
          <span className="hero-detail-value">{ev.location || 'Unknown'}</span>
        </div>
        <div className="hero-detail">
          <span className="hero-detail-label">Coordinates</span>
          <span className="hero-detail-value mono">
            {ev.latitude != null ? `${ev.latitude.toFixed(4)}°, ${ev.longitude.toFixed(4)}°` : 'N/A'}
          </span>
        </div>
        <div className="hero-detail">
          <span className="hero-detail-label">Event ID</span>
          <span className="hero-detail-value mono">{ev.event_id || event.event_id}</span>
        </div>
        {event.research && (
          <>
            <div className="hero-detail">
              <span className="hero-detail-label">Affected Radius</span>
              <span className="hero-detail-value mono">
                {event.research.affected_radius_km} km
              </span>
            </div>
            <div className="hero-detail">
              <span className="hero-detail-label">Infrastructure</span>
              <span className="hero-detail-value">
                🏫 {event.research.schools} · 🏥 {event.research.hospitals} · 🚉 {event.research.transit_stations}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
