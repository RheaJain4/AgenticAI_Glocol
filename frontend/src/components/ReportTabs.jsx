import { useState } from 'react';

const TABS = [
  { key: 'executive_summary', label: 'Executive Summary', icon: '📋' },
  { key: 'technical_report', label: 'Technical', icon: '📊' },
  { key: 'news_report', label: 'News', icon: '📰' },
  { key: 'video_script', label: 'Video Script', icon: '🎬' },
  { key: 'broadcast_script', label: 'Broadcast', icon: '📡' },
];

export default function ReportTabs({ reports }) {
  const [activeTab, setActiveTab] = useState('executive_summary');

  if (!reports || Object.keys(reports).length === 0) {
    return (
      <div className="card animate-slide-up">
        <div className="card-header">
          <span className="card-title">Generated Reports</span>
        </div>
        <div className="empty-state" style={{ padding: 'var(--space-xl)' }}>
          <div className="empty-icon">📄</div>
          <div className="empty-text text-muted">No reports generated yet. Reports appear here after the pipeline completes.</div>
        </div>
      </div>
    );
  }

  // Filter tabs to only show available reports
  const availableTabs = TABS.filter(tab => reports[tab.key]);

  return (
    <div className="card animate-slide-up">
      <div className="card-header">
        <span className="card-title">Generated Reports</span>
        <span className="badge badge-low">{availableTabs.length} reports</span>
      </div>

      <div className="report-tabs-nav">
        {availableTabs.map(tab => (
          <button
            key={tab.key}
            className={`report-tab ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div className="report-content">
        {reports[activeTab] || 'Select a report tab to view content.'}
      </div>
    </div>
  );
}
