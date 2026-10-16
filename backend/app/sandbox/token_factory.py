"""Nebius Token Factory / ConTree Sandbox execution backend adapter.

Official documentation:
- https://docs.tokenfactory.nebius.com/
- https://github.com/nebius/contree-sdk
- https://github.com/nebius/contree-mcp

STATUS: Integration-tested with unit mocks. Requires live Nebius Token Factory / ConTree credentials for live verification.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.errors import ConfigurationError, ProviderError
from app.core.logging import logger
from app.sandbox.base import BaseExecutionBackend, ExecutionResult
from app.sandbox.limits import DEFAULT_COMMAND_TIMEOUT_SECONDS, sanitize_test_args

settings = get_settings()


class TokenFactorySandboxBackend(BaseExecutionBackend):
    """Adapter for remote cloud container sandbox execution via Nebius Token Factory / ConTree."""

    backend_name: str = "token_factory_sandbox"

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        image: str = "python:3.11-slim",
        timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    ):
        self.token = (token or settings.contree_token or settings.nebius_api_key).strip()
        self.base_url = (base_url or settings.contree_base_url).rstrip("/")
        self.image = image
        self.timeout_seconds = timeout_seconds
        self.session_id: Optional[str] = None

    def _validate_credentials(self) -> None:
        """Ensure sandbox credentials are present before attempting operations."""
        if not self.token:
            raise ConfigurationError(
                "Token Factory Sandbox requires authentication credentials. "
                "Please configure CONTREE_TOKEN or NEBIUS_API_KEY in your environment."
            )

    async def acquire_session(self) -> str:
        """Create or provision an isolated remote ConTree execution container session."""
        self._validate_credentials()
        endpoint = f"{self.base_url}/sessions"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "image": self.image,
            "disposable": False,
            "timeout_seconds": self.timeout_seconds,
        }

        logger.info(
            "Requesting Token Factory ConTree sandbox session for image '%s'...", self.image
        )
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                res = await client.post(endpoint, headers=headers, json=payload)

            if res.status_code in (200, 201):
                data = res.json()
                self.session_id = data.get("session_id") or data.get("id") or "session_default"
                logger.info("Acquired Token Factory sandbox session: %s", self.session_id)
                return self.session_id
            elif res.status_code == 401:
                raise ProviderError(
                    "TokenFactorySandbox",
                    "Authentication failed: invalid CONTREE_TOKEN or NEBIUS_API_KEY.",
                    status_code=401,
                )
            else:
                raise ProviderError(
                    "TokenFactorySandbox",
                    f"Failed to provision sandbox session (HTTP {res.status_code}): {res.text[:200]}",
                    status_code=res.status_code,
                )
        except httpx.TimeoutException:
            raise ProviderError(
                "TokenFactorySandbox",
                f"Session provisioning timed out after {self.timeout_seconds}s.",
                status_code=504,
            )
        except httpx.RequestError as exc:
            raise ProviderError(
                "TokenFactorySandbox",
                f"Network error connecting to Token Factory Sandbox: {str(exc)}",
                status_code=502,
            )

    async def execute_tests(
        self,
        workspace_dir: Path,
        test_args: Optional[List[str]] = None,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        """Execute test suite inside the remote Token Factory sandbox."""
        self._validate_credentials()

        if not self.session_id:
            await self.acquire_session()

        sanitized_args = sanitize_test_args(test_args or ["tests", "-v"])
        cmd_str = f"pytest {' '.join(sanitized_args)}"

        endpoint = f"{self.base_url}/sessions/{self.session_id}/exec"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "command": cmd_str,
            "timeout": timeout_seconds,
            "disposable": False,
        }

        logger.info(
            "Executing test command in Token Factory sandbox session %s: %s",
            self.session_id,
            cmd_str,
        )

        try:
            async with httpx.AsyncClient(timeout=float(timeout_seconds + 5)) as client:
                res = await client.post(endpoint, headers=headers, json=payload)

            if res.status_code == 200:
                data = res.json()
                exit_code = data.get("exit_code", 0)
                stdout = data.get("stdout", "")
                stderr = data.get("stderr", "")
                output = f"{stdout}\n{stderr}".strip()

                return ExecutionResult(
                    exit_code=exit_code,
                    output=output,
                    stdout=stdout,
                    stderr=stderr,
                    timed_out=(exit_code == 124),
                    backend_name=self.backend_name,
                    metadata={
                        "session_id": self.session_id,
                        "isolation": "nebius_contree_sandbox",
                        "verification_status": "integration_mock_verified",
                    },
                )
            elif res.status_code == 401:
                raise ProviderError(
                    "TokenFactorySandbox",
                    "Authentication failed during command execution.",
                    status_code=401,
                )
            else:
                raise ProviderError(
                    "TokenFactorySandbox",
                    f"Execution request failed with HTTP {res.status_code}: {res.text[:200]}",
                    status_code=res.status_code,
                )
        except httpx.TimeoutException:
            return ExecutionResult(
                exit_code=124,
                output=f"Command timed out after {timeout_seconds}s.",
                timed_out=True,
                backend_name=self.backend_name,
            )
        except httpx.RequestError as exc:
            raise ProviderError(
                "TokenFactorySandbox",
                f"Communication error with sandbox: {str(exc)}",
                status_code=502,
            )

    async def cleanup(self) -> None:
        """Terminate and clean up remote sandbox session."""
        if not self.session_id or not self.token:
            return

        endpoint = f"{self.base_url}/sessions/{self.session_id}"
        headers = {"Authorization": f"Bearer {self.token}"}

        logger.info("Cleaning up Token Factory sandbox session %s...", self.session_id)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.delete(endpoint, headers=headers)
        except Exception as exc:
            logger.warning("Failed to clean up sandbox session %s: %s", self.session_id, exc)
        finally:
            self.session_id = None
