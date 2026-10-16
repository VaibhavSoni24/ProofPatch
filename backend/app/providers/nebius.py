"""Nebius Token Factory OpenAI-compatible inference provider adapter."""

from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.errors import ConfigurationError, ProviderError
from app.core.logging import logger
from app.providers.base import BaseLLMProvider, ProviderResponse

settings = get_settings()


class NebiusTokenFactoryProvider(BaseLLMProvider):
    """Adapter for Nebius Token Factory inference using OpenAI-compatible endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.api_key = (api_key or settings.nebius_api_key).strip()
        self.base_url = (base_url or settings.nebius_base_url).rstrip("/")
        self.model = (model or settings.nebius_model).strip()
        self.timeout_seconds = timeout_seconds or settings.model_timeout_seconds

    def _validate_configuration(self) -> None:
        """Ensure provider has required credentials and model identifier."""
        if not self.api_key:
            raise ConfigurationError(
                "Nebius API key is not configured. Please set NEBIUS_API_KEY in .env."
            )
        if not self.model:
            raise ConfigurationError(
                "Nebius model is not configured. Please specify an eligible NVIDIA model in NEBIUS_MODEL."
            )
        if not self.model.startswith("nvidia/"):
            raise ConfigurationError(
                f"Configured model '{self.model}' is not an eligible NVIDIA model. "
                "ProofPatch requires an eligible open-source NVIDIA model (starting with 'nvidia/') "
                "from the Nebius Token Factory catalog."
            )

    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None,
    ) -> ProviderResponse:
        """Call Nebius Token Factory chat completions API."""
        self._validate_configuration()

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        logger.info(
            "Calling Nebius Token Factory model '%s' (messages: %d, timeout: %ds)",
            self.model,
            len(messages),
            self.timeout_seconds,
        )

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                res = await client.post(endpoint, headers=headers, json=payload)

            if res.status_code == 200:
                data = res.json()
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                usage = data.get("usage", {})

                return ProviderResponse(
                    content=content,
                    model=data.get("model", self.model),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    raw_response=data,
                )

            elif res.status_code == 401:
                raise ProviderError(
                    "Nebius",
                    "Authentication failed: invalid NEBIUS_API_KEY. Please verify your token.",
                    status_code=401,
                )
            elif res.status_code == 402:
                raise ProviderError(
                    "Nebius",
                    "Insufficient credits on Nebius Token Factory account.",
                    status_code=402,
                )
            elif res.status_code == 404:
                raise ProviderError(
                    "Nebius",
                    f"Configured model '{self.model}' was not found in the Nebius Token Factory catalog.",
                    status_code=404,
                )
            elif res.status_code == 429:
                raise ProviderError(
                    "Nebius",
                    "Nebius Token Factory rate limit exceeded. Please back off and try again.",
                    status_code=429,
                )
            else:
                error_body = res.text[:200]
                raise ProviderError(
                    "Nebius",
                    f"API request failed with HTTP {res.status_code}: {error_body}",
                    status_code=res.status_code,
                )

        except httpx.TimeoutException:
            logger.warning("Nebius API request timed out after %ds", self.timeout_seconds)
            raise ProviderError(
                "Nebius",
                f"Inference request timed out after {self.timeout_seconds} seconds.",
                status_code=504,
            )
        except httpx.RequestError as exc:
            logger.error("Network error communicating with Nebius Token Factory: %s", exc)
            raise ProviderError(
                "Nebius",
                f"Network communication failure: {str(exc)}",
                status_code=502,
            )
