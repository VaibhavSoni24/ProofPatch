import React from 'react';
import { ShieldCheck, Play, History, FileText, Settings, PlusCircle, LayoutDashboard, Cpu } from 'lucide-react';

interface HeaderProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onTriggerDemo: () => void;
  isTriggeringDemo: boolean;
  mode: string;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onSelectTab,
  onTriggerDemo,
  isTriggeringDemo,
  mode,
}) => {
  return (
    <header>
      {/* Global Transparent Demo Banner */}
      <div className="demo-banner">
        <div>
          <strong>LOCAL DEMO MODE</strong>
          <span>Deterministic local execution — zero external AI inference API calls, zero credit spend.</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem' }}>
          <Cpu size={14} />
          <span>Nebius & Tavily providers are implemented with mock verification.</span>
        </div>
      </div>

      {/* Main Navbar */}
      <nav className="navbar">
        <div className="nav-brand" onClick={() => onSelectTab('dashboard')}>
          <div className="nav-logo-icon">
            <ShieldCheck size={20} />
          </div>
          <div>
            <div className="nav-title">ProofPatch</div>
          </div>
          <div className="nav-tagline">AI repairs you can verify.</div>
        </div>

        <div className="nav-links">
          <button
            className={`nav-btn ${currentTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => onSelectTab('dashboard')}
          >
            <LayoutDashboard size={16} />
            <span>Dashboard</span>
          </button>

          <button
            className={`nav-btn ${currentTab === 'new-repair' ? 'active' : ''}`}
            onClick={() => onSelectTab('new-repair')}
          >
            <PlusCircle size={16} />
            <span>New Repair</span>
          </button>

          <button
            className={`nav-btn ${currentTab === 'runs' ? 'active' : ''}`}
            onClick={() => onSelectTab('runs')}
          >
            <History size={16} />
            <span>Run History</span>
          </button>

          <button
            className={`nav-btn ${currentTab === 'evidence' ? 'active' : ''}`}
            onClick={() => onSelectTab('evidence')}
          >
            <FileText size={16} />
            <span>Evidence Audit</span>
          </button>

          <button
            className={`nav-btn ${currentTab === 'settings' ? 'active' : ''}`}
            onClick={() => onSelectTab('settings')}
          >
            <Settings size={16} />
            <span>Settings</span>
          </button>
        </div>

        <div className="nav-actions">
          <span className={`badge ${mode === 'demo' ? 'badge-running' : 'badge-warning'}`}>
            {mode.toUpperCase()} MODE
          </span>

          <button
            className="btn-primary"
            onClick={onTriggerDemo}
            disabled={isTriggeringDemo}
          >
            <Play size={15} fill="currentColor" />
            <span>{isTriggeringDemo ? 'Executing Demo...' : 'Run Demo Repair'}</span>
          </button>
        </div>
      </nav>
    </header>
  );
};
