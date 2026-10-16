"""Configuration status schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ConfigStatusResponse(BaseModel):
    """Sanitized public configuration status (zero secrets exposed)."""

    model_config = ConfigDict(from_attributes=True)

    app_name: str
    app_env: str
    mode: str
    nebius_configured: bool
    nebius_model: Optional[str] = None
    nebius_base_url: str
    tavily_enabled: bool
    tavily_configured: bool
    docker_available: bool
    max_model_calls: int
    max_patch_iterations: int
    timeout_seconds: int
