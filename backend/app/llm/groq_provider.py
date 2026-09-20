"""Groq LLM provider — uses the official Groq Python SDK (async client)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from groq import AsyncGroq

from app.config import get_settings
from app.llm.base import LLMError, LLMProvider

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """
    LLM provider backed by the Groq Python SDK.
    Compatible with any model on api.groq.com, including openai/gpt-oss-20b.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.timeout = timeout or settings.llm_timeout_seconds
        self._client = AsyncGroq(api_key=self.api_key, timeout=self.timeout)

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        try:
            kwargs: dict[str, Any] = dict(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if response_format:
                kwargs["response_format"] = response_format

            resp = await self._client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""

        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                raise LLMError("LLM_TIMEOUT", f"Groq request timed out after {self.timeout}s") from e
            if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                raise LLMError("LLM_AUTH_ERROR", "Groq API key is invalid or missing.") from e
            raise LLMError("LLM_ERROR", f"Groq request failed: {error_msg}") from e

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> str:
        """
        Request JSON output.
        Groq supports response_format={"type": "json_object"} for most models.
        Falls back to plain completion if JSON mode is not supported.
        """
        try:
            return await self.complete(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except LLMError as e:
            if "json" in e.message.lower() or "response_format" in e.message.lower():
                # Model doesn't support JSON mode — fall back
                logger.warning("Groq JSON mode not supported for %s, falling back.", self.model)
                return await self.complete(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            raise
