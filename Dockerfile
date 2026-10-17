# Multi-stage Dockerfile for ProofPatch (Frontend + Backend in unified production container)

# Stage 1: Build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install minimal OS dependencies for repository operations and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies and pytest for bundled demo reproduction and regression runner
COPY backend/pyproject.toml ./backend/
RUN pip install --no-cache-dir "./backend" "pytest>=8.0.0"

# Copy backend application source
COPY backend/app/ ./backend/app/

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy bundled deterministic demo fixture
COPY examples/ ./examples/

# Create runtime data directories and unprivileged non-root user
RUN groupadd -r proofpatch && useradd -r -g proofpatch -d /app -s /sbin/nologin proofpatch \
    && mkdir -p /app/data/workspaces \
    && chown -R proofpatch:proofpatch /app

ENV APP_NAME="ProofPatch" \
    APP_ENV="production" \
    APP_HOST="0.0.0.0" \
    PORT=8000 \
    PROOFPATCH_MODE="demo" \
    DATABASE_URL="sqlite:////app/data/proofpatch.db" \
    WORKSPACE_ROOT="/app/data/workspaces" \
    FRONTEND_DIST_DIR="/app/frontend/dist" \
    PYTHONPATH="/app/backend" \
    PYTHONUNBUFFERED=1

USER proofpatch

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
