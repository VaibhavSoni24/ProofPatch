# Nebius x NVIDIA Global AI Hackathon Submission Draft

- **Project Name**: ProofPatch
- **Tagline**: AI repairs you can verify.
- **Track**: Coding & Agentic Engineering
- **Secondary Objective**: Best Use of Tavily (Technical Research Integration)
- **Author**: Vaibhav Soni (`vaibhavsoni280506@gmail.com`)
- **Repository**: [https://github.com/VaibhavSoni24/ProofPatch](https://github.com/VaibhavSoni24/ProofPatch)

---

## 1. Project Summary

ProofPatch is an autonomous bug-fixing developer tool that transforms generative AI code suggestions into an observable, verified software engineering pipeline. Rather than generating code and asking developers to trust it, ProofPatch autonomously inspects repositories, reproduces reported defects via real test execution, synthesizes minimal unified diffs, runs post-patch regression suites in isolated sandboxes, and compiles structured, auditable evidence reports with raw command outputs, exit codes, and verification checks.

---

## 2. The Problem

Generative AI coding tools frequently suggest hallucinated or plausible-sounding code patches that fail subtle boundary conditions, break existing test suites, or introduce regressions. Developers waste significant time reviewing ungrounded PRs and manually reproducing issues. A code patch without verifiable proof of reproduction and passing regression tests is technical debt, not a fix.

---

## 3. The Solution & Key Differentiators

ProofPatch bridges generative AI and software engineering rigor through an evidence-first workflow:

1. **Observable Defect Reproduction**: Executes test commands in isolated workspaces before patching to prove the bug exists (Exit Code != 0). Halts as `INCONCLUSIVE` if tests pass or fail due to unrelated environment issues.
2. **Surgical Unified Diffs**: Synthesizes minimal diffs validated against path traversal (`../`), symlink escapes, protected files, and strict size caps.
3. **Deterministic Verification Audit**: Independently evaluates 6 concrete claims (exit codes, diff syntax, scope confinement, pristine source repository before/after SHA-256 manifest immutability & workspace isolation, and secret scrubbing).
4. **Isolated Execution Backends**: Supports local Docker isolation (`--network none`, memory & CPU caps) and official Nebius ConTree cloud container sandboxes (`token_factory_sandbox`) with symlink rejection and fail-closed transfer limits.
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
- **Model Compatibility**: Configurable via `NEBIUS_MODEL`. Requires an eligible open-source NVIDIA model identifier starting with `nvidia/` from the current Nebius Token Factory catalog (e.g. selected from active models at `tokenfactory.nebius.com/models` or `docs.tokenfactory.nebius.com`). Rejects non-NVIDIA models to enforce track compliance.
- **Adapter Design**:
  - Implements `BaseLLMProvider` with asynchronous completion handling and token usage tracking.
  - Handles rate limits (429), authentication failures (401), insufficient credits (402), and model errors (404) with typed exceptions.
  - Enforces strict execution limits (`MAX_MODEL_CALLS_PER_RUN=4`, `MAX_PATCH_ITERATIONS=2`) to prevent credit overconsumption.
- **Verification Status**: Validated locally using comprehensive HTTP mock test suites. Live execution requires entering a valid `NEBIUS_API_KEY` and active `NEBIUS_MODEL` in `.env`.

---

## 6. Official Token Factory Sandbox Integration (Nebius ConTree)

- **Architecture**: `TokenFactorySandboxBackend` integrates using official `contree-sdk` and `contree-client` (`ContreeAsyncClient`, `Contree`, `ContreeImage`, `UploadFileSpec`).
- **Lifecycle Implementation**:
  - Client construction: initializes configured `ContreeAsyncClient` (with token, base URL, timeout, and retry policy) from `contree_client.httpx` and passes it into `Contree(api_client)`.
  - Image acquisition via `client.images.use("python:3.11-slim", strict=True)`.
  - Workspace file transfer: safely walks repository rejecting symlinks and secret-bearing files, enforces cumulative and per-file transfer limits (failing closed if bounds are exceeded), and transfers allowed files into the remote container via `UploadFileSpec` in `image.run(shell="mkdir -p /workspace", files=upload_specs, disposable=False)`, followed by containerized dependency setup (`requirements.txt`, `pyproject.toml`, `setup.py` + `pytest`).
  - Command execution via `image.run(cwd="/workspace", disposable=False)` with state preservation across subsequent commands.
  - Strict outcome verification: extracts genuine exit codes, rejecting missing, null, or malformed exit codes to prevent false-positive test claims.
  - Patch synchronization: applies unified diff to local working copy and uploads modified files to container via `UploadFileSpec` in `image.run()`.
  - Explicit resource cleanup: awaits `api_client.close()` and releases remote container sessions upon run completion.
- **Verification Status**: Validated with comprehensive mock SDK unit tests covering client instantiation, container acquisition, file transfer, patch synchronization, timeouts, nonzero exit codes, missing exit code rejection, and cleanup. Requires live `CONTREE_TOKEN` or `NEBIUS_API_KEY` for live cloud execution.

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
- [x] Nebius ConTree Token Factory sandbox adapter implementation via official `contree-sdk` and `contree-client`.
- [x] Tavily Search API research integration.
- [x] Passing backend tests (120 tests) and frontend tests (3 tests) — 123 automated tests total.
- [x] Automated CI workflow (`.github/workflows/ci.yml`).
- [ ] Add valid `NEBIUS_API_KEY` and select active model in `.env` before live demonstration.
- [ ] Record and upload 2-3 minute YouTube demonstration video (see `docs/DEMO_SCRIPT.md`).
- [ ] Submit Devpost entry with public repository URL and video link.
