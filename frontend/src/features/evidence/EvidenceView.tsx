import React, { useState } from 'react';
import type { RunSummary } from '../../lib/api';
import { fetchRunEvidence } from '../../lib/api';
import { ShieldCheck, Download, Search, CheckCircle2, FileText, ArrowRight } from 'lucide-react';

interface EvidenceViewProps {
  runs: RunSummary[];
  onSelectRun: (runId: string) => void;
}

export const EvidenceView: React.FC<EvidenceViewProps> = ({ runs, onSelectRun }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const filteredRuns = runs.filter(
    (r) =>
      r.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.bug_title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDownload = async (runId: string, format: 'json' | 'md') => {
    try {
      setDownloadingId(runId);
      const ev = await fetchRunEvidence(runId);
      const content =
        format === 'json'
          ? JSON.stringify(ev, null, 2)
          : ev.markdown_report;
      const mime = format === 'json' ? 'application/json' : 'text/markdown';
      const ext = format === 'json' ? 'json' : 'md';

      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `proofpatch-evidence-${runId}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Could not fetch evidence for ${runId}`);
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="card">
        <div className="card-header">
          <div>
            <h1 className="card-title" style={{ fontSize: '1.25rem' }}>
              <ShieldCheck size={22} color="var(--color-brand)" />
              <span>Verifiable Evidence Audit Registry</span>
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '4px' }}>
              Download cryptographically traceable execution evidence, diffs, and verification logs for auditing.
            </p>
          </div>

          <div style={{ position: 'relative', minWidth: '280px' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-input"
              placeholder="Filter by Run ID or Title..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ paddingLeft: '36px' }}
            />
          </div>
        </div>

        {filteredRuns.length === 0 ? (
          <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <p>No verifiable runs found matching your search.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Issue Title</th>
                  <th>Execution Mode</th>
                  <th>Audit Status</th>
                  <th>Regression Tests</th>
                  <th>Export Evidence</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredRuns.map((run) => (
                  <tr key={run.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-brand)' }}>
                      {run.id}
                    </td>
                    <td style={{ maxWidth: '340px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {run.bug_title}
                    </td>
                    <td>
                      <span className={`badge ${run.mode === 'demo' ? 'badge-neutral' : 'badge-warning'}`}>
                        {run.mode}
                      </span>
                    </td>
                    <td>
                      {run.verified ? (
                        <span className="badge badge-passed">
                          <CheckCircle2 size={13} />
                          <span>VERIFIED</span>
                        </span>
                      ) : (
                        <span className="badge badge-warning">PARTIAL</span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${run.test_passed ? 'badge-passed' : 'badge-failed'}`}>
                        {run.test_passed ? 'PASSED' : 'FAILED'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          className="btn-secondary"
                          onClick={() => handleDownload(run.id, 'md')}
                          disabled={downloadingId === run.id}
                          style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                          title="Download Markdown Report"
                        >
                          <FileText size={13} />
                          <span>MD</span>
                        </button>
                        <button
                          className="btn-secondary"
                          onClick={() => handleDownload(run.id, 'json')}
                          disabled={downloadingId === run.id}
                          style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                          title="Download Full JSON Evidence"
                        >
                          <Download size={13} />
                          <span>JSON</span>
                        </button>
                      </div>
                    </td>
                    <td>
                      <button
                        className="btn-secondary"
                        onClick={() => onSelectRun(run.id)}
                        style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                      >
                        <span>Details</span>
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
