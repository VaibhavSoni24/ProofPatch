"""Factory for resolving and instantiating sandbox execution backends."""

from typing import Optional

from app.core.config import get_settings
from app.core.errors import SecurityError
from app.sandbox.base import BaseExecutionBackend
from app.sandbox.docker_backend import DockerExecutionBackend
from app.sandbox.local_runner import LocalExecutionBackend
from app.sandbox.token_factory import TokenFactorySandboxBackend

settings = get_settings()


def get_execution_backend(
    mode: str = "demo",
    backend_override: Optional[str] = None,
) -> BaseExecutionBackend:
    """Resolve appropriate execution backend based on mode and safety configuration."""
    target_backend = (backend_override or settings.execution_backend).lower()

    if mode == "demo":
        return LocalExecutionBackend(allow_untrusted=True)

    # In Live mode, untrusted code execution MUST be isolated
    if target_backend == "demo" or target_backend == "local":
        raise SecurityError(
            "Local host subprocess execution is strictly prohibited for external repositories. "
            "Please configure 'docker' or 'token_factory_sandbox' as your EXECUTION_BACKEND."
        )

    if target_backend == "token_factory_sandbox":
        return TokenFactorySandboxBackend()

    # Default live execution backend is Docker
    return DockerExecutionBackend()
