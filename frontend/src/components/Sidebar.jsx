import React from 'react';
import { 
  FileText, 
  BarChart2, 
  Sparkles, 
  UploadCloud, 
  Layers 
} from 'lucide-react';

export default function Sidebar({ currentScreen, onSelectScreen, onOpenUpload }) {
  return (
    <aside className="sidebar">
      {/* Kaagazy / SwasthiQ Logo Icon */}
      <div className="sidebar-logo" title="SwasthiQ Kaagazy">
        <Layers size={22} />
      </div>

      {/* Navigation Icons */}
      <nav className="sidebar-nav">
        <button
          className={`nav-item ${currentScreen === 'reconciliation' ? 'active' : ''}`}
          onClick={() => onSelectScreen('reconciliation')}
          aria-label="EOD Reconciliation"
        >
          <FileText size={20} />
          <span className="nav-tooltip">1. EOD Reconciliation</span>
        </button>

        <button
          className={`nav-item ${currentScreen === 'analytics' ? 'active' : ''}`}
          onClick={() => onSelectScreen('analytics')}
          aria-label="Analytics"
        >
          <BarChart2 size={20} />
          <span className="nav-tooltip">2. Analytics</span>
        </button>

        <button
          className={`nav-item ${currentScreen === 'narrative' ? 'active' : ''}`}
          onClick={() => onSelectScreen('narrative')}
          aria-label="AI Narrative Summary"
        >
          <Sparkles size={20} />
          <span className="nav-tooltip">3. AI Narrative Summary</span>
        </button>

        <div style={{ width: 28, height: 1, backgroundColor: 'var(--border-light)', margin: '8px 0' }} />

        <button
          className="nav-item"
          onClick={onOpenUpload}
          aria-label="Upload Billing Log"
        >
          <UploadCloud size={20} />
          <span className="nav-tooltip">Upload Billing Log</span>
        </button>
      </nav>
    </aside>
  );
}
