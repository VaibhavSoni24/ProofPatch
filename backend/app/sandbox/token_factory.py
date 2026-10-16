"""Nebius Token Factory / ConTree Sandbox execution backend adapter using official contree-sdk.

Official documentation:
- https://github.com/nebius/contree-sdk
- https://docs.tokenfactory.nebius.com/

STATUS: Integration-tested with unit mocks. Requires live Nebius Token Factory / ConTree credentials for live verification.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from contree_sdk import Contree
except ImportError:
    Contree = None

from app.core.config import get_settings
from app.core.errors import ConfigurationError, ProviderError
from app.core.logging import logger
from app.sandbox.base import BaseExecutionBackend, ExecutionResult
from app.sandbox.limits import (
    DEFAULT_COMMAND_TIMEOUT_SECONDS,
    MAX_OUTPUT_CHARACTERS,
    sanitize_test_args,
)

settings = get_settings()


class TokenFactorySandboxBackend(BaseExecutionBackend):
    """Adapter for remote cloud container sandbox execution via official Nebius ConTree SDK."""

    backend_name: str = "token_factory_sandbox"

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        image_name: str = "python:3.11-slim",
        timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
        client: Optional[Any] = None,
    ):
        self.token = (token or settings.contree_token or settings.nebius_api_key).strip()
        self.base_url = (base_url or settings.contree_base_url).rstrip("/")
        self.image_name = image_name
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._remote_image = None
        self._files_transferred = False

    def _validate_credentials(self) -> None:
        """Ensure sandbox credentials are present before attempting operations."""
        if not self.token:
            raise ConfigurationError(
                "Token Factory Sandbox requires authentication credentials. "
                "Please configure CONTREE_TOKEN or NEBIUS_API_KEY in your environment."
            )

    async def _get_client(self) -> Any:
        """Instantiate official Contree client if not already provided."""
        if self._client:
            return self._client
        if Contree is None:
            raise ConfigurationError(
                "contree-sdk is not installed. Run `pip install contree-sdk` to use Token Factory sandboxes."
            )
        self._validate_credentials()
        self._client = Contree(base_url=self.base_url, token=self.token)
        return self._client

    async def acquire_session(self) -> Any:
        """Create or provision an isolated remote ConTree execution container from base image."""
        client = await self._get_client()
        logger.info(
            "Initializing Token Factory ConTree container with base image '%s'...", self.image_name
        )
        try:
            self._remote_image = await client.images.use(self.image_name, strict=True)
            return self._remote_image
        except Exception as exc:
            logger.error("Failed to acquire ConTree sandbox image: %s", exc)
            raise ProviderError(
                "TokenFactorySandbox",
                f"Failed to acquire ConTree image '{self.image_name}': {str(exc)}",
                status_code=502,
            )

    async def transfer_workspace(self, workspace_dir: Path) -> None:
        """Collect bounded repository contents from workspace_dir and transfer into remote sandbox."""
        self._validate_credentials()
        if not self._remote_image:
            await self.acquire_session()

        if not workspace_dir.is_dir():
            raise FileNotFoundError(f"Local workspace directory does not exist: {workspace_dir}")

        # Scan files with bounded limit to prevent memory/payload exhaustion
        files_to_transfer: Dict[str, bytes] = {}
        scanned_count = 0
        ignored_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}

        for item in workspace_dir.rglob("*"):
            if any(part in ignored_dirs for part in item.parts):
                continue
            if item.is_file():
                scanned_count += 1
                if scanned_count > settings.max_repository_files:
                    logger.warning(
                        "Reached maximum repository file cap (%d); skipping remaining files.",
                        settings.max_repository_files,
                    )
                    break
                try:
                    rel_path = item.relative_to(workspace_dir).as_posix()
                    content = item.read_bytes()
                    # Bounded size per file (e.g. 500KB)
                    if len(content) <= settings.max_patch_bytes * 10:
                        remote_dest = f"/workspace/{rel_path}"
                        files_to_transfer[remote_dest] = content
                except Exception as read_err:
                    logger.debug("Skipping unreadable file %s: %s", item, read_err)

        logger.info(
            "Transferring %d repository file(s) into remote ConTree sandbox (/workspace)...",
            len(files_to_transfer),
        )
        try:
            # Create remote workspace directory
            self._remote_image = await self._remote_image.run(
                shell="mkdir -p /workspace", disposable=False
            )
            # Apply files into the remote container filesystem
            if files_to_transfer:
                self._remote_image = await self._remote_image.apply_files(files_to_transfer)

            # Ensure pytest is available inside the container
            self._remote_image = await self._remote_image.run(
                shell="pip install --no-cache-dir pytest",
                cwd="/workspace",
                disposable=False,
                timeout=float(self.timeout_seconds),
            )
            self._files_transferred = True
        except Exception as exc:
            logger.error("Error during ConTree workspace transfer: %s", exc)
            raise ProviderError(
                "TokenFactorySandbox",
                f"Failed to transfer workspace to ConTree sandbox: {str(exc)}",
                status_code=502,
            )

    async def execute_tests(
        self,
        workspace_dir: Path,
        test_args: Optional[List[str]] = None,
        timeout_seconds: int = 60,
    ) -> ExecutionResult:
        """Execute test suite inside the remote ConTree sandbox with state preservation."""
        self._validate_credentials()
        if not self._remote_image:
            await self.acquire_session()
        if not self._files_transferred:
            await self.transfer_workspace(workspace_dir)

        sanitized_args = sanitize_test_args(test_args or ["tests", "-v"])
        cmd_str = f"pytest {' '.join(sanitized_args)}"

        logger.info("Executing test command in ConTree sandbox: %s (cwd=/workspace)", cmd_str)
        try:
            # Run non-disposable to preserve state across subsequent commands
            self._remote_image = await self._remote_image.run(
                shell=cmd_str,
                cwd="/workspace",
                disposable=False,
                timeout=float(timeout_seconds),
            )
            exit_code = getattr(self._remote_image, "exit_code", 0)
            if exit_code is None:
                exit_code = 0
            stdout = getattr(self._remote_image, "stdout", "") or ""
            stderr = getattr(self._remote_image, "stderr", "") or ""
            output = f"{stdout}\n{stderr}".strip()
            if len(output) > MAX_OUTPUT_CHARACTERS:
                output = output[:MAX_OUTPUT_CHARACTERS] + "\n... [TRUNCATED]"

            return ExecutionResult(
                exit_code=exit_code,
                output=output,
                stdout=stdout,
                stderr=stderr,
                timed_out=(exit_code == 124),
                backend_name=self.backend_name,
                metadata={
                    "isolation": "nebius_contree_sdk_sandbox",
                    "verification_status": "integration_mock_verified",
                },
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                exit_code=124,
                output=f"Command timed out after {timeout_seconds}s.",
                timed_out=True,
                backend_name=self.backend_name,
                metadata={"isolation": "nebius_contree_sdk_sandbox"},
            )
        except Exception as exc:
            if "timeout" in str(exc).lower():
                return ExecutionResult(
                    exit_code=124,
                    output=f"Execution timed out: {str(exc)}",
                    timed_out=True,
                    backend_name=self.backend_name,
                    metadata={"isolation": "nebius_contree_sdk_sandbox"},
                )
            logger.error("Error during ConTree command execution: %s", exc)
            raise ProviderError(
                "TokenFactorySandbox",
                f"ConTree execution failed: {str(exc)}",
                status_code=502,
            )

    async def apply_patch(self, patch_diff: str, workspace_dir: Path) -> List[str]:
        """Apply patch to local copy and synchronize patch inside remote ConTree workspace."""
        from app.agents.patch_parser import apply_patch_to_workspace

        # 1. Apply to local working copy for inspection & reporting
        modified = await asyncio.to_thread(apply_patch_to_workspace, workspace_dir, patch_diff)

        # 2. Synchronize modified files into remote sandbox
        if self._remote_image:
            remote_patch_files: Dict[str, bytes] = {}
            for rel_file in modified:
                local_file = workspace_dir / rel_file
                if local_file.is_file():
                    remote_patch_files[f"/workspace/{rel_file}"] = local_file.read_bytes()
            if remote_patch_files:
                self._remote_image = await self._remote_image.apply_files(remote_patch_files)

        return modified

    async def cleanup(self) -> None:
        """Dispose remote sandbox resources."""
        logger.info("Disposing ConTree sandbox resources...")
        self._remote_image = None
        self._client = None
        self._files_transferred = False
