# ProofPatch Architecture & Technical Design

This document details the software architecture, orchestration pipeline, sandbox security boundaries, provider abstraction layer, and data persistence model of ProofPatch.

---

## 1. High-Level System Architecture

ProofPatch uses a modular monorepo architecture with clean boundaries separating user interfaces, REST endpoints, workflow orchestration, AI inference adapters, external research providers, safe sandbox execution, and persistent storage.

```mermaid
graph TD
    User["Developer / Web Browser"] -->|HTTP / JSON| Frontend["React 19 + TypeScript + Vite"]
    Frontend -->|REST API| API["FastAPI Backend Orchestrator"]
    subgraph Core Engine
        API --> DB[(SQLite Local Persistence)]
        API --> Orchestrator["Autonomous Repair Orchestrator"]
        Orchestrator --> RepoAcq["Repository Acquisition & Git"]
        Orchestrator --> Sandbox["Sandbox Subprocess / Docker Runner"]
        Orchestrator --> PatchParser["Unified Diff Security Validator"]
        Orchestrator --> Verifier["Independent Deterministic Verifier"]
        Orchestrator --> EvidenceService["Evidence Report Generator"]
    end

    subgraph External Provider Integrations
        Orchestrator -->|OpenAI-Compatible| Nebius["Nebius Token Factory (NVIDIA Models)"]
        Orchestrator -->|HTTP JSON API| Tavily["Tavily Search API"]
    end

    subgraph Sandboxed Workspaces
        Sandbox -->|Isolated Pytest Runner| Workspace["Disposable Workspace Copy (/data/workspaces)"]
    end
```

---

## 2. Request & Execution Lifecycle (The 10 Stages)

Every repair run transitions through an explicit, auditable sequence of stages:

```mermaid
stateDiagram-v2
    [*] --> Inspect: Repository Acquisition & Inspection
    Inspect --> Reproduce: Execute Baseline Tests
    Reproduce --> Inconclusive: Tests Unexpectedly Pass (Exit 0)
    Reproduce --> Diagnose: Defect Confirmed (Exit != 0)
    Diagnose --> Research: Optional Tavily Context Search
    Research --> Patch: Generate Surgical Unified Diff
    Patch --> Test: Execute Tests on Patched Code
    Test --> Iterate: Tests Fail (Loop <= MAX_PATCH_ITERATIONS)
    Iterate --> Test
    Test --> Verify: Tests Pass (Exit 0)
    Verify --> Report: Perform Independent Audit
    Inconclusive --> Report
    Report --> [*]
```

### Stage Breakdown

1. **Stage 1: Repository Acquisition**:
   - Validates public GitHub URLs (rejecting credentials, insecure schemes, and malformed paths).
   - Shallow clones into an isolated temporary workspace directory under `data/workspaces/<run_id>`.
2. **Stage 2: Repository Inspection**:
   - Bounded directory scan ignoring `.git`, virtual environments, caches, and build folders.
   - Discovers test manifests (`pyproject.toml`, `requirements.txt`) and test files.
3. **Stage 3: Bug Reproduction**:
   - Executes allowlisted pytest command in the unpatched workspace.
   - Captures stdout/stderr, return code, and establishes verifiable proof of the bug. If reproduction fails (exit code 0), run halts safely as `INCONCLUSIVE`.
4. **Stage 4: Model-Driven Diagnosis**:
   - Sends issue description, failure trace, and code context to Nebius Token Factory.
   - Enforces a strict Pydantic JSON schema (`DiagnosisResult`).
5. **Stage 5: Optional Research (Tavily)**:
   - When configured, queries Tavily for relevant documentation, API updates, or known framework issues.
   - Attaches actual source URLs and excerpts to the evidence log.
6. **Stage 6: Patch Generation & Validation**:
   - Requests minimal unified diff targeting diagnosed lines.
   - Validates diff size (`MAX_PATCH_BYTES`), path safety (strictly rejecting traversal and protected files), and applies hunks cleanly.
7. **Stage 7: Test Execution**:
   - Executes pytest runner against the patched code.
8. **Stage 8: Bounded Repair Loop**:
   - If tests fail, feeds failure trace back to the model for a revised patch.
   - Strict caps: `MAX_PATCH_ITERATIONS=2`, `MAX_MODEL_CALLS_PER_RUN=4`.
9. **Stage 9: Independent Verification**:
   - Deterministically audits 6 concrete claims (exit codes, diff syntax, scope confinement, immutability of original repo, secret scrubbing).
10. **Stage 10: Evidence Report**:
    - Generates downloadable Markdown and JSON evidence documents with raw command logs.

---

## 3. Data Persistence Model

Local SQLite persistence is managed through SQLAlchemy.

```mermaid
erDiagram
    RUNS ||--o{ STAGE_EVENTS : logs
    RUNS ||--o| EVIDENCE_REPORTS : produces

    RUNS {
        string id PK
        string mode
        string status
        string repository_url
        string commit_hash
        string bug_title
        string bug_description
        string reproduction_command
        int reproduction_exit_code
        text reproduction_output
        boolean reproduced
        text patch_diff
        text modified_files
        int post_patch_exit_code
        boolean test_passed
        boolean verified
        int iteration_count
        int model_call_count
        datetime created_at
    }

    STAGE_EVENTS {
        int id PK
        string run_id FK
        datetime timestamp
        string stage
        string status
        text message
        text metadata_json
    }

    EVIDENCE_REPORTS {
        int id PK
        string run_id FK
        datetime created_at
        text evidence_json
        text evidence_markdown
    }
```

---

## 4. Sandbox Security & Isolation Boundaries

1. **Host Immutability**:
   - Execution is strictly confined to disposable working directories under `data/workspaces/`. The user's original repository or parent workspace is never touched.
2. **Environment Sanitization**:
   - Subprocess environments are completely stripped of all API keys, tokens, and passwords (`PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`).
3. **No Shell Invocations**:
   - Commands are invoked as direct argument arrays (`[python_bin, "-m", "pytest", ...]`) without passing through shell interpreters (`shell=False`).
   - Semicolons, pipes (`|`), ampersands (`&&`), and shell meta-characters in arguments are strictly rejected by `sanitize_test_args()`.
4. **Credential Redaction**:
   - Logging formatters and verification scanners use regex patterns (`RE_SECRETS`) to scrub API tokens and bearer credentials from outputs and diffs before persistence or display.
