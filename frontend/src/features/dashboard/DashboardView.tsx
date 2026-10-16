import React from 'react';
import type { RunSummary, ConfigStatus } from '../../lib/api';
import { CheckCircle2, XCircle, AlertTriangle, Play, PlusCircle, ArrowRight, ShieldCheck, Terminal, Cpu } from 'lucide-react';

interface DashboardViewProps {
  runs: RunSummary[];
  config: ConfigStatus | null;
  onSelectRun: (runId: string) => void;
  onTriggerDemo: () => void;
  onNewRepair: () => void;
  isTriggeringDemo: boolean;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  runs,
  config,
  onSelectRun,
  onTriggerDemo,
  onNewRepair,
  isTriggeringDemo,
}) => {
  const totalRuns = runs.length;
  const verifiedRuns = runs.filter((r) => r.verified).length;
  const passedRuns = runs.filter((r) => r.status === 'passed').length;
  const verificationRate = totalRuns > 0 ? Math.round((verifiedRuns / totalRuns) * 100) : 100;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Hero Quickstart Banner */}
      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, rgba(18, 25, 41, 0.95) 0%, rgba(14, 28, 54, 0.95) 100%)',
          borderColor: 'rgba(59, 130, 246, 0.25)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '20px',
        }}
      >
        <div style={{ maxWidth: '680px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#38bdf8', fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px' }}>
            <ShieldCheck size={16} />
            <span>Autonomous Bug Fixing With Verifiable Evidence</span>
          </div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '8px', letterSpacing: '-0.02em' }}>
            AI Code Repairs You Can Actually Trust
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.6 }}>
            Generated code is not proof that a bug is fixed. ProofPatch autonomously reproduces defects with real test commands, synthesizes surgical patches, runs regression suites, and compiles immutable execution evidence.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button
            className="btn-primary"
            onClick={onTriggerDemo}
            disabled={isTriggeringDemo}
            style={{ padding: '12px 20px', fontSize: '0.95rem' }}
          >
            <Play size={16} fill="currentColor" />
            <span>{isTriggeringDemo ? 'Running Offline Demo...' : 'Launch Zero-Credit Demo'}</span>
          </button>

          <button
            className="btn-secondary"
            onClick={onNewRepair}
            style={{ padding: '12px 20px', fontSize: '0.95rem' }}
          >
            <PlusCircle size={16} />
            <span>Custom Repair</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Total Repair Runs</span>
          <span className="metric-value">{totalRuns}</span>
          <span className="metric-desc">Autonomous workflows initiated</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Verified Fixes</span>
          <span className="metric-value" style={{ color: 'var(--status-passed)' }}>
            {verifiedRuns}
          </span>
          <span className="metric-desc">Independent audit checks passed</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Verification Rate</span>
          <span className="metric-value">{verificationRate}%</span>
          <span className="metric-desc">{passedRuns} test suites green</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Execution Environment</span>
          <span className="metric-value" style={{ fontSize: '1.3rem', color: '#38bdf8' }}>
            {config?.mode.toUpperCase() || 'DEMO'}
          </span>
          <span className="metric-desc">
            {config?.mode === 'demo' ? 'Zero external tokens consumed' : 'Nebius + Tavily Live'}
          </span>
        </div>
      </div>

      {/* Provider Status Pill Strip */}
      {config && (
        <div
          className="card"
          style={{
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px',
            fontSize: '0.88rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={16} color="var(--color-brand)" />
            <span style={{ fontWeight: 600 }}>Inference Adapter:</span>
            <span style={{ color: config.nebius_configured ? 'var(--status-passed)' : 'var(--text-muted)' }}>
              {config.nebius_configured
                ? `Nebius (${config.nebius_model})`
                : 'Deterministic Sample Mode (Nebius ready)'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={16} color="var(--color-cyan)" />
            <span style={{ fontWeight: 600 }}>External Research:</span>
            <span style={{ color: config.tavily_configured ? 'var(--status-passed)' : 'var(--text-muted)' }}>
              {config.tavily_configured ? 'Tavily Search Active' : 'Disabled (Zero Credits)'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontWeight: 600 }}>Docker Sandbox:</span>
            <span className={`badge ${config.docker_available ? 'badge-passed' : 'badge-neutral'}`}>
              {config.docker_available ? 'DOCKER ACTIVE' : 'HOST ISOLATED'}
            </span>
          </div>
        </div>
      )}

      {/* Recent Runs Table */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <span>Recent Repair Runs</span>
            <span className="badge badge-neutral">{runs.length}</span>
          </h2>
          <button className="btn-secondary" onClick={onNewRepair} style={{ padding: '6px 12px', fontSize: '0.82rem' }}>
            <PlusCircle size={14} />
            <span>New Run</span>
          </button>
        </div>

        {runs.length === 0 ? (
          <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <p style={{ fontSize: '1.05rem', marginBottom: '12px', color: 'var(--text-secondary)' }}>
              No repair runs recorded yet.
            </p>
            <p style={{ fontSize: '0.88rem', marginBottom: '20px' }}>
              Launch the bundled deterministic demo to see ProofPatch reproduce a boundary bug, apply a surgical patch, and audit the results.
            </p>
            <button className="btn-primary" onClick={onTriggerDemo} disabled={isTriggeringDemo}>
              <Play size={15} fill="currentColor" />
              <span>Launch Demo Run</span>
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Issue / Title</th>
                  <th>Mode</th>
                  <th>Status</th>
                  <th>Reproduction</th>
                  <th>Regression Tests</th>
                  <th>Audit Seal</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} style={{ cursor: 'pointer' }} onClick={() => onSelectRun(run.id)}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-brand)' }}>
                      {run.id}
                    </td>
                    <td style={{ maxWidth: '320px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {run.bug_title}
                    </td>
                    <td>
                      <span className={`badge ${run.mode === 'demo' ? 'badge-neutral' : 'badge-warning'}`}>
                        {run.mode}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          run.status === 'passed'
                            ? 'badge-passed'
                            : run.status === 'running'
                            ? 'badge-running'
                            : 'badge-failed'
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td>
                      {run.reproduced ? (
                        <span style={{ color: 'var(--status-passed)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle2 size={14} />
                          <span>Reproduced</span>
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <XCircle size={14} />
                          <span>Inconclusive</span>
                        </span>
                      )}
                    </td>
                    <td>
                      {run.test_passed ? (
                        <span style={{ color: 'var(--status-passed)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle2 size={14} />
                          <span>Passed</span>
                        </span>
                      ) : (
                        <span style={{ color: 'var(--status-failed)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <AlertTriangle size={14} />
                          <span>Failed</span>
                        </span>
                      )}
                    </td>
                    <td>
                      {run.verified ? (
                        <span className="badge badge-passed">VERIFIED</span>
                      ) : (
                        <span className="badge badge-warning">PARTIAL</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn-secondary"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectRun(run.id);
                        }}
                        style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                      >
                        <span>View</span>
                        <ArrowRight size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
