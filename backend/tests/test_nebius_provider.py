"""Unit tests for Nebius Token Factory adapter using mocked HTTP responses."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.errors import ConfigurationError, ProviderError
from app.providers.nebius import NebiusTokenFactoryProvider


@pytest.mark.asyncio
async def test_nebius_missing_api_key_raises_error():
    """Verify provider raises ConfigurationError if NEBIUS_API_KEY is missing."""
    provider = NebiusTokenFactoryProvider(api_key="", model="nvidia/nemotron-4-340b-instruct")
    with pytest.raises(ConfigurationError) as exc:
        await provider.generate_completion(messages=[{"role": "user", "content": "hi"}])
    assert "API key is not configured" in str(exc.value)


@pytest.mark.asyncio
async def test_nebius_missing_model_raises_error():
    """Verify provider raises ConfigurationError if model identifier is missing."""
    provider = NebiusTokenFactoryProvider(api_key="valid-key", model="")
    with pytest.raises(ConfigurationError) as exc:
        await provider.generate_completion(messages=[{"role": "user", "content": "hi"}])
    assert "model is not configured" in str(exc.value)


@pytest.mark.asyncio
async def test_nebius_non_nvidia_model_raises_error():
    """Verify provider raises ConfigurationError if model identifier is not an eligible NVIDIA model."""
    provider = NebiusTokenFactoryProvider(api_key="valid-key", model="openai/gpt-4")
    with pytest.raises(ConfigurationError) as exc:
        await provider.generate_completion(messages=[{"role": "user", "content": "hi"}])
    assert "not an eligible NVIDIA model" in str(exc.value)


@pytest.mark.asyncio
async def test_nebius_successful_completion_mocked():
    """Test successful completion using mocked OpenAI-compatible HTTP response."""
    mock_payload = {
        "id": "chatcmpl-123",
        "model": "nvidia/nemotron-4-340b-instruct",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Minimal patch generated successfully",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 20},
    }

    mock_response = httpx.Response(
        status_code=200,
        json=mock_payload,
        request=httpx.Request("POST", "https://api.tokenfactory.nebius.com/v1/chat/completions"),
    )

    provider = NebiusTokenFactoryProvider(
        api_key="mock-key", model="nvidia/nemotron-4-340b-instruct"
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        res = await provider.generate_completion(messages=[{"role": "user", "content": "hello"}])

        assert res.content == "Minimal patch generated successfully"
        assert res.model == "nvidia/nemotron-4-340b-instruct"
        assert res.prompt_tokens == 50
        assert res.completion_tokens == 20
        assert mock_post.called


@pytest.mark.asyncio
async def test_nebius_401_auth_error_handling():
    """Verify 401 returns actionable ProviderError."""
    mock_response = httpx.Response(
        status_code=401,
        text="Unauthorized",
        request=httpx.Request("POST", "https://api.tokenfactory.nebius.com/v1/chat/completions"),
    )
    provider = NebiusTokenFactoryProvider(
        api_key="bad-key", model="nvidia/nemotron-4-340b-instruct"
    )
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        with pytest.raises(ProviderError) as exc:
            await provider.generate_completion(messages=[{"role": "user", "content": "hi"}])
        assert exc.value.status_code == 401
        assert "Authentication failed" in exc.value.message


@pytest.mark.asyncio
async def test_nebius_timeout_handling():
    """Verify request timeout raises 504 ProviderError."""
    provider = NebiusTokenFactoryProvider(
        api_key="key", model="nvidia/nemotron-4-340b-instruct", timeout_seconds=1
    )
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Read timed out")
        with pytest.raises(ProviderError) as exc:
            await provider.generate_completion(messages=[{"role": "user", "content": "hi"}])
        assert exc.value.status_code == 504
        assert "timed out" in exc.value.message
