"""Abstract interfaces and common data structures for AI and search providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ProviderResponse(BaseModel):
    """Normalized output from an LLM inference call."""

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_response: Optional[Dict[str, Any]] = None


class SearchResultItem(BaseModel):
    """Normalized search result from an external research provider."""

    title: str
    url: str
    content: str
    score: Optional[float] = None


class SearchResponse(BaseModel):
    """Normalized search response container."""

    enabled: bool
    query: str
    results: List[SearchResultItem] = []
    error: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM inference providers."""

    @abstractmethod
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None,
    ) -> ProviderResponse:
        """Execute chat completion request."""
        pass


class BaseSearchProvider(ABC):
    """Abstract base class for search/research providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> SearchResponse:
        """Execute external research query."""
        pass
