"""Unit tests for execution backend interface and sandboxes."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.errors import ConfigurationError, DockerNotAvailableError, SecurityError
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
    mock_image.apply_files.return_value = mock_image

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(
        token="test-token",
        base_url="https://api.tokenfactory.nebius.com/sandboxes",
        client=mock_client,
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
    # Verify apply_files was called to transfer repository
    mock_image.apply_files.assert_called()

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

    # 3. Cleanup session
    await backend.cleanup()
    assert backend._remote_image is None
    assert backend._client is None
    assert backend._files_transferred is False


@pytest.mark.asyncio
async def test_token_factory_sandbox_timeout_handling(tmp_path):
    """Verify Token Factory sandbox flags timed out commands correctly."""
    mock_image = AsyncMock()
    mock_image.exit_code = 124
    mock_image.stdout = ""
    mock_image.stderr = "Command timed out"
    mock_image.run.return_value = mock_image
    mock_image.apply_files.return_value = mock_image

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    res = await backend.execute_tests(tmp_path)
    assert res.exit_code == 124
    assert res.timed_out is True


@pytest.mark.asyncio
async def test_token_factory_sandbox_execution_error(tmp_path):
    """Verify Token Factory sandbox raises ProviderError on remote execution exception."""
    from app.core.errors import ProviderError

    mock_image = AsyncMock()
    mock_image.run.side_effect = RuntimeError("ConTree container lost connection")
    mock_image.apply_files.return_value = mock_image

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
    from app.core.errors import ProviderError

    mock_image = AsyncMock()
    mock_image.run.side_effect = RuntimeError("Disk quota exceeded")

    mock_client = AsyncMock()
    mock_client.images.use.return_value = mock_image

    backend = TokenFactorySandboxBackend(token="test-token", client=mock_client)
    with pytest.raises(ProviderError, match="Failed to transfer workspace"):
        await backend.transfer_workspace(tmp_path)


def test_token_factory_sandbox_no_silent_host_fallback():
    """Verify that when token_factory_sandbox is configured, it never resolves to host LocalExecutionBackend."""
    backend = get_execution_backend(mode="live", backend_override="token_factory_sandbox")
    assert not isinstance(backend, LocalExecutionBackend)
    assert backend.backend_name == "token_factory_sandbox"
