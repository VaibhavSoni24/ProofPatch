"""Main FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import get_settings
from app.core.errors import ProofPatchError
from app.core.logging import logger
from app.db.session import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager to initialize database on startup."""
    logger.info("Initializing ProofPatch application database...")
    init_db()
    logger.info("ProofPatch backend ready (Mode: %s).", settings.proofpatch_mode)
    yield
    logger.info("ProofPatch backend shutting down.")


app = FastAPI(
    title="ProofPatch API",
    description="Autonomous Bug Fixing With Verifiable Evidence — Backend Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration for modern developer frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ProofPatchError)
async def handle_proofpatch_error(request: Request, exc: ProofPatchError):
    """Centralized exception handler for custom ProofPatch errors."""
    logger.warning("ProofPatch domain error (%s): %s", exc.status_code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "status_code": exc.status_code},
    )


# Mount unified API routes
app.include_router(api_router)


@app.get("/")
def root():
    """Root redirect / welcome message."""
    return {
        "app": settings.app_name,
        "tagline": "AI repairs you can verify",
        "docs_url": "/docs",
        "health_url": "/api/health",
        "config_status_url": "/api/config-status",
        "mode": settings.proofpatch_mode,
    }
