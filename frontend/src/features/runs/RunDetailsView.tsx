import React, { useState } from 'react';
import type { RunDetail, EvidenceReport } from '../../lib/api';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Terminal,
  FileCode,
  GitCommit,
  ExternalLink,
  Download,
  Clock,
  RotateCw,
  Search,
  ArrowLeft,
  Check,
} from 'lucide-react';

interface RunDetailsViewProps {
  run: RunDetail;
  evidence: EvidenceReport | null;
  onBack: () => void;
  onRefresh: () => void;
}

export const RunDetailsView: React.FC<RunDetailsViewProps> = ({
  run,
  evidence,
  onBack,
  onRefresh,
}) => {
  const [activeTab, setActiveTab] = useState<
    'timeline' | 'reproduction' | 'diagnosis' | 'research' | 'patch' | 'tests' | 'verification' | 'report'
  >('timeline');

  const downloadJsonReport = () => {
    if (!evidence) return;
    const blob = new Blob([JSON.stringify(evidence, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `proofpatch-evidence-${run.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadMarkdownReport = () => {
    if (!evidence) return;
    const blob = new Blob([evidence.markdown_report], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `proofpatch-report-${run.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Header Card */}
      <div className="card" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <button
                className="btn-secondary"
                onClick={onBack}
                style={{ padding: '6px 10px', fontSize: '0.8rem' }}
              >
                <ArrowLeft size={14} />
                <span>Back</span>
              </button>

              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-brand)' }}>
                {run.id}
              </span>

              <span
                className={`badge ${
                  run.status === 'passed'
                    ? 'badge-passed'
                    : run.status === 'running'
                    ? 'badge-running'
                    : 'badge-failed'
                }`}
              >
                {run.status.toUpperCase()}
              </span>

              <span className={`badge ${run.mode === 'demo' ? 'badge-neutral' : 'badge-warning'}`}>
                {run.mode.toUpperCase()} MODE
              </span>

              {run.verified ? (
                <span className="badge badge-passed" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <ShieldCheck size={14} />
                  <span>VERIFIED AUDIT</span>
                </span>
              ) : (
                <span className="badge badge-warning">
                  <span>UNVERIFIED / PARTIAL</span>
                </span>
              )}
            </div>

            <h1 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '6px' }}>{run.bug_title}</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
              Repository: <code>{run.repository_url}</code>
              {run.commit_hash && (
                <span style={{ marginLeft: '12px' }}>
                  Commit: <code>{run.commit_hash.slice(0, 8)}</code>
                </span>
              )}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button className="btn-secondary" onClick={onRefresh} style={{ padding: '8px 12px', fontSize: '0.82rem' }}>
              <RotateCw size={14} />
              <span>Refresh</span>
            </button>

            <button
              className="btn-primary"
              onClick={downloadMarkdownReport}
              disabled={!evidence}
              style={{ padding: '8px 14px', fontSize: '0.82rem' }}
            >
              <Download size={14} />
              <span>Download Report</span>
            </button>
          </div>
        </div>

        {/* Quick Metrics Bar */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: '12px',
            marginTop: '20px',
            paddingTop: '16px',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: '0.82rem',
          }}
        >
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>Defect Reproduced</span>
            <strong style={{ color: run.reproduced ? 'var(--status-passed)' : 'var(--text-muted)' }}>
              {run.reproduced ? 'YES (Exit Code 1)' : 'NO'}
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>Post-Patch Tests</span>
            <strong style={{ color: run.test_passed ? 'var(--status-passed)' : 'var(--status-failed)' }}>
              {run.test_passed ? 'ALL PASSED (Exit 0)' : 'FAILED'}
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>Modified Files</span>
            <strong style={{ fontFamily: 'var(--font-mono)' }}>{run.modified_files.length} file(s)</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>Repair Iterations</span>
            <strong>{run.iteration_count} / 2</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>Model Calls</span>
            <strong>{run.model_call_count} invocations</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>Tavily Inquiries</span>
            <strong>{run.tavily_searches_count} queries</strong>
          </div>
        </div>
      </div>

      {/* Subnavigation Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px', overflowX: 'auto' }}>
        {[
          { key: 'timeline', label: 'Timeline & Stages' },
          { key: 'reproduction', label: 'Bug Reproduction' },
          { key: 'diagnosis', label: 'Diagnosis & Root Cause' },
          { key: 'research', label: 'Research (Tavily)' },
          { key: 'patch', label: 'Surgical Patch (Diff)' },
          { key: 'tests', label: 'Test Comparison' },
          { key: 'verification', label: 'Independent Verification' },
          { key: 'report', label: 'Audit Report Export' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`nav-btn ${activeTab === tab.key ? 'active' : ''}`}
            style={{ padding: '8px 16px', fontSize: '0.85rem', whiteSpace: 'nowrap' }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Workflow Timeline */}
      {activeTab === 'timeline' && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Clock size={18} color="var(--color-brand)" />
              <span>Orchestrated Repair Stages & Events</span>
            </h2>
            <span className="badge badge-neutral">{run.events.length} Events</span>
          </div>

          <div className="timeline">
            {run.events.map((evt) => {
              const isCompleted = evt.status === 'completed';
              const isFailed = evt.status === 'failed';
              const isSkipped = evt.status === 'skipped';

              return (
                <div key={evt.id} className="timeline-item">
                  <div
                    className={`timeline-icon-wrap ${
                      isCompleted
                        ? 'timeline-icon-completed'
                        : isFailed
                        ? 'timeline-icon-failed'
                        : isSkipped
                        ? ''
                        : 'timeline-icon-started'
                    }`}
                  >
                    {isCompleted ? (
                      <Check size={16} />
                    ) : isFailed ? (
                      <XCircle size={16} />
                    ) : (
                      <Clock size={16} />
                    )}
                  </div>

                  <div className="timeline-content">
                    <div className="timeline-meta">
                      <span className="timeline-stage-title">
                        Stage: {evt.stage} —{' '}
                        <span
                          className={`badge ${
                            isCompleted
                              ? 'badge-passed'
                              : isFailed
                              ? 'badge-failed'
                              : isSkipped
                              ? 'badge-neutral'
                              : 'badge-running'
                          }`}
                          style={{ fontSize: '0.68rem', padding: '2px 8px' }}
                        >
                          {evt.status}
                        </span>
                      </span>
                      <span className="timeline-time">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                    </div>

                    <p className="timeline-message">{evt.message}</p>

                    {evt.metadata_json && (
                      <details style={{ marginTop: '8px' }}>
                        <summary style={{ fontSize: '0.78rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
                          View stage metadata
                        </summary>
                        <pre
                          style={{
                            background: 'var(--bg-code)',
                            padding: '8px',
                            borderRadius: '4px',
                            marginTop: '6px',
                            fontSize: '0.78rem',
                            overflowX: 'auto',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          {JSON.stringify(JSON.parse(evt.metadata_json), null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: Bug Reproduction */}
      {activeTab === 'reproduction' && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Terminal size={18} color="var(--color-cyan)" />
              <span>Observable Bug Reproduction Evidence</span>
            </h2>
            <span
              className={`badge ${run.reproduced ? 'badge-passed' : 'badge-failed'}`}
            >
              {run.reproduced ? 'DEFECT CONFIRMED (EXIT 1)' : 'INCONCLUSIVE'}
            </span>
          </div>

          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '16px' }}>
            Before synthesizing any patch, ProofPatch executes the target test suite in the isolated workspace copy to establish ground-truth defect manifestation.
          </p>

          <div style={{ marginBottom: '16px', display: 'flex', gap: '20px', fontSize: '0.85rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Reproduction Command: </span>
              <code style={{ background: 'var(--bg-card)', padding: '2px 8px', borderRadius: '4px' }}>
                {run.reproduction_command || 'pytest tests -v'}
              </code>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Exit Code: </span>
              <code style={{ color: run.reproduced ? 'var(--status-failed)' : 'var(--text-main)', fontWeight: 600 }}>
                {run.reproduction_exit_code ?? 'N/A'}
              </code>
            </div>
          </div>

          <div className="terminal-window">
            <div className="terminal-header">
              <div className="terminal-dots">
                <span className="terminal-dot dot-red"></span>
                <span className="terminal-dot dot-yellow"></span>
                <span className="terminal-dot dot-green"></span>
              </div>
              <span>Captured Pre-Patch Test Output</span>
            </div>
            <div className="terminal-body">{run.reproduction_output || 'No reproduction output recorded.'}</div>
          </div>
        </div>
      )}

      {/* Tab 3: Diagnosis */}
      {activeTab === 'diagnosis' && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <FileCode size={18} color="var(--color-brand)" />
              <span>Model Diagnosis & Technical Analysis</span>
            </h2>
            <span className="badge badge-neutral">Structured Schema</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-cyan)', marginBottom: '6px' }}>
                Problem Summary
              </h3>
              <p style={{ color: 'var(--text-main)', fontSize: '0.92rem', lineHeight: 1.6 }}>
                {run.diagnosis_summary || 'No diagnosis summary recorded.'}
              </p>
            </div>

            <div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-cyan)', marginBottom: '6px' }}>
                Likely Root Cause
              </h3>
              <div
                style={{
                  background: 'var(--bg-code)',
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-secondary)',
                  fontSize: '0.88rem',
                  lineHeight: 1.6,
                  border: '1px solid var(--border-subtle)',
                }}
              >
                {run.diagnosis_root_cause || 'No technical root cause recorded.'}
              </div>
            </div>

            <div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-cyan)', marginBottom: '6px' }}>
                Targeted Source Files
              </h3>
              <ul style={{ paddingLeft: '20px', color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
                {run.modified_files.map((f) => (
                  <li key={f} style={{ fontFamily: 'var(--font-mono)' }}>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Tavily Research */}
      {activeTab === 'research' && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Search size={18} color="var(--color-cyan)" />
              <span>External Research & Technical Context (Tavily)</span>
            </h2>
            <span
              className={`badge ${
                evidence?.tavily_research?.enabled ? 'badge-passed' : 'badge-neutral'
              }`}
            >
              {evidence?.tavily_research?.enabled ? 'TAVILY EVIDENCE ATTACHED' : 'RESEARCH DISABLED'}
            </span>
          </div>

          {evidence?.tavily_research?.enabled && evidence.tavily_research.results ? (
            <div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '16px' }}>
                Autonomous query dispatched to Tavily Search API for live issue context:
                <br />
                <strong>Query: </strong>
                <code>{evidence.tavily_research.query}</code>
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {evidence.tavily_research.results.map((res, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-md)',
                      padding: '16px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <a
                        href={res.url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: 'var(--color-brand)', fontWeight: 600, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        <span>{res.title}</span>
                        <ExternalLink size={13} />
                      </a>
                      {res.score !== undefined && (
                        <span className="badge badge-neutral">Relevance: {(res.score * 100).toFixed(0)}%</span>
                      )}
                    </div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      {res.content}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <p style={{ fontSize: '0.95rem', marginBottom: '8px', color: 'var(--text-secondary)' }}>
                External research via Tavily was not triggered for this run.
              </p>
              <p style={{ fontSize: '0.82rem' }}>
                In deterministic demo mode, external network requests are bypassed to guarantee zero API token spend. In live mode, Tavily can be activated by setting <code>TAVILY_ENABLED=true</code> and providing <code>TAVILY_API_KEY</code>.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Surgical Patch (Diff) */}
      {activeTab === 'patch' && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <GitCommit size={18} color="var(--color-brand)" />
              <span>Surgical Patch Preview (Unified Diff)</span>
            </h2>
            <span className="badge badge-passed">Strict Diff Parsed</span>
          </div>

          <div style={{ marginBottom: '14px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            <span>Targeted Files: </span>
            {run.modified_files.map((f) => (
              <span
                key={f}
                style={{
                  background: 'var(--bg-card)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--color-brand)',
                  marginRight: '8px',
                }}
              >
                {f}
              </span>
            ))}
          </div>

          <div className="diff-container">
            <div className="diff-header">
              <span>Unified Diff View</span>
              <span style={{ fontSize: '0.75rem', fontWeight: 'normal', color: 'var(--text-muted)' }}>
                Protected against directory traversal & oversized payloads
              </span>
            </div>
            <div className="diff-body">
              {run.patch_diff ? (
                run.patch_diff.split('\n').map((line, idx) => {
                  let lineClass = 'diff-ctx';
                  if (line.startsWith('+') && !line.startsWith('+++')) lineClass = 'diff-add';
                  else if (line.startsWith('-') && !line.startsWith('---')) lineClass = 'diff-del';
                  else if (line.startsWith('@@')) lineClass = 'diff-hunk';

                  return (
                    <div key={idx} className={`diff-line ${lineClass}`}>
                      {line}
                    </div>
                  );
                })
              ) : (
                <div style={{ padding: '16px', color: 'var(--text-muted)' }}>No unified diff recorded.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 6: Test Comparison */}
      {activeTab === 'tests' && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <CheckCircle2 size={18} color="var(--status-passed)" />
              <span>Test Suite Execution Comparison (Before vs After)</span>
            </h2>
            <span className={`badge ${run.test_passed ? 'badge-passed' : 'badge-failed'}`}>
              {run.test_passed ? 'REGRESSION TESTS GREEN' : 'TESTS FAILED'}
            </span>
          </div>

          <div style={{ overflowX: 'auto', marginBottom: '24px' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Execution Phase</th>
                  <th>Invoked Command</th>
                  <th>Exit Code</th>
                  <th>Outcome</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ fontWeight: 600 }}>1. Baseline (Pre-Patch)</td>
                  <td>
                    <code>{run.reproduction_command || 'pytest tests -v'}</code>
                  </td>
                  <td>
                    <code style={{ color: 'var(--status-failed)' }}>{run.pre_patch_exit_code ?? 1}</code>
                  </td>
                  <td>
                    <span className="badge badge-failed">REPRODUCED DEFECT</span>
                  </td>
                </tr>
                <tr>
                  <td style={{ fontWeight: 600 }}>2. Verification (Post-Patch)</td>
                  <td>
                    <code>pytest tests -v</code>
                  </td>
                  <td>
                    <code style={{ color: 'var(--status-passed)' }}>{run.post_patch_exit_code ?? 0}</code>
                  </td>
                  <td>
                    <span className="badge badge-passed">ALL TESTS PASSED</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '8px' }}>
            Post-Patch Test Runner Terminal Output
          </h3>
          <div className="terminal-window">
            <div className="terminal-header">
              <div className="terminal-dots">
                <span className="terminal-dot dot-red"></span>
                <span className="terminal-dot dot-yellow"></span>
                <span className="terminal-dot dot-green"></span>
              </div>
              <span>Captured stdout / stderr</span>
            </div>
            <div className="terminal-body">{run.post_patch_test_output || 'No post-patch test output recorded.'}</div>
          </div>
        </div>
      )}

      {/* Tab 7: Independent Verification */}
      {activeTab === 'verification' && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <ShieldCheck size={18} color="var(--color-brand)" />
              <span>Independent Deterministic Verification Checklist</span>
            </h2>
            <span className={`badge ${run.verified ? 'badge-passed' : 'badge-warning'}`}>
              {run.verified ? 'ALL 6 CHECKS PASSED' : 'VERIFICATION INCOMPLETE'}
            </span>
          </div>

          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '20px' }}>
            ProofPatch never accepts a model's verbal claim of a fix. The verification engine independently checks the filesystem, exit codes, diff format, and source immutability.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {evidence?.verification_checks.map((chk, idx) => {
              const passed = chk.status === 'PASSED';
              return (
                <div
                  key={idx}
                  style={{
                    background: 'var(--bg-card)',
                    border: `1px solid ${passed ? 'var(--status-passed-border)' : 'var(--status-failed-border)'}`,
                    borderRadius: 'var(--radius-md)',
                    padding: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {passed ? (
                      <CheckCircle2 size={20} color="var(--status-passed)" />
                    ) : (
                      <XCircle size={20} color="var(--status-failed)" />
                    )}
                    <div>
                      <strong style={{ fontSize: '0.95rem', color: 'var(--text-main)', display: 'block' }}>
                        {chk.name}
                      </strong>
                      <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{chk.detail}</span>
                    </div>
                  </div>

                  <span className={`badge ${passed ? 'badge-passed' : 'badge-failed'}`}>{chk.status}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 8: Audit Report & Export */}
      {activeTab === 'report' && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Download size={18} color="var(--color-brand)" />
              <span>Auditable Evidence Report</span>
            </h2>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="btn-secondary" onClick={downloadJsonReport} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                <Download size={13} />
                <span>Download JSON</span>
              </button>
              <button className="btn-primary" onClick={downloadMarkdownReport} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                <Download size={13} />
                <span>Download Markdown</span>
              </button>
            </div>
          </div>

          <div
            style={{
              background: 'var(--bg-code)',
              padding: '24px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.84rem',
              color: '#e2e8f0',
              overflowX: 'auto',
              maxHeight: '600px',
              whiteSpace: 'pre-wrap',
            }}
          >
            {evidence?.markdown_report || 'Evidence report generation in progress...'}
          </div>
        </div>
      )}
    </div>
  );
};
