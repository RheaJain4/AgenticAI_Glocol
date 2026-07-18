export default function OccupancyPanel({ occupancy }) {
  if (!occupancy) {
    return (
      <div className="card animate-slide-up" style={{ animationDelay: '100ms' }}>
        <div className="card-header">
          <span className="card-title">Occupancy</span>
        </div>
        <div className="empty-state" style={{ padding: 'var(--space-lg)' }}>
          <div className="empty-text text-muted">No occupancy data</div>
        </div>
      </div>
    );
  }

  const method = occupancy.estimation_method || 'sensor';
  const confidence = occupancy.confidence_score != null ? occupancy.confidence_score : 1.0;
  const isSensor = method === 'sensor';
  const population = occupancy.estimated_population || 0;

  const getConfidenceColor = () => {
    if (confidence >= 0.8) return 'var(--accent-green)';
    if (confidence >= 0.5) return 'var(--accent-amber)';
    return 'var(--accent-red)';
  };

  return (
    <div className="card animate-slide-up" style={{ animationDelay: '100ms' }}>
      <div className="card-header">
        <span className="card-title">Occupancy</span>
        <span className={`badge ${isSensor ? 'badge-sensor' : 'badge-estimated'}`}>
          {isSensor ? '📡 Sensor' : '🧠 Estimated'}
        </span>
      </div>

      <div className="occupancy-stat">
        <span className="occupancy-number">{population.toLocaleString()}</span>
        <span className="occupancy-unit">people</span>
      </div>

      <div>
        <div className="flex justify-between" style={{ marginBottom: '4px' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Confidence
          </span>
          <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
            {Math.round(confidence * 100)}%
          </span>
        </div>
        <div className="confidence-bar">
          <div
            className="confidence-fill"
            style={{
              width: `${confidence * 100}%`,
              background: getConfidenceColor(),
            }}
          />
        </div>
      </div>

      {occupancy.high_density_zones?.length > 0 && (
        <ul className="zones-list">
          {occupancy.high_density_zones.slice(0, 5).map((zone, i) => (
            <li key={i}>📍 {zone}</li>
          ))}
        </ul>
      )}

      {occupancy.sensor_count != null && (
        <div style={{ marginTop: 'var(--space-sm)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          Sensors in range: {occupancy.sensor_count}
        </div>
      )}
    </div>
  );
}
