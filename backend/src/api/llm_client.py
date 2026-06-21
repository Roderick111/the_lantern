"""Unified LLM client using LiteLLM for multi-provider support.

Provides async interface for multiple LLM providers (Anthropic, OpenRouter,
OpenAI, Google) with automatic fallback, cost logging, BYOK support,
and streaming.
"""

import asyncio
import logging
import os
import time
from collections.abc import AsyncGenerator

from litellm import acompletion, completion_cost
from litellm.exceptions import (
    AuthenticationError,
    RateLimitError,
)

from src.config.llm_settings import get_llm_settings
from src.telemetry.logger import log_event

# Timeout before falling back to secondary model
STREAM_TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)


CHUNK_TIMEOUT_SECONDS = 30


class LLMClientError(Exception):
    """Base exception for LLM client errors."""

    pass


class RateLimitExceededError(LLMClientError):
    """Raised when API rate limit is exceeded."""

    pass


class AuthenticationFailedError(LLMClientError):
    """Raised when API authentication fails."""

    pass



class UnsupportedModelError(LLMClientError):
    """Raised when a user-supplied BYOK model is not on known patterns."""

    pass

# Backward compatibility alias
ClaudeClientError = LLMClientError


def _is_retryable(e: Exception) -> bool:
    """True if the error is worth retrying with a fallback model."""
    if isinstance(e, (TimeoutError, asyncio.TimeoutError)):
        return True
    if isinstance(e, RateLimitError):
        return True
    if isinstance(e, AuthenticationError):
        return False
    msg = str(e).lower()
    return any(k in msg for k in ("timeout", "502", "503", "504", "overloaded"))



def is_valid_byok_model(model: str) -> bool:
    """Return True if model string matches known safe patterns for BYOK use.

    Prevents garbage models from reaching LiteLLM (causing 500s).
    Supports common provider prefixes and openrouter routed models.
    """
    if not model or not isinstance(model, str):
        return False
    m = model.strip().lower()
    if len(m) > 120 or any(bad in m for bad in (";", "drop", "script", "<", "`", "union")):
        return False
    # Accept direct or openrouter prefixed
    prefixes = (
        "anthropic/", "claude",
        "openai/", "gpt-",
        "google/", "gemini",
        "openrouter/",
        "user/",
    )
    if any(m.startswith(p) or p in m for p in prefixes):
        return True
    # Also accept bare model-ish (some litellm handle)
    if m.startswith(("claude", "gpt", "gemini", "deepseek", "llama", "mistral")):
        return True
    return False


def validate_byok_model(model: str | None) -> None:
    """Validate user supplied model for BYOK. Raise on invalid."""
    if model is None:
        return
    if not is_valid_byok_model(model):
        raise UnsupportedModelError(f"Unsupported model for provider: {model}")

