const AGENTS = [
  { id: 1, name: 'Ingestion', key: 'Agent 1 - Ingestion' },
  { id: 2, name: 'Research', key: 'Agent 2 - Research' },
  { id: 3, name: 'Occupancy', key: 'Agent 3 - Occupancy' },
  { id: 4, name: 'Risk', key: 'Agent 4 - Risk Assessment' },
  { id: 5, name: 'Surge', key: 'Agent 5 - Crowd Surge' },
  { id: 6, name: 'Reports', key: 'Agent 6 - Reports' },
];

export default function PipelineTracker({ status }) {
  const currentAgent = status?.current_agent || '';
  const pipelineState = status?.pipeline_state || 'idle';
  const progress = status?.progress || 0;

  const getStepState = (agent) => {
    if (pipelineState === 'idle') return 'idle';
    if (pipelineState === 'error') {
      if (currentAgent === agent.key) return 'error';
    }
    if (pipelineState === 'completed') return 'completed';

    // Determine based on progress thresholds
    const thresholds = [10, 25, 40, 55, 70, 85];
    const agentIndex = agent.id - 1;
    const agentThreshold = thresholds[agentIndex];

    if (currentAgent === agent.key) return 'running';
    if (progress > agentThreshold + 10) return 'completed';
    if (progress >= agentThreshold) return 'running';
    return 'idle';
  };

  const getConnectorState = (agent) => {
    const state = getStepState(agent);
    if (state === 'completed') return 'completed';
    if (state === 'running') return 'running';
    return '';
  };

  return (
    <div className="card animate-slide-up">
      <div className="card-header">
        <span className="card-title">Pipeline Progress</span>
        {pipelineState === 'running' && (
          <span className="badge badge-sensor">
            <span className="spinner" style={{ width: 10, height: 10 }} />
            Processing...
          </span>
        )}
        {pipelineState === 'completed' && (
          <span className="badge badge-low">✓ Complete</span>
        )}
      </div>

      <div className="pipeline-track">
        {AGENTS.map((agent, index) => (
          <div key={agent.id} className="pipeline-step">
            <div className="pipeline-node">
              <div className={`pipeline-dot ${getStepState(agent)}`}>
                {getStepState(agent) === 'completed' ? '✓' : agent.id}
              </div>
              <span className="pipeline-label">{agent.name}</span>
            </div>
            {index < AGENTS.length - 1 && (
              <div className={`pipeline-connector ${getConnectorState(agent)}`} />
            )}
          </div>
        ))}
      </div>

      {status?.event_id && (
        <div style={{ marginTop: 'var(--space-sm)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          Event: <span className="mono">{status.event_id}</span>
        </div>
      )}
    </div>
  );
}
