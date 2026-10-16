# ProofPatch Engineering & Development Log

This document records the chronological development trajectory, milestones, and architectural decisions made while building ProofPatch from scratch.

---

## Milestone 1: Workspace & Tooling Initialization (Phase A)
- Inspected development environment (Windows, Python 3.10.11, Node.js v24.16.0, npm 11.13.0).
- Configured local Git author identity for Vaibhav Soni (`vaibhavsoni280506@gmail.com`).
- Created core repository files: `.gitignore`, `.editorconfig`, `.env.example`, `.env`, `LICENSE` (MIT), `SECURITY.md`, `CONTRIBUTING.md`, `Makefile`, and `docker-compose.yml`.
- Configured GitHub Actions CI workflow in `.github/workflows/ci.yml`.
- **Git Commit**: `16d5c6b chore: initialize ProofPatch workspace and project structure`.

---

## Milestone 2: Reproducible Buggy Example Service (Phase C)
- Implemented `examples/buggy-python-service/`:
  - `src/billing.py`: SaaS subscription calculator with intentional boundary defect (`if seats > 6 and seats <= 20:`).
  - `tests/test_billing.py`: Comprehensive test suite where `test_growth_tier_boundary_six_seats` fails deterministically with Exit Code 1.
  - Verified baseline failure via pytest: `1 failed, 6 passed in 0.08s`.
- **Git Commit**: `da47eec feat(demo): add buggy python service example for reproducible test workflow`.

---

## Milestone 3: Backend Foundation & Deterministic Demo Engine (Phase B & C)
- Built FastAPI application with SQLite database persistence via SQLAlchemy.
- Implemented Pydantic models for runs, stage events, and evidence reports.
- Created `patch_parser.py`: strict unified diff validation, path traversal prevention, and atomic file patcher.
- Created `verification.py`: independent deterministic auditor checking 6 concrete safety and execution invariants.
- Created `demo.py`: deterministic runner copying bundled service into an isolated workspace, running baseline tests, applying surgical patch, running regression tests, and compiling evidence report.
- Achieved green test suite: 19 pytest tests passed, clean ruff linting.
- **Git Commit**: `b2cf74f feat(backend): implement core schemas, database, demo service, and run APIs`.

---

## Milestone 4: Nebius Token Factory & Tavily Integrations (Phase E)
- Implemented `NebiusTokenFactoryProvider` supporting OpenAI-compatible chat completions against `https://api.tokenfactory.nebius.com/v1/` for eligible NVIDIA open-source models.
- Implemented `TavilySearchProvider` for autonomous retrieval of framework documentation and technical context.
- Implemented `git.py` for public GitHub repository validation and shallow cloning.
- Implemented `inspection.py` for bounded repository file discovery.
- Implemented `orchestrator.py` for bounded multi-stage repair execution with retry limits.
- Added comprehensive mocked test suites (`test_nebius_provider.py`, `test_tavily_provider.py`, `test_git_repository.py`, `test_orchestrator.py`) verifying zero external network calls during testing.
- All 34 backend pytest tests passing.
- **Git Commit**: `f7c6528 feat(integrations): implement Nebius Token Factory and Tavily providers with bounded orchestration`.

---

## Milestone 5: Complete Frontend Experience (Phase D)
- Scaffolding with React 19, TypeScript, and Vite.
- Implemented custom dark developer tool CSS design system (`styles/index.css`) with tokens, high-contrast badges, cards, and interactive tabs.
- Created feature components:
  - `Header`: Navigation, mode pill, primary demo action, and transparent zero-credit demo banner.
  - `DashboardView`: Metrics, quickstart hero, and recent runs table.
  - `NewRepairView`: Preset selector, custom GitHub repo input, and live safeguard confirmation.
  - `RunDetailsView`: 8 sub-tabs covering stages timeline, reproduction terminal, diagnosis, Tavily research citations, surgical diff viewer, before-and-after test comparison, verification checks, and report export.
  - `EvidenceView`: Audit registry with one-click JSON/Markdown downloads.
  - `SettingsView`: Sanitized provider status and instructions for activating live credentials.
- All 3 Vitest frontend tests passed; production build passed (`tsc -b && vite build`) in 363ms.
- **Git Commit**: `d67940d feat(ui): build developer dashboard, run history, diff viewer, and evidence screens`.
