"""Safe public configuration status endpoint (zero credentials exposed)."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.sandbox.docker_runner import is_docker_available
from app.schemas.config import ConfigStatusResponse

router = APIRouter(tags=["Config"])
settings = get_settings()


@router.get("/config-status", response_model=ConfigStatusResponse)
def get_config_status():
    """Return sanitized system configuration status for UI display."""
    return ConfigStatusResponse(
        app_name=settings.app_name,
        app_env=settings.app_env,
        mode=settings.proofpatch_mode,
        nebius_configured=settings.is_nebius_configured,
        nebius_model=settings.nebius_model if settings.nebius_model else None,
        nebius_base_url=settings.nebius_base_url,
        tavily_enabled=settings.tavily_enabled,
        tavily_configured=settings.is_tavily_configured,
        docker_available=is_docker_available(),
        max_model_calls=settings.max_model_calls_per_run,
        max_patch_iterations=settings.max_patch_iterations,
        timeout_seconds=settings.sandbox_timeout_seconds,
    )
