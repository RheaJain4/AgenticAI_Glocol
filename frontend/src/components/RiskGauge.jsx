export default function RiskGauge({ riskScore, riskLevel, dataQuality }) {
  const score = riskScore != null ? Math.round(riskScore) : 0;
  const level = riskLevel || 'N/A';
  const circumference = 283; // 2 * π * 45
  const offset = circumference - (score / 100) * circumference;

  const getColor = () => {
    if (score >= 80) return 'var(--severity-critical)';
    if (score >= 60) return 'var(--severity-high)';
    if (score >= 40) return 'var(--severity-medium)';
    return 'var(--severity-low)';
  };

  const getSeverityClass = () => {
    if (score >= 80) return 'badge-critical';
    if (score >= 60) return 'badge-high';
    if (score >= 40) return 'badge-medium';
    return 'badge-low';
  };

  return (
    <div className="card animate-slide-up">
      <div className="card-header">
        <span className="card-title">Risk Score</span>
        <span className={`badge ${getSeverityClass()}`}>{level}</span>
      </div>
      <div className="risk-gauge-container">
        <svg className="risk-gauge-svg" viewBox="0 0 100 100">
          <circle className="risk-gauge-bg" cx="50" cy="50" r="45" />
          <circle
            className="risk-gauge-fill"
            cx="50"
            cy="50"
            r="45"
            stroke={getColor()}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ animation: 'gauge-fill 1.5s ease-out' }}
          />
          <text className="risk-gauge-text" x="50" y="47">{score}</text>
          <text className="risk-gauge-label" x="50" y="62">/ 100</text>
        </svg>
        {dataQuality === 'estimated' && (
          <span className="badge badge-estimated" style={{ fontSize: '0.65rem' }}>
            ⚠ Based on estimated occupancy
          </span>
        )}
      </div>
    </div>
  );
}
