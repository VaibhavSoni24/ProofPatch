"""Unit tests for Tavily search provider adapter using mocked HTTP responses."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.providers.tavily import TavilySearchProvider


@pytest.mark.asyncio
async def test_tavily_disabled_when_credentials_absent():
    """Verify Tavily gracefully reports disabled if api_key is missing."""
    provider = TavilySearchProvider(api_key="", enabled=False)
    res = await provider.search("python pytest documentation")
    assert res.enabled is False
    assert res.results == []
    assert "disabled" in res.error.lower()


@pytest.mark.asyncio
async def test_tavily_successful_search_mocked():
    """Test successful Tavily search using mocked response."""
    mock_payload = {
        "query": "fastapi cors middleware",
        "results": [
            {
                "title": "FastAPI CORS Guide",
                "url": "https://fastapi.tiangolo.com/tutorial/cors/",
                "content": "Use CORSMiddleware to allow cross-origin requests.",
                "score": 0.98,
            }
        ],
    }

    mock_response = httpx.Response(
        status_code=200,
        json=mock_payload,
        request=httpx.Request("POST", "https://api.tavily.com/search"),
    )

    provider = TavilySearchProvider(api_key="mock-tvly-key", enabled=True)

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        res = await provider.search("fastapi cors middleware")

        assert res.enabled is True
        assert len(res.results) == 1
        assert res.results[0].title == "FastAPI CORS Guide"
        assert res.results[0].url == "https://fastapi.tiangolo.com/tutorial/cors/"
        assert res.results[0].score == 0.98
        assert mock_post.called


@pytest.mark.asyncio
async def test_tavily_network_error_graceful_fallback():
    """Verify network error returns clean SearchResponse with error field."""
    provider = TavilySearchProvider(api_key="mock-key", enabled=True)

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        res = await provider.search("any query")

        assert res.enabled is True
        assert res.results == []
        assert "failed" in res.error.lower()
