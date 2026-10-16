"""Unit tests for execution backend interface and sandboxes."""

from unittest.mock import AsyncMock, MagicMock, patch

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
    """Verify complete Token Factory sandbox lifecycle (session acquisition, execution, cleanup) with mocked HTTP."""
    backend = TokenFactorySandboxBackend(
        token="test-token", base_url="https://api.tokenfactory.nebius.com/sandboxes"
    )

    mock_client = AsyncMock()

    # Session create response
    mock_post_session = MagicMock(status_code=201)
    mock_post_session.json.return_value = {"session_id": "session_test_123"}

    # Exec command response
    mock_post_exec = MagicMock(status_code=200)
    mock_post_exec.json.return_value = {
        "exit_code": 0,
        "stdout": "5 passed in 0.10s",
        "stderr": "",
    }

    # Delete cleanup response
    mock_delete = MagicMock(status_code=204)

    async def mock_post(url, *args, **kwargs):
        if "exec" in url:
            return mock_post_exec
        return mock_post_session

    mock_client.post.side_effect = mock_post
    mock_client.delete.return_value = mock_delete
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        # 1. Execute tests (triggers session acquire then exec)
        res = await backend.execute_tests(tmp_path)
        assert res.exit_code == 0
        assert "5 passed" in res.output
        assert backend.session_id == "session_test_123"

        # 2. Cleanup session
        await backend.cleanup()
        assert backend.session_id is None
        mock_client.delete.assert_called_once()
