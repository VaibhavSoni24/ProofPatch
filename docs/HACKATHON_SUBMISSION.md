# Nebius x NVIDIA Global AI Hackathon Submission Draft

- **Project Name**: ProofPatch
- **Tagline**: AI repairs you can verify.
- **Track**: Coding & Agentic Engineering
- **Secondary Objective**: Best Use of Tavily (Technical Research Integration)
- **Author**: Vaibhav Soni (`vaibhavsoni280506@gmail.com`)
- **Repository**: [https://github.com/VaibhavSoni24/ProofPatch](https://github.com/VaibhavSoni24/ProofPatch)

---

## 1. Project Summary

ProofPatch is an autonomous bug-fixing developer tool that transforms generative AI code suggestions into an observable, verified software engineering pipeline. Rather than generating code and asking developers to trust it, ProofPatch autonomously inspects repositories, reproduces reported defects via real test execution, synthesizes minimal unified diffs, runs post-patch regression suites in isolated sandboxes, and compiles immutable audit reports with raw command outputs, exit codes, and verification checks.

---

## 2. The Problem

Generative AI coding tools frequently suggest hallucinated or plausible-sounding code patches that fail subtle boundary conditions, break existing test suites, or introduce regressions. Developers waste significant time reviewing ungrounded PRs and manually reproducing issues. A code patch without verifiable proof of reproduction and passing regression tests is technical debt, not a fix.

---

## 3. The Solution & Key Differentiators

ProofPatch bridges generative AI and software engineering rigor through an evidence-first workflow:

1. **Observable Defect Reproduction**: Executes test commands in isolated workspaces before patching to prove the bug exists (Exit Code != 0). Halts as `INCONCLUSIVE` if tests pass or fail due to unrelated environment issues.
2. **Surgical Unified Diffs**: Synthesizes minimal diffs validated against path traversal (`../`), protected files, and strict size caps.
3. **Deterministic Verification Audit**: Independently evaluates 6 concrete claims (exit codes, diff syntax, scope confinement, immutability of original source, and secret scrubbing).
4. **Isolated Execution Backends**: Supports local Docker isolation (`--network none`, memory & CPU caps) and official Nebius ConTree cloud container sandboxes (`token_factory_sandbox`).
5. **Zero-Token Local Demo**: Ships with an offline demo featuring an intentionally buggy SaaS billing service (Issue #104) that requires zero API keys or cloud hardware.
6. **Downloadable Audit Artifacts**: Persists structured Markdown and JSON reports for compliance and code review.

---

## 4. Technical Architecture & Tech Stack

- **Backend**: Python 3.10+, FastAPI (fully asynchronous), Pydantic, SQLAlchemy, SQLite, Pytest, Ruff.
- **Frontend**: React 19, TypeScript, Vite, custom responsive dark CSS design system, Lucide React icons, Vitest.
- **Inference Integration**: Asynchronous OpenAI-compatible adapter for Nebius Token Factory with typed `ProviderResponse`.
- **Search Integration**: Asynchronous Tavily Search API adapter for deep technical documentation retrieval with typed `SearchResponse`.
- **Execution Sandboxes**: `LocalExecutionBackend` (demo only), `DockerExecutionBackend` (non-networked local container), and `TokenFactorySandboxBackend` (Nebius ConTree cloud container runtime).

---

## 5. Nebius Token Factory & NVIDIA Model Integration

- **Endpoint**: `https://api.tokenfactory.nebius.com/v1/`
- **Model Compatibility**: Configurable via `NEBIUS_MODEL`. Designed for eligible open-source NVIDIA reasoning models from the Nebius Token Factory catalog (e.g. `nvidia/nemotron-4-340b-instruct` or current active Nemotron identifiers from `tokenfactory.nebius.com/models`).
- **Adapter Design**:
  - Implements `BaseLLMProvider` with asynchronous completion handling and token usage tracking.
  - Handles rate limits (429), authentication failures (401), insufficient credits (402), and model errors (404) with typed exceptions.
  - Enforces strict execution limits (`MAX_MODEL_CALLS_PER_RUN=4`, `MAX_PATCH_ITERATIONS=2`) to prevent credit overconsumption.
- **Verification Status**: Validated locally using comprehensive HTTP mock test suites. Live execution requires entering a valid `NEBIUS_API_KEY` and active `NEBIUS_MODEL` in `.env`.

---

## 6. Official Token Factory Sandbox Integration (Nebius ConTree)

- **Architecture**: `TokenFactorySandboxBackend` integrates with the Nebius ConTree container runtime API (`https://api.tokenfactory.nebius.com/sandboxes`).
- **Lifecycle Implementation**:
  - Session provisioning (`POST /sessions`) with `python:3.11-slim` base image.
  - Test command execution (`POST /sessions/{id}/exec`) with timeout controls.
  - Session cleanup and disposal (`DELETE /sessions/{id}`) upon run completion.
- **Verification Status**: Tested with unit mocks for session lifecycle, command execution, and disposal. Runtime verification with live credentials will take place upon final hackathon deployment.

---

## 7. Tavily Search Integration (Best Use of Tavily)

- **Role**: During the diagnosis phase, ProofPatch autonomously queries Tavily to retrieve official framework documentation, recent breaking changes, and relevant technical issues.
- **Implementation**:
  - Direct integration with `https://api.tavily.com/search`.
  - Normalizes search results with source titles, URLs, and relevant content snippets.
  - Stores full citation provenance in the auditable evidence report.
  - Gracefully falls back when disabled or unconfigured without failing the repair loop.

---

## 8. Hackathon Submission Checklist

- [x] Working open-source codebase with clean monorepo structure.
- [x] MIT License and Security Policy.
- [x] Functional zero-credential deterministic demo mode.
- [x] Nebius Token Factory adapter with eligible NVIDIA model configuration.
- [x] Nebius ConTree Token Factory sandbox adapter implementation.
- [x] Tavily Search API research integration.
- [x] Passing backend tests (46 tests) and frontend tests (3 tests).
- [x] Automated CI workflow (`.github/workflows/ci.yml`).
- [ ] Add valid `NEBIUS_API_KEY` and select active model in `.env` before live demonstration.
- [ ] Record and upload 2-3 minute YouTube demonstration video (see `docs/DEMO_SCRIPT.md`).
- [ ] Submit Devpost entry with public repository URL and video link.
