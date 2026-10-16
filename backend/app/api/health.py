"""Health check endpoint (zero inference calls, minimal local overhead)."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
def get_health():
    """Inexpensive health probe returning service status."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "mode": settings.proofpatch_mode,
    }
