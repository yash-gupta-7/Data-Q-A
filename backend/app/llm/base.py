"""LLM provider abstraction — base class and shared error types."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from an LLM provider."""

    content: str
    """The raw text / JSON content returned by the model."""

    model: str
    """The model identifier used for this completion."""

    prompt_tokens: int = 0
    """Number of tokens in the prompt (if reported by provider)."""

    completion_tokens: int = 0
    """Number of tokens in the completion (if reported by provider)."""

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMProvider(ABC):
    """Abstract LLM provider. All providers must implement this interface."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Send messages and return a structured LLMResponse."""
        ...

    @abstractmethod
    async def complete_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Request JSON-mode completion, return LLMResponse with JSON content."""
        ...

    async def complete_with_retry(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2048,
        max_retries: int = 3,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Complete with automatic retry on transient LLM errors.

        Args:
            messages: Conversation messages to send.
            temperature: Sampling temperature.
            max_tokens: Max tokens for the completion.
            max_retries: Number of retry attempts on transient errors.
            response_format: Optional format hint (e.g., JSON mode).

        Returns:
            LLMResponse from the first successful attempt.

        Raises:
            LLMError: If all retries are exhausted.
        """
        import asyncio

        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                response = await self.complete(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
                if attempt > 1:
                    logger.info("LLM succeeded on attempt %d/%d", attempt, max_retries)
                return response
            except LLMRateLimitError as e:
                last_error = e
                wait = 2**attempt  # exponential backoff: 2, 4, 8 seconds
                logger.warning(
                    "LLM rate limit hit (attempt %d/%d), retrying in %ds: %s",
                    attempt,
                    max_retries,
                    wait,
                    e,
                )
                await asyncio.sleep(wait)
            except LLMTransientError as e:
                last_error = e
                logger.warning("Transient LLM error (attempt %d/%d): %s", attempt, max_retries, e)
                await asyncio.sleep(1)

        raise LLMError(
            code="max_retries_exceeded",
            message=f"LLM failed after {max_retries} attempts: {last_error}",
        )


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Base class for all LLM-related errors."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

    def __repr__(self) -> str:
        return f"LLMError(code={self.code!r}, message={self.message!r})"


class LLMRateLimitError(LLMError):
    """Raised when the LLM provider returns a rate-limit response (429)."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(code="rate_limit", message=message)


class LLMTransientError(LLMError):
    """Raised on transient provider errors (5xx, timeouts)."""

    def __init__(self, message: str):
        super().__init__(code="transient_error", message=message)


class LLMContextLengthError(LLMError):
    """Raised when the prompt exceeds the model's context window."""

    def __init__(self, message: str = "Context length exceeded"):
        super().__init__(code="context_length_exceeded", message=message)
