"""Tavily Search provider adapter for technical documentation and bug research."""

from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import logger
from app.providers.base import BaseSearchProvider, SearchResponse, SearchResultItem

settings = get_settings()

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilySearchProvider(BaseSearchProvider):
    """Adapter for Tavily search API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        enabled: Optional[bool] = None,
        timeout_seconds: float = 15.0,
    ):
        self.api_key = (api_key or settings.tavily_api_key).strip()
        self.enabled = enabled if enabled is not None else settings.is_tavily_configured
        self.timeout_seconds = timeout_seconds

    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> SearchResponse:
        """Execute web search to gather relevant documentation and issue context."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return SearchResponse(enabled=self.enabled, query="", results=[])

        if not self.enabled or not self.api_key:
            logger.info("Tavily search skipped: provider is not enabled or API key is absent.")
            return SearchResponse(
                enabled=False,
                query=cleaned_query,
                results=[],
                error="Tavily search is disabled or missing credentials.",
            )

        payload: Dict[str, Any] = {
            "api_key": self.api_key,
            "query": cleaned_query,
            "search_depth": "basic",
            "max_results": max(1, min(max_results, 5)),
            "include_answer": False,
        }

        logger.info("Executing Tavily research search for query: '%s'", cleaned_query)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.post(TAVILY_SEARCH_URL, json=payload)

            if res.status_code == 200:
                data = res.json()
                raw_results = data.get("results", [])
                items: List[SearchResultItem] = []
                for item in raw_results:
                    items.append(
                        SearchResultItem(
                            title=item.get("title", "Resource"),
                            url=item.get("url", "#"),
                            content=item.get("content", "").strip(),
                            score=item.get("score"),
                        )
                    )
                logger.info("Tavily returned %d search results.", len(items))
                return SearchResponse(
                    enabled=True,
                    query=cleaned_query,
                    results=items,
                )
            else:
                logger.warning(
                    "Tavily API responded with HTTP %d: %s",
                    res.status_code,
                    res.text[:120],
                )
                return SearchResponse(
                    enabled=True,
                    query=cleaned_query,
                    results=[],
                    error=f"Tavily returned HTTP {res.status_code}",
                )

        except httpx.TimeoutException:
            logger.warning("Tavily search request timed out after %.1fs", self.timeout_seconds)
            return SearchResponse(
                enabled=True,
                query=cleaned_query,
                results=[],
                error=f"Tavily search timed out after {self.timeout_seconds}s.",
            )
        except Exception as exc:
            logger.error("Error executing Tavily search: %s", exc)
            return SearchResponse(
                enabled=True,
                query=cleaned_query,
                results=[],
                error=f"Tavily search failed: {str(exc)}",
            )
