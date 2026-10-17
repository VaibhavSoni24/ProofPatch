"""Main FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.api import api_router
from app.core.config import get_settings
from app.core.errors import ProofPatchError
from app.core.logging import logger
from app.db.session import init_db
from app.repositories.security import SecurityViolationError, validate_path_containment

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
    """Root endpoint: serves frontend index.html in production, or welcome JSON in backend-only dev."""
    dist_dir = settings.get_frontend_dist_dir()
    if dist_dir and (dist_dir / "index.html").is_file():
        return FileResponse(dist_dir / "index.html", media_type="text/html")
    return {
        "app": settings.app_name,
        "tagline": "AI repairs you can verify",
        "docs_url": "/docs",
        "health_url": "/api/health",
        "config_status_url": "/api/config-status",
        "mode": settings.proofpatch_mode,
    }


@app.get("/{full_path:path}")
async def serve_spa_or_static(full_path: str):
    """Serve static assets or SPA client-side routes safely."""
    # Never intercept API or documentation routes
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="API route not found")
    if full_path in ("docs", "redoc", "openapi.json"):
        raise HTTPException(status_code=404, detail="Not Found")

    dist_dir = settings.get_frontend_dist_dir()
    if not dist_dir:
        raise HTTPException(status_code=404, detail="Frontend static distribution not found")

    # Reject null bytes
    if "\x00" in full_path:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Safe containment check against path traversal
    candidate = dist_dir / full_path
    try:
        target_path = validate_path_containment(candidate, dist_dir)
    except SecurityViolationError:
        raise HTTPException(status_code=403, detail="Access denied: path traversal prohibited")
    except Exception:
        raise HTTPException(status_code=403, detail="Access denied")

    # If it is an existing file, serve it directly
    if target_path.is_file():
        return FileResponse(target_path)

    # For asset-like files with extensions (e.g. .js, .css, .ico, .png, etc.), return 404
    # rather than falling back to index.html which causes MIME-type errors in browsers
    last_segment = full_path.rstrip("/").split("/")[-1]
    if "." in last_segment:
        raise HTTPException(status_code=404, detail=f"Asset '{last_segment}' not found")

    # Return index.html for SPA client-side routes
    index_file = dist_dir / "index.html"
    if index_file.is_file():
        return FileResponse(index_file, media_type="text/html")

    raise HTTPException(status_code=404, detail="Frontend entrypoint not found")
