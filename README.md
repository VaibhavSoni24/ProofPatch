# ProofPatch — AI Repairs You Can Verify

> **Autonomous bug fixing with verifiable evidence.**
> Built for the Nebius x NVIDIA Global AI Hackathon (Track: Coding & Agentic Engineering).

ProofPatch bridges the gap between AI code generation and software engineering rigor. Instead of merely proposing code patches, ProofPatch autonomously inspects repositories, reproduces defects via deterministic test execution, generates surgical patches, executes regression tests in sandboxed environments, and produces an immutable, auditable evidence trail.

---

## Key Differentiators

1. **Evidence-Driven Verification**: Never accept a model's claim without executable proof. Every run logs exact commands, stdout/stderr, exit codes, and unified diffs.
2. **Zero-Credential Local Demo**: Immediate out-of-the-box local demo workflow with an intentionally buggy service—no API keys or hardware required.
3. **OpenAI-Compatible Nebius Token Factory Adapter**: Supports eligible NVIDIA open-source reasoning models (e.g., Nemotron family) for live autonomous repair.
4. **Deep Context Research with Tavily**: Autonomous search integration to retrieve framework docs, security advisories, and API changes.
5. **Strict Isolation & Safety Guardrails**: Path traversal prevention, patch size limits, command execution sandboxing, and sensitive secret scrubbing.

---

## Quick Start (Demo Mode)

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

pip install -e backend
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to explore the dashboard and launch the deterministic demo repair.

---

## Documentation
- [Architecture & Workflow](docs/ARCHITECTURE.md)
- [Configuration Reference](docs/CONFIGURATION.md)
- [Testing Guide](docs/TESTING.md)
- [Demo Script](docs/DEMO_SCRIPT.md)
- [Hackathon Submission Draft](docs/HACKATHON_SUBMISSION.md)
- [Security Policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

---

## License
MIT License. Copyright (c) 2026 Vaibhav Soni.
