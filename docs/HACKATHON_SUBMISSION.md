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

1. **Observable Defect Reproduction**: Executes test commands in isolated workspaces before patching to prove the bug exists (Exit Code != 0).
2. **Surgical Unified Diffs**: Synthesizes minimal diffs validated against path traversal (`../`) and strict size caps.
3. **Deterministic Verification Audit**: Independently evaluates 6 concrete claims (exit codes, diff syntax, scope confinement, immutability of original source, and secret scrubbing).
4. **Zero-Token Local Demo**: Ships with an offline demo featuring an intentionally buggy SaaS billing service (Issue #104) that requires zero API keys or cloud hardware.
5. **Downloadable Audit Artifacts**: Persists structured Markdown and JSON reports for compliance and code review.

---

## 4. Technical Architecture & Tech Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic, SQLAlchemy, SQLite, Pytest, Ruff.
- **Frontend**: React 19, TypeScript, Vite, custom responsive dark CSS design system, Lucide React icons, Vitest.
- **Inference Integration**: OpenAI-compatible adapter for Nebius Token Factory.
- **Search Integration**: Tavily Search API adapter for deep technical documentation retrieval.
- **Execution Sandbox**: Subprocess runner with environment sanitization and Docker container isolation support (`--network none`, memory & CPU caps).

---

## 5. Nebius Token Factory & NVIDIA Model Integration

- **Endpoint**: `https://api.tokenfactory.nebius.com/v1/`
- **Model Compatibility**: Designed for eligible NVIDIA open-source reasoning models from the Nebius catalog (e.g. `nvidia/nemotron-4-340b-instruct`).
- **Adapter Design**:
  - Implements `BaseLLMProvider` with structured completion handling.
  - Handles rate limits (429), authentication failures (401), insufficient credits (402), and model errors (404) with typed exceptions.
  - Enforces strict execution limits (`MAX_MODEL_CALLS_PER_run=4`, `MAX_PATCH_ITERATIONS=2`) to prevent credit overconsumption.
- **Verification Status**: Tested and validated locally using comprehensive HTTP mock test suites. Live execution requires entering a valid `NEBIUS_API_KEY` in the local `.env` file.

---

## 6. Tavily Search Integration (Best Use of Tavily)

- **Role**: During the diagnosis phase, ProofPatch autonomously queries Tavily to retrieve official framework documentation, recent breaking changes, and relevant technical issues.
- **Implementation**:
  - Direct integration with `https://api.tavily.com/search`.
  - Normalizes search results with source titles, URLs, and relevant content snippets.
  - Stores full citation provenance in the auditable evidence report.
  - Gracefully falls back when disabled or unconfigured without failing the repair loop.

---

## 7. Remaining User Actions Before Submission

To transition from the offline demonstration to a genuine live submission:
1. **Configure Nebius Credentials**:
   Add your Nebius Token Factory API key and desired NVIDIA model to your untracked `.env`:
   ```bash
   PROOFPATCH_MODE=live
   NEBIUS_API_KEY=your_actual_nebius_api_key
   NEBIUS_MODEL=nvidia/nemotron-4-340b-instruct
   ```
2. **Configure Tavily Credentials**:
   ```bash
   TAVILY_API_KEY=your_actual_tavily_api_key
   TAVILY_ENABLED=true
   ```
3. **Execute a Live Run**:
   Launch a repair against a supported public GitHub repository with `confirm_live_execution=true`.
4. **Record Demo Video**:
   Follow [docs/DEMO_SCRIPT.md](file:///e:/Projects/ProofPatch/docs/DEMO_SCRIPT.md) to record the 2-minute walkthrough.
