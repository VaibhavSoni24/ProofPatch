# Contributing to ProofPatch

Thank you for your interest in contributing to ProofPatch!

## Code of Conduct

Please maintain a collaborative, respectful, and evidence-driven development environment.

## Development Setup

ProofPatch consists of:
- **Backend**: FastAPI + Python 3.10+ (SQLite, Pydantic, Ruff, Pytest)
- **Frontend**: React + TypeScript + Vite + modern CSS design system

### Prerequisites
- Python 3.10 or higher
- Node.js 18+ and npm
- Git

### Quick Setup

1. **Clone and enter repository**:
   ```bash
   git clone https://github.com/VaibhavSoni24/ProofPatch.git
   cd ProofPatch
   ```

2. **Backend**:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate

   pip install -e backend
   ```

3. **Frontend**:
   ```bash
   cd frontend
   npm install
   ```

4. **Verify Tests**:
   - Backend: `pytest backend/tests`
   - Frontend: `npm test` inside `frontend/`

## Commit Discipline

We follow Conventional Commits:
- `feat(scope): message`
- `fix(scope): message`
- `test(scope): message`
- `docs(scope): message`
- `refactor(scope): message`
- `chore(scope): message`

Never commit secrets, credentials, `.env` files, or untracked temporary data.
