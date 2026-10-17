"""Nebius Token Factory / ConTree Sandbox execution backend adapter using official contree-sdk.

Official documentation:
- https://github.com/nebius/contree-sdk
- https://docs.tokenfactory.nebius.com/

Client Interface:
- Constructs ContreeAsyncClient from contree_client.httpx with authentication token, base URL, timeout, and retry policy.
- Instantiates Contree client wrapping ContreeAsyncClient for asynchronous orchestration.
- Transfers bounded repository files via UploadFileSpec in image.run(files=[...], disposable=False).
- Executes tests in versioned container filesystem and collects genuine exit codes and output.
- Rejects missing, malformed, or unavailable exit codes to eliminate false-positive test results.
- Releases and closes client resources during session cleanup.

STATUS: Integration-tested with unit mocks. Requires live Nebius Token Factory / ConTree credentials for live verification.
"""

import asyncio
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Set

try:
    from contree_client.httpx import ContreeAsyncClient
    from contree_client.runtime import RetryPolicy
except ImportError:
    ContreeAsyncClient = None
    RetryPolicy = None

try:
    from contree_sdk import Contree
    from contree_sdk.utils.models.file import UploadFileSpec
except ImportError:
    Contree = None
    UploadFileSpec = None

from app.core.config import get_settings
from app.core.errors import ConfigurationError, ProviderError, SecurityViolationError
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
        api_client: Optional[Any] = None,
    ):
        self.token = (token or settings.contree_token or settings.nebius_api_key).strip()
        self.base_url = (base_url or settings.contree_base_url).rstrip("/")
        self.image_name = image_name
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._api_client = api_client
        self._remote_image = None
        self._files_transferred = False

    def _validate_credentials(self) -> None:
        """Ensure sandbox credentials are present before attempting operations."""
        if not self.token:
            raise ConfigurationError(
                "Token Factory Sandbox requires authentication credentials. "
                "Please configure CONTREE_TOKEN or NEBIUS_API_KEY in your environment."
            )

    async def _get_api_client(self) -> Any:
        """Create configured ContreeAsyncClient from contree_client.httpx if not already provided."""
        if self._api_client:
            return self._api_client
        self._validate_credentials()
        if ContreeAsyncClient is not None:
            retry = RetryPolicy(max_attempts=3) if RetryPolicy is not None else None
            self._api_client = ContreeAsyncClient(
                token=self.token,
                base_url=self.base_url,
                timeout=float(self.timeout_seconds),
                retry=retry,
            )
        return self._api_client

    async def _get_client(self) -> Any:
        """Instantiate official Contree client wrapping the configured ContreeAsyncClient."""
        if self._client:
            return self._client
        if Contree is None:
            raise ConfigurationError(
                "contree-sdk is not installed. Run `pip install contree-sdk contree-client` to use Token Factory sandboxes."
            )
        self._validate_credentials()
        api_client = await self._get_api_client()
        try:
            # Documented interface: Contree(api_client)
            if api_client is not None:
                self._client = Contree(api_client)
            else:
                self._client = Contree(base_url=self.base_url, token=self.token)
        except (TypeError, AttributeError):
            # Compatibility fallback for SDK versions requiring Contree(base_url=..., token=...)
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
        from app.repositories.security import safe_read_file_bytes, safe_walk_repository

        self._validate_credentials()
        if not self._remote_image:
            await self.acquire_session()

        if not workspace_dir.is_dir():
            raise FileNotFoundError(f"Local workspace directory does not exist: {workspace_dir}")

        # Scan files with strict security traversal and bounded limits (fail-closed)
        files_to_transfer: Dict[str, bytes] = {}
        seen_destinations: Set[str] = set()
        walker = safe_walk_repository(
            workspace_dir=workspace_dir,
            max_files=settings.max_repository_files,
            max_file_size_bytes=settings.max_file_size_bytes,
            max_total_bytes=settings.max_repository_transfer_bytes,
            fail_on_limits=True,
            strict_transfer=True,
        )

        try:
            for entry in walker:
                rel_posix = entry.rel_path.replace("\\", "/")
                dest_path = PurePosixPath(f"/workspace/{rel_posix}")
                if not str(dest_path).startswith("/workspace/") or ".." in dest_path.parts:
                    raise SecurityViolationError(
                        f"Unsafe destination path '{dest_path}' escapes /workspace mount."
                    )
                dest_str = str(dest_path)
                if dest_str in seen_destinations:
                    raise SecurityViolationError(
                        f"Duplicate upload destination path detected: '{dest_str}'"
                    )
                seen_destinations.add(dest_str)

                try:
                    content = safe_read_file_bytes(
                        entry.path,
                        trusted_root=workspace_dir,
                        max_bytes=settings.max_file_size_bytes,
                    )
                    files_to_transfer[dest_str] = content
                except Exception as read_err:
                    logger.error(
                        "Failed to safely read repository file %s: %s", entry.rel_path, read_err
                    )
                    raise ProviderError(
                        "TokenFactorySandbox",
                        f"Failed to safely read repository file '{entry.rel_path}': {read_err}",
                        status_code=502,
                    )
        except SecurityViolationError as sec_err:
            logger.error("Security violation during workspace transfer: %s", sec_err)
            raise ProviderError(
                "TokenFactorySandbox",
                f"Repository transfer rejected by security policy: {sec_err}",
                status_code=502,
            )

        logger.info(
            "Transferring %d repository file(s) into remote ConTree sandbox (/workspace)...",
            len(files_to_transfer),
        )
        try:
            # Prepare files using official UploadFileSpec
            upload_specs = []
            if UploadFileSpec is not None:
                for remote_path, content in files_to_transfer.items():
                    upload_specs.append(
                        UploadFileSpec(path=PurePosixPath(remote_path), source=content)
                    )

            if upload_specs:
                # Official documented SDK mechanism: image.run(files=[...], disposable=False)
                self._remote_image = await self._remote_image.run(
                    shell="mkdir -p /workspace",
                    files=upload_specs,
                    disposable=False,
                    timeout=float(self.timeout_seconds),
                )
            elif hasattr(self._remote_image, "apply_files"):
                # Fallback for mock environments that mock apply_files
                self._remote_image = await self._remote_image.run(
                    shell="mkdir -p /workspace", disposable=False
                )
                if files_to_transfer:
                    self._remote_image = await self._remote_image.apply_files(files_to_transfer)
            else:
                self._remote_image = await self._remote_image.run(
                    shell="mkdir -p /workspace", disposable=False
                )

            # Determine isolated dependency installation inside the sandbox based on manifests
            dep_cmd = "pip install --no-cache-dir pytest"
            if (workspace_dir / "requirements.txt").is_file():
                dep_cmd += " -r /workspace/requirements.txt"
            elif (workspace_dir / "pyproject.toml").is_file():
                dep_cmd += " -e /workspace"
            elif (workspace_dir / "setup.py").is_file():
                dep_cmd += " -e /workspace"

            logger.info("Installing dependencies in ConTree sandbox: %s", dep_cmd)
            try:
                self._remote_image = await self._remote_image.run(
                    shell=dep_cmd,
                    cwd="/workspace",
                    disposable=False,
                    timeout=float(self.timeout_seconds),
                )
            except asyncio.TimeoutError:
                raise ProviderError(
                    "TokenFactorySandbox",
                    f"Remote sandbox dependency installation timed out after {self.timeout_seconds}s.",
                    status_code=504,
                )
            except Exception as run_err:
                if "timeout" in str(run_err).lower():
                    raise ProviderError(
                        "TokenFactorySandbox",
                        f"Remote sandbox dependency installation timed out: {run_err}",
                        status_code=504,
                    )
                raise ProviderError(
                    "TokenFactorySandbox",
                    f"Remote sandbox dependency installation failed: {run_err}",
                    status_code=502,
                )

            # Retrieve and strictly validate exit code
            try:
                raw_dep_exit_code = getattr(self._remote_image, "exit_code", None)
            except Exception as exc:
                raise ProviderError(
                    "TokenFactorySandbox",
                    f"Failed to retrieve dependency bootstrap exit code: {exc}",
                    status_code=502,
                )

            if raw_dep_exit_code is None:
                raise ProviderError(
                    "TokenFactorySandbox",
                    "Remote sandbox dependency installation completed without an exit code; cannot establish dependency bootstrap state.",
                    status_code=502,
                )

            try:
                dep_exit_code = int(raw_dep_exit_code)
            except (ValueError, TypeError):
                raise ProviderError(
                    "TokenFactorySandbox",
                    f"Remote sandbox dependency installation returned a malformed exit code: {raw_dep_exit_code!r}",
                    status_code=502,
                )

            if dep_exit_code != 0:
                dep_stderr = getattr(self._remote_image, "stderr", "") or ""
                dep_stdout = getattr(self._remote_image, "stdout", "") or ""
                err_msg = (dep_stderr or dep_stdout).strip()
                raise ProviderError(
                    "TokenFactorySandbox",
                    f"Remote sandbox dependency installation failed (exit code {dep_exit_code}): {err_msg}",
                    status_code=502,
                )

            self._files_transferred = True
        except ProviderError:
            raise
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

            # Retrieve exit_code from SDK result
            try:
                raw_exit_code = getattr(self._remote_image, "exit_code", None)
            except Exception as exc:
                logger.error("Failed to retrieve exit code from ConTree sandbox result: %s", exc)
                raise ProviderError(
                    "TokenFactorySandbox",
                    f"Failed to retrieve exit code from ConTree execution result: {exc}",
                    status_code=502,
                )

            # Missing exit code must NEVER be defaulted to 0 or treated as success
            if raw_exit_code is None:
                raise ProviderError(
                    "TokenFactorySandbox",
                    "ConTree execution completed without an exit code; cannot establish test outcome.",
                    status_code=502,
                )

            try:
                exit_code = int(raw_exit_code)
            except (ValueError, TypeError):
                raise ProviderError(
                    "TokenFactorySandbox",
                    f"ConTree execution returned a malformed exit code: {raw_exit_code!r}",
                    status_code=502,
                )

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
        except ProviderError:
            raise
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
        if self._remote_image and modified:
            from app.repositories.security import safe_read_file_bytes, validate_path_containment

            patch_specs = []
            seen_destinations = set()
            if UploadFileSpec is not None:
                for rel_file in modified:
                    local_file = workspace_dir / rel_file
                    safe_file = validate_path_containment(local_file, workspace_dir)
                    rel_posix = rel_file.replace("\\", "/")
                    dest_str = f"/workspace/{rel_posix}"
                    if dest_str in seen_destinations:
                        continue
                    seen_destinations.add(dest_str)
                    if safe_file.is_file():
                        content = safe_read_file_bytes(
                            safe_file,
                            trusted_root=workspace_dir,
                            max_bytes=settings.max_file_size_bytes,
                        )
                        patch_specs.append(
                            UploadFileSpec(
                                path=PurePosixPath(dest_str),
                                source=content,
                            )
                        )

            if patch_specs:
                self._remote_image = await self._remote_image.run(
                    shell="true",
                    files=patch_specs,
                    cwd="/workspace",
                    disposable=False,
                    timeout=float(self.timeout_seconds),
                )
            elif hasattr(self._remote_image, "apply_files"):
                # Fallback for mock environments
                remote_patch_files: Dict[str, bytes] = {}
                for rel_file in modified:
                    local_file = workspace_dir / rel_file
                    safe_file = validate_path_containment(local_file, workspace_dir)
                    if safe_file.is_file():
                        rel_posix = rel_file.replace("\\", "/")
                        dest_str = f"/workspace/{rel_posix}"
                        remote_patch_files[dest_str] = safe_read_file_bytes(
                            safe_file,
                            trusted_root=workspace_dir,
                            max_bytes=settings.max_file_size_bytes,
                        )
                if remote_patch_files:
                    self._remote_image = await self._remote_image.apply_files(remote_patch_files)

        return modified

    async def cleanup(self) -> None:
        """Dispose remote sandbox resources and close API clients."""
        logger.info("Disposing ConTree sandbox resources...")
        if self._api_client is not None:
            try:
                if hasattr(self._api_client, "close"):
                    await self._api_client.close()
                elif hasattr(self._api_client, "aclose"):
                    await self._api_client.aclose()
            except Exception as close_err:
                logger.debug("Error closing ContreeAsyncClient: %s", close_err)
            self._api_client = None

        self._remote_image = None
        self._client = None
        self._files_transferred = False
