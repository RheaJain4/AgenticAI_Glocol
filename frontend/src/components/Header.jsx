export default function Header({ pipelineStatus, mqttStatus, wsConnected, onTrigger, loading }) {
  const pipelineState = pipelineStatus?.pipeline_state || 'idle';

  const getStatusDotClass = () => {
    if (pipelineState === 'running') return 'status-dot status-dot-running';
    if (pipelineState === 'completed') return 'status-dot status-dot-connected';
    if (pipelineState === 'error') return 'status-dot status-dot-disconnected';
    return 'status-dot status-dot-idle';
  };

  return (
    <header className="header app-header">
      <div className="header-brand">
        <div>
          <div className="header-logo">⚡ AgenticAI Glocol</div>
          <div className="header-subtitle">Emergency Intelligence Dashboard</div>
        </div>
      </div>

      <div className="header-status">
        <div className="header-status-item">
          <span className={getStatusDotClass()} />
          <span>Pipeline: {pipelineState}</span>
        </div>
        <div className="header-status-item">
          <span className={`status-dot ${mqttStatus?.connected ? 'status-dot-connected' : 'status-dot-disconnected'}`} />
          <span>MQTT</span>
        </div>
        <div className="header-status-item">
          <span className={`status-dot ${wsConnected ? 'status-dot-connected' : 'status-dot-disconnected'}`} />
          <span>Live</span>
        </div>
      </div>

      <div className="header-actions">
        <button
          className="btn btn-primary"
          onClick={() => onTrigger('USGS')}
          disabled={loading || pipelineState === 'running'}
        >
          {loading ? <span className="spinner" /> : <span className="btn-icon">▶</span>}
          Run Pipeline
        </button>
      </div>
    </header>
  );
}
