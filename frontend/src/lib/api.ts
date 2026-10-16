/**
 * ProofPatch REST API Client
 */

export interface ConfigStatus {
  app_name: string;
  app_env: string;
  mode: 'demo' | 'live';
  nebius_configured: boolean;
  nebius_model: string | null;
  nebius_base_url: string;
  tavily_enabled: boolean;
  tavily_configured: boolean;
  docker_available: boolean;
  execution_backend: string;
  token_factory_sandbox_configured: boolean;
  max_model_calls: number;
  max_patch_iterations: number;
  timeout_seconds: number;
}

export interface StageEvent {
  id: number;
  run_id: string;
  timestamp: string;
  stage: string;
  status: 'started' | 'completed' | 'failed' | 'skipped';
  message: string;
  metadata_json?: string | null;
}

export interface RunSummary {
  id: string;
  created_at: string;
  updated_at: string;
  mode: 'demo' | 'live';
  status: 'queued' | 'running' | 'passed' | 'failed' | 'partial' | 'cancelled' | 'inconclusive';
  repository_url: string;
  bug_title: string;
  reproduced: boolean;
  test_passed: boolean;
  verified: boolean;
  iteration_count: number;
}

export interface RunDetail extends RunSummary {
  bug_description: string;
  commit_hash?: string | null;
  reproduction_command?: string | null;
  reproduction_exit_code?: number | null;
  reproduction_output?: string | null;
  diagnosis_summary?: string | null;
  diagnosis_root_cause?: string | null;
  patch_diff?: string | null;
  modified_files: string[];
  pre_patch_test_output?: string | null;
  pre_patch_exit_code?: number | null;
  post_patch_test_output?: string | null;
  post_patch_exit_code?: number | null;
  model_call_count: number;
  tavily_searches_count: number;
  error_message?: string | null;
  events: StageEvent[];
}

export interface VerificationItem {
  name: string;
  status: 'PASSED' | 'FAILED' | 'NOT_RUN' | 'INCONCLUSIVE';
  detail: string;
}

export interface TestRecord {
  stage: string;
  command: string;
  exit_code: number;
  passed: boolean;
  output_summary: string;
}

export interface EvidenceReport {
  run_id: string;
  created_at: string;
  mode: string;
  status: string;
  repository_url: string;
  bug_title: string;
  reproduced: boolean;
  tests_passed: boolean;
  verified: boolean;
  verification_checks: VerificationItem[];
  tests: TestRecord[];
  patch_diff?: string | null;
  modified_files: string[];
  tavily_research?: {
    enabled: boolean;
    query?: string;
    results?: Array<{
      title: string;
      url: string;
      content: string;
      score?: number;
    }>;
  } | null;
  markdown_report: string;
}

export interface RunCreatePayload {
  repository_url: string;
  bug_title: string;
  bug_description: string;
  mode?: 'demo' | 'live';
  confirm_live_execution?: boolean;
}

const API_BASE = '/api';

export async function fetchConfigStatus(): Promise<ConfigStatus> {
  const res = await fetch(`${API_BASE}/config-status`);
  if (!res.ok) {
    throw new Error(`Failed to fetch config status: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRuns(): Promise<RunSummary[]> {
  const res = await fetch(`${API_BASE}/runs`);
  if (!res.ok) {
    throw new Error(`Failed to fetch runs: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRun(runId: string): Promise<RunDetail> {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch run ${runId}: ${res.statusText}`);
  }
  return res.json();
}

export async function triggerDemoRun(): Promise<RunDetail> {
  const res = await fetch(`${API_BASE}/runs/demo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.error || `Failed to trigger demo run: ${res.statusText}`);
  }
  return res.json();
}

export async function createRun(payload: RunCreatePayload): Promise<RunDetail> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.error || `Failed to create run: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRunEvidence(runId: string): Promise<EvidenceReport> {
  const res = await fetch(`${API_BASE}/runs/${runId}/evidence`);
  if (!res.ok) {
    throw new Error(`Failed to fetch evidence for run ${runId}: ${res.statusText}`);
  }
  return res.json();
}

export async function cancelRun(runId: string): Promise<{ run_id: string; status: string; message: string }> {
  const res = await fetch(`${API_BASE}/runs/${runId}/cancel`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to cancel run ${runId}: ${res.statusText}`);
  }
  return res.json();
}
