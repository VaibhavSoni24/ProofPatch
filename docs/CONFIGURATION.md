# ProofPatch Configuration Reference

This document provides a comprehensive reference for all configuration options available in ProofPatch. All settings are loaded from `.env` via `pydantic-settings` and can be overridden by system environment variables.

---

## Configuration Variables

| Variable | Type | Default | Required? | Description & Scope |
|---|---|---|---|---|
| `APP_NAME` | `string` | `ProofPatch` | No | Display name of the application. |
| `APP_ENV` | `string` | `development` | No | Environment runtime (`development`, `test`, `production`). |
| `APP_HOST` | `string` | `127.0.0.1` | No | Host IP address the backend server binds to. |
| `APP_PORT` | `integer` | `8000` | No | Port for backend REST API. |
| `FRONTEND_PORT` | `integer` | `5173` | No | Default Vite development server port. |
| `PROOFPATCH_MODE` | `string` | `demo` | **Yes** | Execution mode: `demo` (zero-credential offline sample workflow) or `live` (invokes Nebius Token Factory & Tavily). |
| `NEBIUS_API_KEY` | `string` | `""` | Only in `live` mode | API Key for Nebius Token Factory OpenAI-compatible inference. Must NEVER be committed to Git. |
| `NEBIUS_BASE_URL` | `string` | `https://api.tokenfactory.nebius.com/v1/` | No | OpenAI-compatible endpoint URL for Nebius Token Factory. |
| `NEBIUS_MODEL` | `string` | `""` | Only in `live` mode | Configured NVIDIA open-source model identifier (e.g. `nvidia/nemotron-4-340b-instruct` or an eligible model from the Nebius catalog). |
| `TAVILY_API_KEY` | `string` | `""` | Only if `TAVILY_ENABLED=true` | API key for Tavily Search API. Used to retrieve documentation, API updates, and security advisories. |
| `TAVILY_ENABLED` | `boolean` | `false` | No | Set to `true` to activate autonomous web research during the diagnosis stage. |
| `EXECUTION_BACKEND` | `string` | `docker` | No | Isolation backend for running test commands on external repositories (`docker` or `local`). |
| `ALLOW_EXTERNAL_REPOSITORIES` | `boolean` | `false` | No | Safety safeguard. When `false`, only bundled fixtures can be executed; prevents arbitrary untrusted git clone execution without explicit user consent. |
| `MAX_MODEL_CALLS_PER_RUN` | `integer` | `4` | No | Strict budget cap on the number of LLM inference calls allowed per repair run to prevent credit exhaustion. |
| `MAX_PATCH_ITERATIONS` | `integer` | `2` | No | Maximum number of repair loops if post-patch tests fail. |
| `MODEL_TIMEOUT_SECONDS` | `integer` | `90` | No | HTTP timeout (seconds) when calling Nebius Token Factory. |
| `SANDBOX_TIMEOUT_SECONDS` | `integer` | `60` | No | Execution timeout (seconds) for running test runner commands in isolated workspaces. |
| `MAX_REPOSITORY_FILES` | `integer` | `300` | No | Upper bound on files scanned during repository inspection to avoid memory overflow. |
| `MAX_CONTEXT_CHARACTERS` | `integer` | `40000` | No | Upper bound on source code characters injected into prompt context. |
| `MAX_PATCH_BYTES` | `integer` | `50000` | No | Maximum permitted byte size for an incoming unified diff patch. Rejects oversized patches. |
| `DATABASE_URL` | `string` | `sqlite:///./data/proofpatch.db` | No | SQLAlchemy database connection URI. Local SQLite file by default. |
| `WORKSPACE_ROOT` | `string` | `./data/workspaces` | No | Local filesystem directory where isolated checkout workspaces are instantiated. |
| `LOG_LEVEL` | `string` | `INFO` | No | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Redacts API keys automatically. |

---

## Execution Modes

### 1. `demo` Mode (Default)
- **Zero Credentials Needed**: Operates without any API keys or network access to model providers.
- **Deterministic Example**: Leverages the bundled `examples/buggy-python-service/` billing boundary defect.
- **Real Execution**: Test commands (`pytest`) actually execute, reproduce failure (exit code 1), apply a surgical patch, verify test passes (exit code 0), and compile verifiable audit evidence.
- **Banner**: Displays `LOCAL DEMO — no external AI API calls were made.`

### 2. `live` Mode
- **Requires**: `PROOFPATCH_MODE=live`, a valid `NEBIUS_API_KEY`, an eligible `NEBIUS_MODEL`, and explicit user confirmation per run.
- **Tavily (Optional)**: If `TAVILY_ENABLED=true` and `TAVILY_API_KEY` is supplied, autonomous web research is conducted during the diagnosis stage.
- **Docker Isolation**: External repositories are isolated inside disposable, non-networked Docker containers.
