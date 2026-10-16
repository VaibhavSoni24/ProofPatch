"""Application configuration and environment settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for ProofPatch backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "ProofPatch"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    frontend_port: int = 5173

    # Execution Mode: "demo" (deterministic offline) or "live" (Nebius + Tavily)
    proofpatch_mode: Literal["demo", "live"] = "demo"

    # Nebius Token Factory (OpenAI-compatible inference)
    nebius_api_key: str = ""
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    nebius_model: str = ""

    # Tavily Search API
    tavily_api_key: str = ""
    tavily_enabled: bool = False

    # Safety and execution limits
    execution_backend: Literal["docker", "local"] = "docker"
    allow_external_repositories: bool = False
    max_model_calls_per_run: int = 4
    max_patch_iterations: int = 2
    model_timeout_seconds: int = 90
    sandbox_timeout_seconds: int = 60
    max_repository_files: int = 300
    max_context_characters: int = 40000
    max_patch_bytes: int = 50000

    # Local persistence and workspaces
    database_url: str = "sqlite:///./data/proofpatch.db"
    workspace_root: str = "./data/workspaces"

    # Logging
    log_level: str = "INFO"

    @property
    def is_demo_mode(self) -> bool:
        """Return True if running in zero-credential demo mode."""
        return self.proofpatch_mode == "demo"

    @property
    def is_nebius_configured(self) -> bool:
        """Return True only if Nebius API key and model are explicitly provided."""
        return bool(self.nebius_api_key.strip() and self.nebius_model.strip())

    @property
    def is_tavily_configured(self) -> bool:
        """Return True only if Tavily is enabled and API key is provided."""
        return bool(self.tavily_enabled and self.tavily_api_key.strip())

    def get_workspace_dir(self) -> Path:
        """Ensure and return the workspace root directory."""
        path = Path(self.workspace_root).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache()
def get_settings() -> Settings:
    """Singleton cached provider for application settings."""
    return Settings()
