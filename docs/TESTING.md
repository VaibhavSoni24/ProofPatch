# ProofPatch Testing & Quality Assurance Guide

ProofPatch enforces rigorous automated test coverage across both backend orchestration and frontend interfaces. Testing requires **zero external API credits**; all model inference and search providers are comprehensively tested using mocked HTTP responses and local deterministic fixtures.

---

## Test Suites Overview

| Test Suite | Framework | Count | Purpose |
|---|---|---|---|
| **Backend Configuration** | `pytest` | 4 tests | Tests default demo mode, Nebius detection, Tavily detection, and secret exclusion. |
| **Demo Workflow** | `pytest` | 1 test | End-to-end local reproduction, patching, regression pass, and evidence generation. |
| **Git & Repositories** | `pytest` | 6 tests | Tests public GitHub URL parsing, credential rejection, scheme verification. |
| **Nebius Provider** | `pytest` | 6 tests | Mocks OpenAI-compatible completions, non-NVIDIA model rejection, 401 auth, timeouts. |
| **Tavily Provider** | `pytest` | 3 tests | Mocks search queries, disabled status, and network connection fallbacks. |
| **Patch Parser & Security** | `pytest` | 6 tests | Path traversal rejection (`../`), diff size caps, clean hunk application. |
| **Run Management API** | `pytest` | 5 tests | Endpoints for `/api/health`, `/api/config-status`, `/api/runs`, `/api/runs/demo`, 404 handling. |
| **Execution Sandboxes** | `pytest` | 19 tests | Tests Local backend, Docker fail-closed behavior, and Token Factory ConTree SDK lifecycle, client construction, UploadFileSpec file transfer, patch apply, valid zero exit codes, nonzero exit codes, missing exit code rejection, invalid exit code rejection, timeouts, and clean resource cleanup. |
| **Deterministic Verifier** | `pytest` | 13 tests | Audits missing exit codes, inconclusive baseline tests, unrelated failures, import errors, collection errors, timeouts, contradictory post-patch outputs, and secrets. |
| **Async Orchestrator Integration** | `pytest` | 6 tests | Full async workflow with mocked Nebius, Tavily, strict baseline gating on unrelated failures, collection errors, timeouts, and provider error handling. |
| **Frontend UI Suite** | `vitest` + RTL | 3 tests | Tests branding, demo banner, metric cards, tab navigation, and settings view. |
| **Total Automated Tests** | | **72 tests** | **100% Pass Rate** |

---

## Running Backend Tests

### Windows PowerShell:
```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run full pytest suite with verbose output
pytest backend/tests -v
```

### Linux / macOS:
```bash
source .venv/bin/activate
pytest backend/tests -v
```

### Run Specific Test Modules:
```bash
# Sandbox and execution backend tests
pytest backend/tests/test_sandbox.py -v

# Verification engine audit tests
pytest backend/tests/test_verification.py -v

# Async orchestrator integration tests
pytest backend/tests/test_orchestrator.py -v

# Provider mocked tests
pytest backend/tests/test_nebius_provider.py -v
pytest backend/tests/test_tavily_provider.py -v
```

---

## Running Frontend Tests & Build

From the `frontend/` directory:

```bash
cd frontend

# Run Vitest test suite
npm test

# Run TypeScript typecheck
npm run typecheck

# Run Production Vite Build
npm run build
```

---

## Code Quality & Linting Checks

### Python (Ruff):
```bash
# Check code style and imports
ruff check backend

# Verify formatting
ruff format --check backend
```

### Frontend (TypeScript):
```bash
cd frontend
npm run typecheck
```

---

## Running the Automated Full Verification Script

You can run the end-to-end check script to validate both backend and frontend suites with one command:

### Windows PowerShell:
```powershell
./scripts/check.ps1
```

### Linux / macOS:
```bash
./scripts/check.sh
```
