import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';

describe('ProofPatch Frontend Application', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    // Mock global fetch
    globalThis.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = String(url);
      if (urlStr.includes('/api/config-status')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              app_name: 'ProofPatch',
              app_env: 'development',
              mode: 'demo',
              nebius_configured: false,
              nebius_model: null,
              nebius_base_url: 'https://api.tokenfactory.nebius.com/v1/',
              tavily_enabled: false,
              tavily_configured: false,
              docker_available: true,
              max_model_calls: 4,
              max_patch_iterations: 2,
              timeout_seconds: 60,
            }),
        } as Response);
      }

      if (urlStr.includes('/api/runs')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve([
              {
                id: 'demo_test_123',
                created_at: '2026-10-16T12:00:00Z',
                updated_at: '2026-10-16T12:00:05Z',
                mode: 'demo',
                status: 'passed',
                repository_url: 'bundled:examples/buggy-python-service',
                bug_title: '[BUG] 6-seat Growth tier boundary calculates at Starter rate',
                reproduced: true,
                test_passed: true,
                verified: true,
                iteration_count: 1,
              },
            ]),
        } as Response);
      }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response);
    });
  });

  it('renders application branding and transparent demo banner', async () => {
    render(<App />);

    // Brand and tagline
    expect(screen.getByText('ProofPatch')).toBeInTheDocument();
    expect(screen.getByText('AI repairs you can verify.')).toBeInTheDocument();

    // Zero-token demo banner
    expect(screen.getByText('LOCAL DEMO MODE')).toBeInTheDocument();
  });

  it('renders dashboard metrics and recent runs', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Total Repair Runs')).toBeInTheDocument();
      expect(screen.getByText('Verified Fixes')).toBeInTheDocument();
    });

    // Recent run item
    await waitFor(() => {
      expect(screen.getByText(/6-seat Growth tier boundary/)).toBeInTheDocument();
    });
  });

  it('switches navigation tabs to New Repair and Settings cleanly', async () => {
    render(<App />);

    // Navigate to New Repair
    const newRepairBtn = screen.getByRole('button', { name: /New Repair/i });
    fireEvent.click(newRepairBtn);

    expect(screen.getByText(/Initiate Verifiable Code Repair/i)).toBeInTheDocument();
    expect(screen.getByText(/Bundled Demo Service/i)).toBeInTheDocument();

    // Navigate to Settings
    const settingsBtn = screen.getByRole('button', { name: /Settings/i });
    fireEvent.click(settingsBtn);

    expect(screen.getByText(/System Configuration & Provider Status/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Nebius/i)[0]).toBeInTheDocument();
  });
});
