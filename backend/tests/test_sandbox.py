"""Unit tests for execution backend interface and sandboxes."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.errors import (
    ConfigurationError,
    DockerNotAvailableError,
    ProviderError,
    SecurityError,
)
from app.sandbox.docker_backend import DockerExecutionBackend
from app.sandbox.factory import get_execution_backend
from app.sandbox.local_runner import LocalExecutionBackend
from app.sandbox.token_factory import TokenFactorySandboxBackend


@pytest.mark.asyncio
async def test_demo_mode_resolves_local_backend(tmp_path):
    """Test demo mode resolves to LocalExecutionBackend."""
    backend = get_execution_backend(mode="demo")
    assert isinstance(backend, LocalExecutionBackend)
    assert backend.backend_name == "demo"


def test_live_mode_rejects_local_backend():
    """Test live mode strictly rejects local subprocess execution."""
    with pytest.raises(SecurityError, match="strictly prohibited"):
        get_execution_backend(mode="live", backend_override="local")


def test_live_mode_defaults_to_docker():
    """Test live mode defaults to Docker backend."""
    backend = get_execution_backend(mode="live", backend_override="docker")
    assert isinstance(backend, DockerExecutionBackend)
    assert backend.backend_name == "docker"


def test_live_mode_resolves_token_factory_sandbox():
    """Test live mode resolves to TokenFactorySandboxBackend when requested."""
    backend = get_execution_backend(mode="live", backend_override="token_factory_sandbox")
    assert isinstance(backend, TokenFactorySandboxBackend)
    assert backend.backend_name == "token_factory_sandbox"


@pytest.mark.asyncio
async def test_docker_backend_fails_closed_when_daemon_unavailable(tmp_path):
    """Verify Docker backend fails closed with actionable error if daemon is not available."""
    backend = DockerExecutionBackend()
    with patch("app.sandbox.docker_backend.is_docker_available", return_value=False):
        with pytest.raises(DockerNotAvailableError, match="Docker daemon is not running"):
            await backend.execute_tests(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_requires_credentials(tmp_path):
    """Verify TokenFactorySandboxBackend raises ConfigurationError if credentials are missing."""
    backend = TokenFactorySandboxBackend(token="")
    with pytest.raises(ConfigurationError, match="requires authentication credentials"):
        await backend.execute_tests(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_lifecycle_mocked(tmp_path):
    """Verify complete Token Factory sandbox lifecycle (session acquisition, transfer, exec, patch, cleanup) with mocked ConTree SDK."""
    # Create sample repository files in tmp_path
    sample_file = tmp_path / "src" / "sample.py"
    sample_file.parent.mkdir(parents=True, exist_ok=True)
    sample_file.write_text("print('initial')", encoding="utf-8")

    mock_image = AsyncMock()
    mock_image.exit_code = 0
    mock_image.stdout = "5 passed in 0.10s"
    mock_image.stderr = ""
    mock_image.run.return_value = mock_image

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    mock_api_client = AsyncMock()
    mock_api_client.close = AsyncMock()

    backend = TokenFactorySandboxBackend(
        token="test-token",
        base_url="https://api.tokenfactory.nebius.com/sandboxes",
        client=mock_client,
        api_client=mock_api_client,
    )

    # 1. Execute tests (triggers session acquisition, transfer_workspace, then execute_tests)
    res = await backend.execute_tests(tmp_path)
    assert res.exit_code == 0
    assert "5 passed" in res.output
    assert res.timed_out is False
    assert backend._remote_image is not None
    assert backend._files_transferred is True

    # Verify images.use was called with base image
    mock_client.images.use.assert_called_once_with("python:3.11-slim", strict=True)
    # Verify image.run was called for transfer and execution
    assert mock_image.run.call_count >= 2

    # 2. Test apply_patch
    patch_diff = """--- a/src/sample.py
