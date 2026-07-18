export default function SurgeHotspots({ surge }) {
  if (!surge) {
    return (
      <div className="card animate-slide-up" style={{ animationDelay: '200ms' }}>
        <div className="card-header">
          <span className="card-title">Crowd Surge</span>
        </div>
        <div className="empty-state" style={{ padding: 'var(--space-lg)' }}>
          <div className="empty-text text-muted">No surge prediction data</div>
        </div>
      </div>
    );
  }

  const hotspots = surge.predicted_hotspots || [];
  const probability = surge.congestion_probability != null ? surge.congestion_probability : 0;
  const confidence = surge.confidence || 'MEDIUM';
  const model = surge.prediction_model || 'Unknown';
  const timeWindow = surge.time_window_minutes || 30;

  const getProbColor = () => {
    if (probability >= 0.7) return 'var(--accent-red)';
    if (probability >= 0.4) return 'var(--accent-amber)';
    return 'var(--accent-green)';
  };

  return (
    <div className="card animate-slide-up" style={{ animationDelay: '200ms' }}>
      <div className="card-header">
        <span className="card-title">Crowd Surge</span>
        <span className="badge badge-medium">{timeWindow}min window</span>
      </div>

      <div className="flex items-center gap-md" style={{ marginBottom: 'var(--space-md)' }}>
        <div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>
            Congestion Probability
          </span>
          <span className="mono" style={{ fontSize: '1.5rem', fontWeight: 700, color: getProbColor() }}>
            {Math.round(probability * 100)}%
          </span>
        </div>
        <div className="prob-bar" style={{ flex: 1 }}>
          <div className="prob-fill" style={{ width: `${probability * 100}%`, background: getProbColor() }} />
        </div>
      </div>

      {hotspots.length > 0 && (
        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 'var(--space-sm)' }}>
            Predicted Hotspots
          </div>
          {hotspots.slice(0, 5).map((hotspot, i) => (
            <div key={i} className="hotspot-item">
              <span className="hotspot-name">🔴 {hotspot}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 'var(--space-md)', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
        Model: {model} · Confidence: {confidence}
      </div>
    </div>
  );
}