class LLMClient:
    """Unified interface for all LLM providers via LiteLLM.

    Supports BYOK (Bring Your Own Key) — pass api_key/model to override
    server defaults with user-provided credentials.
    """

    def __init__(self) -> None:
        self.settings = get_llm_settings()
        self._setup_environment()

    def _setup_environment(self) -> None:
        """Set environment variables for LiteLLM."""
        if self.settings.OPENROUTER_API_KEY:
            os.environ["OPENROUTER_API_KEY"] = self.settings.OPENROUTER_API_KEY
            os.environ["OR_SITE_URL"] = self.settings.OR_SITE_URL
            os.environ["OR_APP_NAME"] = self.settings.OR_APP_NAME

        if self.settings.ANTHROPIC_API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = self.settings.ANTHROPIC_API_KEY

        if self.settings.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = self.settings.OPENAI_API_KEY

        if self.settings.GOOGLE_API_KEY:
            os.environ["GOOGLE_API_KEY"] = self.settings.GOOGLE_API_KEY

    async def get_response(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 400,
        temperature: float = 0.7,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = STREAM_TIMEOUT_SECONDS,
    ) -> str:
        """Get LLM response, optionally using user-provided key/model.

        Args:
            prompt: User prompt/message
            system: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature 0-1
            api_key: User-provided API key (BYOK), overrides server default
            model: User-provided model ID, overrides server default
            timeout: Connection timeout in seconds (None = no limit)
        """
        messages = self._build_messages(prompt, system)
        if api_key:
            validate_byok_model(model)
        target_model = model or self.settings.DEFAULT_MODEL

        try:
            return await self._call_llm(
                model=target_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                api_key=api_key,
                timeout=timeout,
            )
        except Exception as e:
            if api_key or not self.settings.ENABLE_FALLBACK or not _is_retryable(e):
                raise self._classify_exception(e) from e

            logger.warning("Primary model failed (retryable): %s", e)
            logger.info("Trying fallback: %s", self.settings.FALLBACK_MODEL)
            try:
                return await self._call_llm(
                    model=self.settings.FALLBACK_MODEL,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=None,
                )
            except Exception as fallback_error:
                logger.error("Fallback also failed: %s", fallback_error)
                raise LLMClientError(
                    f"Both primary and fallback failed: {fallback_error}"
                ) from fallback_error

    async def get_response_stream(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 400,
        temperature: float = 0.7,
        api_key: str | None = None,
        model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response chunks with fallback and timeout.

        Falls back to FALLBACK_MODEL if primary model fails or times out.
        Skips fallback when user provides their own key (BYOK).
        """
        messages = self._build_messages(prompt, system)
        if api_key:
            validate_byok_model(model)
        target_model = model or self.settings.DEFAULT_MODEL
        can_fallback = not api_key and self.settings.ENABLE_FALLBACK
        yielded_any = False

        try:
            async for chunk in self._stream_with_timeout(
                target_model, messages, max_tokens, temperature, api_key
            ):
                yielded_any = True
                yield chunk
        except Exception as e:
            if yielded_any or not can_fallback or not _is_retryable(e):
                raise self._classify_exception(e) from e

            logger.warning("Primary stream failed (%s): %s", target_model, e)
            logger.info("Falling back to: %s", self.settings.FALLBACK_MODEL)

            try:
                async for chunk in self._stream_with_timeout(
                    self.settings.FALLBACK_MODEL, messages, max_tokens, temperature,
                    timeout=None,
                ):
                    yield chunk
            except Exception as fallback_err:
                logger.error("Fallback stream also failed: %s", fallback_err)
                raise LLMClientError(
                    f"Both primary and fallback failed: {fallback_err}"
                ) from fallback_err

    async def _stream_with_timeout(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        api_key: str | None = None,
        timeout: float | None = STREAM_TIMEOUT_SECONDS,
    ) -> AsyncGenerator[str, None]:
        """Stream from a single model with optional timeout on connection."""
        if api_key:
            validate_byok_model(model)
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if api_key:
            kwargs["api_key"] = api_key

        t0 = time.monotonic()
        try:
            coro = acompletion(**kwargs)
            if timeout is not None:
                response = await asyncio.wait_for(coro, timeout=timeout)
            else:
                response = await coro
        except TimeoutError:
            raise LLMClientError(
                f"Timeout: no response from {model} within {timeout}s"
            )
        connect_s = round(time.monotonic() - t0, 2)

        last_chunk = None
        ttfb = None
        aiter = response.__aiter__()
        while True:
            try:
                chunk = await asyncio.wait_for(
                    aiter.__anext__(), timeout=CHUNK_TIMEOUT_SECONDS
                )
            except StopAsyncIteration:
                break
            except TimeoutError:
                raise LLMClientError(
                    f"Stream stalled: no chunk from {model} for {CHUNK_TIMEOUT_SECONDS}s"
                )
            if ttfb is None:
                ttfb = round(time.monotonic() - t0, 2)
            last_chunk = chunk
            content = chunk.choices[0].delta.content
            if content:
                yield content

        total_s = round(time.monotonic() - t0, 2)
        await _log_llm_metrics(model, last_chunk, total_s, streaming=True, connect_s=connect_s, ttfb=ttfb)

    @staticmethod
    def _classify_exception(e: Exception) -> LLMClientError:
        if isinstance(e, LLMClientError):
            return e
        if isinstance(e, RateLimitError):
            return RateLimitExceededError(f"Rate limit exceeded: {e}")
        if isinstance(e, AuthenticationError):
            return AuthenticationFailedError(f"Authentication failed: {e}")
        return LLMClientError(str(e))

    def _build_messages(self, prompt: str, system: str | None = None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _call_llm(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        api_key: str | None = None,
        timeout: float | None = STREAM_TIMEOUT_SECONDS,
    ) -> str:
        """Make LLM API call via LiteLLM."""
        if api_key:
            validate_byok_model(model)
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if api_key:
            kwargs["api_key"] = api_key

        t0 = time.monotonic()
        try:
            coro = acompletion(**kwargs)
            if timeout is not None:
                response = await asyncio.wait_for(coro, timeout=timeout)
            else:
                response = await coro
        except TimeoutError:
            raise LLMClientError(
                f"Timeout: no response from {model} within {timeout}s"
            )
        total_s = round(time.monotonic() - t0, 2)

        content = response.choices[0].message.content or ""
        await _log_llm_metrics(model, response, total_s, streaming=False, connect_s=total_s, ttfb=total_s)
        return content

async def _log_llm_metrics(
    model: str,
    response: object,
    total_s: float,
    streaming: bool,
    connect_s: float | None = None,
    ttfb: float | None = None,
) -> None:
    """Log LLM call metrics to stdout and telemetry JSONL.

    Args:
        model: Model ID used
        response: LiteLLM response (or last chunk for streaming)
        total_s: Total wall clock time (request start → last byte)
        streaming: Whether this was a streaming call
        connect_s: Time to establish connection (acompletion returns)
        ttfb: Time to first byte/chunk
    """
    cost = None
    tokens = None
    try:
        cost = completion_cost(completion_response=response)
    except Exception:
        pass
    try:
        usage = getattr(response, "usage", None)
        if usage:
            tokens = getattr(usage, "total_tokens", None)
    except Exception:
        pass

    metrics = {
        "model": model,
        "connect_s": connect_s,
        "ttfb_s": ttfb,
        "total_s": total_s,
        "tokens": tokens,
        "cost_usd": round(cost, 6) if cost else None,
        "streaming": streaming,
    }
    logger.info(
        "LLM call: model=%s, connect=%.2fs, ttfb=%s, total=%.2fs, tokens=%s, cost=$%s",
        model, connect_s or 0, f"{ttfb:.2f}s" if ttfb else "N/A", total_s, tokens,
        f"{cost:.6f}" if cost else "N/A",
    )
    await log_event("llm_call", "system", "system", metrics)


# Module-level client instance (lazy initialization)
_client: LLMClient | None = None
_client_override: LLMClient | None = None


def get_client() -> LLMClient:
    """Get singleton LLM client instance."""
    global _client
    if _client_override is not None:
        return _client_override
    if _client is None:
        try:
            _client = LLMClient()
        except ValueError as e:
            raise LLMClientError(str(e)) from e
    return _client


def reset_llm_client() -> None:
    """Reset singleton and test override (for pytest isolation)."""
    global _client, _client_override
    _client = None
    _client_override = None


def set_llm_client_override(client: LLMClient | None) -> None:
    """Inject a test double without patching multiple import sites."""
    global _client_override
    _client_override = client


async def get_response(prompt: str, system: str | None = None) -> str:
    """Convenience function for quick responses."""
    client = get_client()
    return await client.get_response(prompt, system=system)