+++ b/src/sample.py
@@ -1 +1 @@
-print('initial')
+print('patched')
"""
    modified = await backend.apply_patch(patch_diff, tmp_path)
    assert "src/sample.py" in modified
    assert sample_file.read_text(encoding="utf-8") == "print('patched')\n"

    # 3. Cleanup session - closes client and resets state
    await backend.cleanup()
    mock_api_client.close.assert_called_once()
    assert backend._remote_image is None
    assert backend._client is None
    assert backend._api_client is None
    assert backend._files_transferred is False


@pytest.mark.asyncio
async def test_token_factory_sandbox_valid_zero_exit_code(tmp_path):
    """Verify Token Factory sandbox correctly records valid zero exit code."""
    mock_image = AsyncMock()
    mock_image.exit_code = 0
    mock_image.stdout = "3 passed in 0.05s"
    mock_image.stderr = ""
    mock_image.run.return_value = mock_image

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    backend._remote_image = mock_image
    backend._files_transferred = True

    res = await backend.execute_tests(tmp_path)
    assert res.exit_code == 0
    assert "3 passed" in res.output
    assert res.timed_out is False


@pytest.mark.asyncio
async def test_token_factory_sandbox_genuine_nonzero_exit_code(tmp_path):
    """Verify Token Factory sandbox preserves real nonzero test failure exit code."""
    mock_image = AsyncMock()
    mock_image.exit_code = 1
    mock_image.stdout = (
        "FAILED tests/test_calc.py::test_boundary - AssertionError: 6 != 8\n1 failed in 0.02s"
    )
    mock_image.stderr = ""
    mock_image.run.return_value = mock_image

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    backend._remote_image = mock_image
    backend._files_transferred = True

    res = await backend.execute_tests(tmp_path)
    assert res.exit_code == 1
    assert "AssertionError: 6 != 8" in res.output
    assert res.timed_out is False


@pytest.mark.asyncio
async def test_token_factory_sandbox_missing_exit_code_rejected(tmp_path):
    """Verify Token Factory sandbox rejects missing exit code and never defaults to 0."""
    mock_image = AsyncMock()
    mock_image.exit_code = None
    mock_image.stdout = "some output"
    mock_image.stderr = ""
    mock_image.run.return_value = mock_image

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    backend._remote_image = mock_image
    backend._files_transferred = True

    with pytest.raises(ProviderError, match="without an exit code"):
        await backend.execute_tests(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_invalid_exit_code_rejected(tmp_path):
    """Verify Token Factory sandbox rejects malformed exit code."""
    mock_image = AsyncMock()
    mock_image.exit_code = "INVALID_CODE"
    mock_image.stdout = "some output"
    mock_image.stderr = ""
    mock_image.run.return_value = mock_image

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    backend._remote_image = mock_image
    backend._files_transferred = True

    with pytest.raises(ProviderError, match="malformed exit code"):
        await backend.execute_tests(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_timeout_handling(tmp_path):
    """Verify Token Factory sandbox flags timed out commands correctly."""
    mock_image = AsyncMock()
    mock_image.exit_code = 124
    mock_image.stdout = ""
    mock_image.stderr = "Command timed out"
    mock_image.run.return_value = mock_image

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    backend._remote_image = mock_image
    backend._files_transferred = True

    res = await backend.execute_tests(tmp_path)
    assert res.exit_code == 124
    assert res.timed_out is True


@pytest.mark.asyncio
async def test_token_factory_sandbox_asyncio_timeout(tmp_path):
    """Verify Token Factory sandbox handles asyncio TimeoutError cleanly."""
    mock_image = AsyncMock()
    mock_image.run.side_effect = asyncio.TimeoutError()

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    backend._remote_image = mock_image
    backend._files_transferred = True

    res = await backend.execute_tests(tmp_path, timeout_seconds=10)
    assert res.exit_code == 124
    assert res.timed_out is True
    assert "timed out after 10s" in res.output


@pytest.mark.asyncio
async def test_token_factory_sandbox_missing_stdout_or_stderr(tmp_path):
    """Verify Token Factory sandbox handles None stdout or stderr without error."""
    mock_image = AsyncMock()
    mock_image.exit_code = 0
    mock_image.stdout = None
    mock_image.stderr = None
    mock_image.run.return_value = mock_image

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    backend._remote_image = mock_image
    backend._files_transferred = True

    res = await backend.execute_tests(tmp_path)
    assert res.exit_code == 0
    assert res.stdout == ""
    assert res.stderr == ""


@pytest.mark.asyncio
async def test_token_factory_sandbox_execution_error(tmp_path):
    """Verify Token Factory sandbox raises ProviderError on remote execution exception."""
    mock_image = AsyncMock()
    mock_image.run.side_effect = RuntimeError("ConTree container lost connection")

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    backend._remote_image = mock_image
    backend._files_transferred = True

    with pytest.raises(ProviderError, match="ConTree execution failed"):
        await backend.execute_tests(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_transfer_error(tmp_path):
    """Verify Token Factory sandbox raises ProviderError on workspace transfer exception."""
    mock_image = AsyncMock()
    mock_image.run.side_effect = RuntimeError("Disk quota exceeded")

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    with pytest.raises(ProviderError, match="Failed to transfer workspace"):
        await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_dependency_bootstrap_failure(tmp_path):
    """Verify Token Factory sandbox raises ProviderError when container dependency setup fails."""
    mock_image = AsyncMock()
    # First run succeeds (mkdir), second run (pip install) fails with exit code 1
    call_count = 0

    async def mock_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        img = AsyncMock()
        img.run = mock_run
        if call_count >= 2:
            img.exit_code = 1
            img.stderr = "ERROR: Could not find a version that satisfies the requirement"
            img.stdout = ""
        else:
            img.exit_code = 0
            img.stderr = ""
            img.stdout = ""
        return img

    mock_image.run = mock_run

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    with pytest.raises(ProviderError, match="dependency installation failed"):
        await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_api_client_lifecycle_and_cleanup():
    """Verify ContreeAsyncClient instantiation and clean resource disposal during cleanup."""
    backend = TokenFactorySandboxBackend(
        token="test-token",
        base_url="https://api.tokenfactory.nebius.com/sandboxes",
    )
    api_client = await backend._get_api_client()
    assert api_client is not None
    assert hasattr(api_client, "close")

    # Cleanup releases client and awaits close
    with patch.object(api_client, "close", new_callable=AsyncMock) as mock_close:
        await backend.cleanup()
        mock_close.assert_called_once()
    assert backend._api_client is None


def test_token_factory_sandbox_no_silent_host_fallback():
    """Verify that when token_factory_sandbox is configured, it never resolves to host LocalExecutionBackend."""
    backend = get_execution_backend(mode="live", backend_override="token_factory_sandbox")
    assert not isinstance(backend, LocalExecutionBackend)
    assert backend.backend_name == "token_factory_sandbox"


@pytest.mark.asyncio
async def test_token_factory_sandbox_per_file_size_limit_exceeded(tmp_path, monkeypatch):
    """Verify transfer_workspace fails closed when a file exceeds the per-file size limit."""
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "max_file_size_bytes", 50)

    oversized = tmp_path / "big_data.py"
    oversized.write_text("x" * 200, encoding="utf-8")

    mock_image = AsyncMock()
    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    with pytest.raises(ProviderError, match="exceeds maximum allowed per-file limit"):
        await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_cumulative_size_limit_exceeded(tmp_path, monkeypatch):
    """Verify transfer_workspace fails closed when cumulative transfer bytes exceed limit."""
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "max_repository_transfer_bytes", 150)

    (tmp_path / "f1.py").write_text("a" * 80, encoding="utf-8")
    (tmp_path / "f2.py").write_text("b" * 90, encoding="utf-8")

    mock_image = AsyncMock()
    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    with pytest.raises(ProviderError, match="exceeds cumulative limit"):
        await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_file_count_limit_exceeded(tmp_path, monkeypatch):
    """Verify transfer_workspace fails closed when file count cap is exceeded."""
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "max_repository_files", 2)

    (tmp_path / "f1.py").write_text("print(1)", encoding="utf-8")
    (tmp_path / "f2.py").write_text("print(2)", encoding="utf-8")
    (tmp_path / "f3.py").write_text("print(3)", encoding="utf-8")

    mock_image = AsyncMock()
    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    with pytest.raises(ProviderError, match="exceeds maximum allowed file limit"):
        await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_bootstrap_missing_exit_code(tmp_path):
    """Verify dependency bootstrap fails closed if exit code is missing (None)."""
    mock_image = AsyncMock()
    call_count = 0

    async def mock_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        img = AsyncMock()
        img.run = mock_run
        img.exit_code = 0 if call_count == 1 else None
        return img

    mock_image.run = mock_run
    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    with pytest.raises(ProviderError, match="without an exit code"):
        await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_bootstrap_malformed_exit_code(tmp_path):
    """Verify dependency bootstrap fails closed if exit code is not a valid integer."""
    mock_image = AsyncMock()
    call_count = 0

    async def mock_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        img = AsyncMock()
        img.run = mock_run
        img.exit_code = 0 if call_count == 1 else "NOT_AN_INT"
        return img

    mock_image.run = mock_run
    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    with pytest.raises(ProviderError, match="malformed exit code"):
        await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_bootstrap_timeout(tmp_path):
    """Verify dependency bootstrap handles remote command timeout."""
    mock_image = AsyncMock()
    call_count = 0

    async def mock_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.TimeoutError()
        img = AsyncMock()
        img.run = mock_run
        img.exit_code = 0
        return img

    mock_image.run = mock_run
    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    with pytest.raises(ProviderError, match="timed out"):
        await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_bootstrap_remote_failure(tmp_path):
    """Verify dependency bootstrap handles unexpected remote container exception."""
    mock_image = AsyncMock()
    call_count = 0

    async def mock_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise RuntimeError("ConTree host network terminated")
        img = AsyncMock()
        img.run = mock_run
        img.exit_code = 0
        return img

    mock_image.run = mock_run
    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    with pytest.raises(ProviderError, match="dependency installation failed"):
        await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_strict_transfer_rejects_symlink(tmp_path):
    """Verify transfer_workspace aborts on symlinks in strict transfer mode."""
    (tmp_path / "real.py").write_text("x = 1\n", encoding="utf-8")
    link = tmp_path / "link.py"

    from tests.test_repository_security import CAN_SYMLINK

    if CAN_SYMLINK:
        link.symlink_to(tmp_path / "real.py")
    else:
        # Patch is_symlink to simulate symlink existence
        pass

    mock_image = AsyncMock()
    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    if CAN_SYMLINK:
        with pytest.raises(ProviderError, match="Repository transfer rejected by security policy"):
            await backend.transfer_workspace(tmp_path)
    else:
        from pathlib import Path

        with patch.object(Path, "is_symlink", return_value=True):
            with pytest.raises(
                ProviderError, match="Repository transfer rejected by security policy"
            ):
                await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_strict_transfer_rejects_unreadable_file(tmp_path):
    """Verify transfer_workspace aborts on unreadable files in strict transfer mode."""
    from pathlib import Path

    (tmp_path / "broken.py").write_text("y = 2\n", encoding="utf-8")

    mock_image = AsyncMock()
    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)

    original_stat = Path.stat

    def mock_stat_err(self, *args, **kwargs):
        if self.name == "broken.py":
            raise PermissionError("EACCES")
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", side_effect=mock_stat_err, autospec=True):
        with pytest.raises(ProviderError, match="Repository transfer rejected by security policy"):
            await backend.transfer_workspace(tmp_path)


@pytest.mark.asyncio
async def test_token_factory_sandbox_strict_transfer_succeeds_for_regular_files(tmp_path):
    """Verify transfer_workspace transfers regular files into ConTree sandbox."""
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")

    mock_image = AsyncMock()
    mock_image.exit_code = 0
    mock_image.run = AsyncMock(return_value=mock_image)

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    await backend.transfer_workspace(tmp_path)

    assert mock_image.run.await_count >= 2
    assert backend._files_transferred is True
