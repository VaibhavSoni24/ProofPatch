import React from 'react';
import type { ConfigStatus } from '../../lib/api';
import { Settings, Shield, Cpu, Search, Box, Lock, CheckCircle2, XCircle } from 'lucide-react';

interface SettingsViewProps {
  config: ConfigStatus | null;
  onRefresh: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ config, onRefresh }) => {
  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="card">
        <div className="card-header">
          <h1 className="card-title">
            <Settings size={22} color="var(--color-brand)" />
            <span>System Configuration & Provider Status</span>
          </h1>
          <button className="btn-secondary" onClick={onRefresh} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            Refresh Status
          </button>
        </div>

        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '24px' }}>
          ProofPatch enforces complete credential isolation. Secrets are read exclusively by the backend and never passed to the client. All provider metadata below is sanitized.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px', marginBottom: '28px' }}>
          {/* Card 1: Execution Mode */}
          <div style={{ background: 'var(--bg-card)', padding: '18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Shield size={18} color="var(--color-brand)" />
              <strong style={{ fontSize: '0.95rem' }}>Active Mode</strong>
            </div>
            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8', marginBottom: '4px' }}>
              {config?.mode.toUpperCase() || 'DEMO'}
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {config?.mode === 'demo'
                ? 'Zero-credit deterministic offline execution'
                : 'Live Nebius Token Factory inference enabled'}
            </p>
          </div>

          {/* Card 2: Nebius Model */}
          <div style={{ background: 'var(--bg-card)', padding: '18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Cpu size={18} color="var(--color-cyan)" />
              <strong style={{ fontSize: '0.95rem' }}>Nebius Token Factory</strong>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              {config?.nebius_configured ? (
                <span className="badge badge-passed">
                  <CheckCircle2 size={12} />
                  <span>Configured</span>
                </span>
              ) : (
                <span className="badge badge-neutral">
                  <XCircle size={12} />
                  <span>Unconfigured</span>
                </span>
              )}
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Model: <code>{config?.nebius_model || 'Unset (placeholder)'}</code>
            </p>
          </div>

          {/* Card 3: Tavily Search */}
          <div style={{ background: 'var(--bg-card)', padding: '18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Search size={18} color="var(--color-indigo)" />
              <strong style={{ fontSize: '0.95rem' }}>Tavily Search API</strong>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              {config?.tavily_configured ? (
                <span className="badge badge-passed">
                  <CheckCircle2 size={12} />
                  <span>Active</span>
                </span>
              ) : (
                <span className="badge badge-neutral">
                  <span>Disabled</span>
                </span>
              )}
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {config?.tavily_enabled
                ? 'Autonomous doc retrieval active'
                : 'Disabled by default to preserve credits'}
            </p>
          </div>

          {/* Card 4: Sandbox Execution Backend */}
          <div style={{ background: 'var(--bg-card)', padding: '18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Box size={18} color="var(--status-passed)" />
              <strong style={{ fontSize: '0.95rem' }}>Sandbox Backend</strong>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-passed">
                <span>{config?.execution_backend?.toUpperCase() || 'DOCKER'}</span>
              </span>
              {config?.token_factory_sandbox_configured && (
                <span className="badge badge-passed" style={{ fontSize: '0.7rem' }}>
                  ConTree Ready
                </span>
              )}
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {config?.execution_backend === 'token_factory_sandbox'
                ? 'Nebius Token Factory / ConTree cloud container sandbox'
                : config?.docker_available
                  ? 'Local non-networked Docker container isolation'
                  : 'Docker daemon offline; demo runs via safe local runner'}
            </p>
          </div>
        </div>

        {/* Execution Budget & Safety Limits */}
        <h2 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '14px' }}>
          Safety Limits & Credit Protection Safeguards
        </h2>
        <div style={{ overflowX: 'auto', marginBottom: '28px' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Constraint Setting</th>
                <th>Configured Value</th>
                <th>Protection Purpose</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Max Model Invocations Per Run</td>
                <td><code>{config?.max_model_calls ?? 4} calls</code></td>
                <td>Prevents runaway model billing in live mode</td>
              </tr>
              <tr>
                <td>Max Patch Iterations</td>
                <td><code>{config?.max_patch_iterations ?? 2} loops</code></td>
                <td>Caps test-failure retry loops to prevent thrashing</td>
              </tr>
              <tr>
                <td>Execution Timeout</td>
                <td><code>{config?.timeout_seconds ?? 60} seconds</code></td>
                <td>Kills hung test processes and infinite loops</td>
              </tr>
              <tr>
                <td>Default Execution Mode</td>
                <td><code>demo</code></td>
                <td>Zero-cost out of the box experience</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* How to activate live credentials guide */}
        <div
          style={{
            background: 'var(--bg-code)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-brand)', fontWeight: 600, marginBottom: '10px' }}>
            <Lock size={16} />
            <span>Activating Live Mode for Hackathon Submission</span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: 1.5 }}>
            To switch from demo mode to genuine live model inference using Nebius Token Factory and NVIDIA models, update your untracked local <code>.env</code> file:
          </p>
          <pre
            style={{
              background: '#070a10',
              padding: '12px',
              borderRadius: '6px',
              fontSize: '0.82rem',
              color: '#38bdf8',
              fontFamily: 'var(--font-mono)',
              overflowX: 'auto',
            }}
          >
{`# 1. Switch mode to live
PROOFPATCH_MODE=live

# 2. Add Nebius Token Factory Credentials & NVIDIA Model
# (Select an active eligible NVIDIA model from https://docs.tokenfactory.nebius.com/ or https://tokenfactory.nebius.com/models)
NEBIUS_API_KEY=your_actual_nebius_api_key_here
NEBIUS_MODEL=nvidia/<selected-active-model-id>

# 3. Choose Execution Sandbox Backend
# Options: "docker" (local daemon) or "token_factory_sandbox" (Nebius ConTree)
EXECUTION_BACKEND=docker
# If using Token Factory sandbox:
# CONTREE_TOKEN=your_contree_or_nebius_token

# 4. (Optional) Activate Tavily Technical Research
TAVILY_API_KEY=your_tavily_api_key_here
TAVILY_ENABLED=true`}
          </pre>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '10px' }}>
            Remember: <code>.env</code> is excluded by <code>.gitignore</code> and will never be committed to Git.
          </p>
        </div>
      </div>
    </div>
  );
};
