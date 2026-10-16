import React, { useState } from 'react';
import type { RunSummary } from '../../lib/api';
import { History, Search, ArrowRight, CheckCircle2, XCircle, AlertTriangle, PlusCircle, Play } from 'lucide-react';

interface RunsListViewProps {
  runs: RunSummary[];
  onSelectRun: (runId: string) => void;
  onNewRepair: () => void;
  onTriggerDemo: () => void;
  isTriggeringDemo: boolean;
}

export const RunsListView: React.FC<RunsListViewProps> = ({
  runs,
  onSelectRun,
  onNewRepair,
  onTriggerDemo,
  isTriggeringDemo,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [modeFilter, setModeFilter] = useState<'all' | 'demo' | 'live'>('all');

  const filteredRuns = runs.filter((r) => {
    const matchesSearch =
      r.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.bug_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.repository_url.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesMode = modeFilter === 'all' || r.mode === modeFilter;
    return matchesSearch && matchesMode;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="card">
        <div className="card-header">
          <div>
            <h1 className="card-title" style={{ fontSize: '1.25rem' }}>
              <History size={22} color="var(--color-brand)" />
              <span>Repair Run History</span>
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '4px' }}>
              Chronological log of all autonomous bug reproductions and verifiable fixes.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ position: 'relative', minWidth: '240px' }}>
              <Search size={15} style={{ position: 'absolute', left: '10px', top: '12px', color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="form-input"
                placeholder="Search runs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ paddingLeft: '32px', paddingRight: '12px' }}
              />
            </div>

            <select
              className="form-select"
              value={modeFilter}
              onChange={(e) => setModeFilter(e.target.value as any)}
              style={{ padding: '8px 12px', fontSize: '0.85rem' }}
            >
              <option value="all">All Modes</option>
              <option value="demo">Demo Only</option>
              <option value="live">Live Only</option>
            </select>

            <button className="btn-primary" onClick={onNewRepair} style={{ padding: '8px 14px', fontSize: '0.85rem' }}>
              <PlusCircle size={15} />
              <span>New Repair</span>
            </button>
          </div>
        </div>

        {filteredRuns.length === 0 ? (
          <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <p style={{ fontSize: '1rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              No repair runs match your filter.
            </p>
            <button
              className="btn-secondary"
              onClick={onTriggerDemo}
              disabled={isTriggeringDemo}
              style={{ marginTop: '12px' }}
            >
              <Play size={14} fill="currentColor" />
              <span>Run Offline Demo</span>
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Defect / Issue</th>
                  <th>Repository</th>
                  <th>Mode</th>
                  <th>Status</th>
                  <th>Reproduction</th>
                  <th>Regression Tests</th>
                  <th>Audit Result</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredRuns.map((run) => (
                  <tr key={run.id} style={{ cursor: 'pointer' }} onClick={() => onSelectRun(run.id)}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-brand)' }}>
                      {run.id}
                    </td>
                    <td style={{ maxWidth: '280px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {run.bug_title}
                    </td>
                    <td style={{ maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                      {run.repository_url}
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
                          <CheckCircle2 size={13} />
                          <span>Yes</span>
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <XCircle size={13} />
                          <span>No</span>
                        </span>
                      )}
                    </td>
                    <td>
                      {run.test_passed ? (
                        <span style={{ color: 'var(--status-passed)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle2 size={13} />
                          <span>Passed</span>
                        </span>
                      ) : (
                        <span style={{ color: 'var(--status-failed)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <AlertTriangle size={13} />
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
                        <span>Inspect</span>
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
