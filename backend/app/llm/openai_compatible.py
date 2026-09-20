"""OpenAI-compatible LLM provider (works with Ollama, OpenAI, Together, etc.)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import get_settings
from app.llm.base import LLMError, LLMProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """
    Provider that speaks the OpenAI Chat Completions API.
    Compatible with: Ollama (/v1), OpenAI, Together AI, Groq, LiteLLM, etc.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.timeout = timeout or settings.llm_timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException as e:
            raise LLMError("LLM_TIMEOUT", f"LLM request timed out after {self.timeout}s") from e
        except httpx.HTTPStatusError as e:
            raise LLMError("LLM_HTTP_ERROR", f"LLM returned HTTP {e.response.status_code}") from e
        except Exception as e:
            raise LLMError("LLM_ERROR", f"LLM request failed: {e}") from e

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> str:
        """Request JSON output. Tries response_format=json_object first, falls back."""
        try:
            return await self.complete(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except LLMError:
            # Fallback: no response_format (some providers don't support it)
            return await self.complete(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )



def get_llm_provider():
    """
    Factory — returns the configured LLM provider.

    Routing rules (LLM_PROVIDER env var):
      groq            → GroqProvider (groq SDK, api.groq.com)
      openai          → OpenAICompatibleProvider (OpenAI API)
      ollama          → OpenAICompatibleProvider (local Ollama /v1)
      <anything else> → OpenAICompatibleProvider (generic OpenAI-compatible)
    """
    from app.config import get_settings
    settings = get_settings()
    provider = (settings.llm_provider or "openai").lower().strip()

    if provider == "groq":
        from app.llm.groq_provider import GroqProvider
        return GroqProvider()

    return OpenAICompatibleProvider()
