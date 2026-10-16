import React, { useState } from 'react';
import type { ConfigStatus, RunCreatePayload } from '../../lib/api';
import { ShieldCheck, AlertCircle, Play, Info, Sparkles } from 'lucide-react';

interface NewRepairViewProps {
  config: ConfigStatus | null;
  onSubmit: (payload: RunCreatePayload) => Promise<void>;
  onTriggerDemo: () => void;
  isSubmitting: boolean;
}

export const NewRepairView: React.FC<NewRepairViewProps> = ({
  config,
  onSubmit,
  onTriggerDemo,
  isSubmitting,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<'bundled' | 'custom'>('bundled');
  const [repoUrl, setRepoUrl] = useState('bundled:examples/buggy-python-service');
  const [bugTitle, setBugTitle] = useState(
    '[BUG] 6-seat Growth tier boundary calculates at Starter tier rate ($120.00 instead of $97.20)'
  );
  const [bugDescription, setBugDescription] = useState(
    'In src/billing.py, calculate_subscription_invoice() uses "if seats > 6 and seats <= 20:" to qualify orders for Growth tier. When a customer orders exactly 6 seats, it improperly evaluates to False and falls through to Starter tier ($20/seat with 0% discount = $120.00) instead of the documented Growth tier ($18/seat with 10% volume discount = $97.20).'
  );
  const [executionMode, setExecutionMode] = useState<'demo' | 'live'>('demo');
  const [confirmLive, setConfirmLive] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handlePresetChange = (preset: 'bundled' | 'custom') => {
    setSelectedPreset(preset);
    if (preset === 'bundled') {
      setRepoUrl('bundled:examples/buggy-python-service');
      setBugTitle('[BUG] 6-seat Growth tier boundary calculates at Starter tier rate ($120.00 instead of $97.20)');
      setBugDescription(
        'In src/billing.py, calculate_subscription_invoice() uses "if seats > 6 and seats <= 20:" to qualify orders for Growth tier. When a customer orders exactly 6 seats, it improperly evaluates to False and falls through to Starter tier ($20/seat with 0% discount = $120.00) instead of the documented Growth tier ($18/seat with 10% volume discount = $97.20).'
      );
      setExecutionMode('demo');
    } else {
      setRepoUrl('https://github.com/VaibhavSoni24/ProofPatch');
      setBugTitle('');
      setBugDescription('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (executionMode === 'live' && !confirmLive) {
      setErrorMsg('Explicit confirmation is required to run in live mode and spend model inference credits.');
      return;
    }

    try {
      await onSubmit({
        repository_url: repoUrl,
        bug_title: bugTitle,
        bug_description: bugDescription,
        mode: executionMode,
        confirm_live_execution: confirmLive,
      });
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit repair run.');
    }
  };

  return (
    <div style={{ maxWidth: '840px', margin: '0 auto' }}>
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <ShieldCheck size={22} color="var(--color-brand)" />
            <span>Initiate Verifiable Code Repair</span>
          </h2>
          <span className="badge badge-neutral">Bounded Orchestration</span>
        </div>

        {/* Preset Selector */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
          <button
            type="button"
            className={`btn-secondary ${selectedPreset === 'bundled' ? 'active' : ''}`}
            onClick={() => handlePresetChange('bundled')}
            style={{
              flex: 1,
              padding: '12px',
              justifyContent: 'center',
              borderColor: selectedPreset === 'bundled' ? 'var(--color-brand)' : 'var(--border-subtle)',
              background: selectedPreset === 'bundled' ? 'var(--bg-card-hover)' : 'var(--bg-card)',
            }}
          >
            <Sparkles size={16} color="var(--color-cyan)" />
            <span>Bundled Demo Service (Issue #104)</span>
          </button>

          <button
            type="button"
            className={`btn-secondary ${selectedPreset === 'custom' ? 'active' : ''}`}
            onClick={() => handlePresetChange('custom')}
            style={{
              flex: 1,
              padding: '12px',
              justifyContent: 'center',
              borderColor: selectedPreset === 'custom' ? 'var(--color-brand)' : 'var(--border-subtle)',
              background: selectedPreset === 'custom' ? 'var(--bg-card-hover)' : 'var(--bg-card)',
            }}
          >
            <span>Custom GitHub Repository</span>
          </button>
        </div>

        {errorMsg && (
          <div
            style={{
              background: 'var(--status-failed-bg)',
              border: '1px solid var(--status-failed-border)',
              color: 'var(--status-failed)',
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontSize: '0.88rem',
            }}
          >
            <AlertCircle size={18} />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Repository URL */}
          <div className="form-group">
            <label className="form-label">Repository Location / URL</label>
            <input
              type="text"
              className="form-input"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repository"
              required
            />
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Supports public GitHub repositories or the built-in deterministic demo workspace.
            </span>
          </div>

          {/* Bug Title */}
          <div className="form-group">
            <label className="form-label">Defect Summary / Title</label>
            <input
              type="text"
              className="form-input"
              value={bugTitle}
              onChange={(e) => setBugTitle(e.target.value)}
              placeholder="e.g. [BUG] 6-seat growth tier boundary calculates at starter rate"
              required
            />
          </div>

          {/* Bug Description */}
          <div className="form-group">
            <label className="form-label">Problem Description & Technical Observations</label>
            <textarea
              className="form-textarea"
              value={bugDescription}
              onChange={(e) => setBugDescription(e.target.value)}
              placeholder="Describe symptoms, expected behavior, and reproduction conditions..."
              rows={4}
              required
            />
          </div>

          {/* Execution Mode Selection */}
          <div className="form-group">
            <label className="form-label">Execution Mode</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <label
                style={{
                  border: `1px solid ${executionMode === 'demo' ? 'var(--color-brand)' : 'var(--border-subtle)'}`,
                  background: executionMode === 'demo' ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input
                    type="radio"
                    name="mode"
                    value="demo"
                    checked={executionMode === 'demo'}
                    onChange={() => setExecutionMode('demo')}
                  />
                  <strong style={{ fontSize: '0.95rem' }}>Demo Mode (Deterministic)</strong>
                </div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Runs completely locally. Zero paid API tokens, zero external inferences.
                </span>
              </label>

              <label
                style={{
                  border: `1px solid ${executionMode === 'live' ? 'var(--color-brand)' : 'var(--border-subtle)'}`,
                  background: executionMode === 'live' ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input
                    type="radio"
                    name="mode"
                    value="live"
                    checked={executionMode === 'live'}
                    onChange={() => setExecutionMode('live')}
                  />
                  <strong style={{ fontSize: '0.95rem' }}>Live Mode (Nebius + Tavily)</strong>
                </div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Calls Nebius Token Factory with configured NVIDIA model. Requires API key.
                </span>
              </label>
            </div>
          </div>

          {/* Live Safeguards & Consent Notice */}
          {executionMode === 'live' && (
            <div
              style={{
                background: 'rgba(245, 158, 11, 0.08)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                marginBottom: '20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-warning)', fontWeight: 600, marginBottom: '8px' }}>
                <Info size={18} />
                <span>Live Run Safeguards & Credit Protection</span>
              </div>
              <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: 1.5 }}>
                Starting a live run will invoke Nebius Token Factory inference using the model configured in your backend environment (<code>{config?.nebius_model || 'Unset'}</code>). ProofPatch enforces a strict maximum of <strong>4 model calls</strong> and <strong>2 patch iterations</strong> per run.
              </p>
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', color: 'var(--text-main)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={confirmLive}
                  onChange={(e) => setConfirmLive(e.target.checked)}
                />
                <span>I confirm that I want to execute a live model-driven repair and authorize token consumption.</span>
              </label>
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
            {selectedPreset === 'bundled' && (
              <button
                type="button"
                className="btn-secondary"
                onClick={onTriggerDemo}
                disabled={isSubmitting}
              >
                <Play size={15} fill="currentColor" />
                <span>Instant Offline Demo</span>
              </button>
            )}

            <button
              type="submit"
              className="btn-primary"
              disabled={isSubmitting}
              style={{ padding: '10px 24px' }}
            >
              <ShieldCheck size={18} />
              <span>{isSubmitting ? 'Dispatching Repair...' : 'Start Verifiable Repair'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
