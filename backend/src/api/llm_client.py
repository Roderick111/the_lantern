"""Unified LLM client using LiteLLM for multi-provider support.

Provides async interface for multiple LLM providers (Anthropic, OpenRouter,
OpenAI, Google) with automatic fallback, cost logging, BYOK support,
and streaming.
"""

import asyncio
import logging
import random
import time
from collections.abc import AsyncGenerator
from typing import Any

from litellm import acompletion, completion_cost
from litellm.exceptions import (
    AuthenticationError,
    RateLimitError,
)

from src.config.llm_settings import get_llm_settings
from src.telemetry.logger import log_event

# Provider connection timeout. The shared SSE runner enforces full request
# deadlines, so no provider attempt can run forever.
STREAM_TIMEOUT_SECONDS = 8

logger = logging.getLogger(__name__)


CHUNK_TIMEOUT_SECONDS = 90


class LLMClientError(Exception):
    """Base exception for LLM client errors."""

    pass


class RateLimitExceededError(LLMClientError):
    """Raised when API rate limit is exceeded."""

    pass


class AuthenticationFailedError(LLMClientError):
    """Raised when API authentication fails."""

    pass


class EmptyLLMResponseError(LLMClientError):
    """Raised when a provider completes without returning text."""

    pass


class LLMConnectionError(LLMClientError):
    """Raised when provider connection fails before visible output."""

    pass


class LLMTimeoutError(LLMClientError):
    """Raised when provider connection or stream deadline expires."""

    pass


class LLMServiceUnavailableError(LLMClientError):
    """Raised when provider reports a transient service failure."""

    pass


class UnsupportedModelError(LLMClientError):
    """Raised when a user-supplied BYOK model is not on known patterns."""

    pass


# Backward compatibility alias
ClaudeClientError = LLMClientError


def _is_retryable(e: Exception) -> bool:
    """True if the error is worth retrying with a fallback model."""
    if isinstance(e, EmptyLLMResponseError):
        return True
    if isinstance(e, (TimeoutError, asyncio.TimeoutError, LLMTimeoutError)):
        return True
    if isinstance(e, (RateLimitError, LLMConnectionError, LLMServiceUnavailableError)):
        return True
    if isinstance(e, AuthenticationError):
        return False
    msg = str(e).lower()
    return any(
        k in msg
        for k in (
            "timeout",
            "timed out",
            "connection",
            "disconnect",
            "502",
            "503",
            "504",
            "service unavailable",
            "temporarily unavailable",
            "overloaded",
            "connection reset",
        )
    )


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
        "anthropic/",
        "claude",
        "openai/",
        "gpt-",
        "google/",
        "gemini",
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

    async def get_response(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 400,
        temperature: float = 0.7,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = STREAM_TIMEOUT_SECONDS,
        disable_reasoning: bool = False,
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
                disable_reasoning=disable_reasoning,
            )
        except Exception as e:
            if api_key and _is_retryable(e):
                await asyncio.sleep(random.uniform(0, 0.5))
                try:
                    return await self._call_llm(
                        model=target_model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        api_key=api_key,
                        timeout=timeout,
                        disable_reasoning=disable_reasoning,
                    )
                except Exception as retry_error:
                    raise self._classify_exception(retry_error) from retry_error
            if not self.settings.ENABLE_FALLBACK or not _is_retryable(e):
                raise self._classify_exception(e) from e

            logger.warning("Primary model failed (retryable): %s", e)
            logger.info("Trying fallback: %s", self.settings.FALLBACK_MODEL)
            try:
                return await self._call_llm(
                    model=self.settings.FALLBACK_MODEL,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    api_key=self._provider_api_key(self.settings.FALLBACK_MODEL),
                    timeout=STREAM_TIMEOUT_SECONDS,
                    fallback=True,
                    disable_reasoning=disable_reasoning,
                )
            except Exception as fallback_error:
                logger.error("Fallback also failed: %s", fallback_error)
                classified = self._classify_exception(fallback_error)
                if isinstance(classified, (EmptyLLMResponseError, RateLimitExceededError, AuthenticationFailedError, UnsupportedModelError)):
                    raise classified from fallback_error
                raise LLMConnectionError(
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
        trace: list[dict[str, Any]] | None = None,
        disable_reasoning: bool = False,
        endpoint: str | None = None,
        request_id: str | None = None,
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
                target_model,
                messages,
                max_tokens,
                temperature,
                api_key,
                trace=trace,
                disable_reasoning=disable_reasoning,
                endpoint=endpoint,
                request_id=request_id,
                attempt=1,
            ):
                yielded_any = True
                yield chunk
        except Exception as e:
            if yielded_any or not _is_retryable(e):
                raise self._classify_exception(e) from e

            if api_key:
                logger.warning("BYOK stream failed; retrying same model: %s", target_model)
                await asyncio.sleep(random.uniform(0, 0.5))
                try:
                    async for chunk in self._stream_with_timeout(
                        target_model,
                        messages,
                        max_tokens,
                        temperature,
                        api_key=api_key,
                        trace=trace,
                        disable_reasoning=disable_reasoning,
                        endpoint=endpoint,
                        request_id=request_id,
                        attempt=2,
                    ):
                        yield chunk
                    return
                except Exception as retry_error:
                    raise self._classify_exception(retry_error) from retry_error

            if not can_fallback:
                raise self._classify_exception(e) from e

            logger.warning("Primary stream failed (%s): %s", target_model, e)
            logger.info("Falling back to: %s", self.settings.FALLBACK_MODEL)

            try:
                async for chunk in self._stream_with_timeout(
                    self.settings.FALLBACK_MODEL,
                    messages,
                    max_tokens,
                    temperature,
                    api_key=self._provider_api_key(self.settings.FALLBACK_MODEL),
                    timeout=STREAM_TIMEOUT_SECONDS,
                    fallback=True,
                    trace=trace,
                    disable_reasoning=disable_reasoning,
                    endpoint=endpoint,
                    request_id=request_id,
                    attempt=2,
                ):
                    yield chunk
            except Exception as fallback_err:
                logger.error("Fallback stream also failed: %s", fallback_err)
                classified = self._classify_exception(fallback_err)
                if isinstance(classified, (EmptyLLMResponseError, RateLimitExceededError, AuthenticationFailedError, UnsupportedModelError)):
                    raise classified from fallback_err
                raise LLMConnectionError(
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
        fallback: bool = False,
        trace: list[dict[str, Any]] | None = None,
        disable_reasoning: bool = False,
        endpoint: str | None = None,
        request_id: str | None = None,
        attempt: int = 1,
    ) -> AsyncGenerator[str, None]:
        """Stream from a single model with optional timeout on connection."""
        if api_key:
            validate_byok_model(model)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if api_key:
            kwargs["api_key"] = api_key
        else:
            provider_key = self._provider_api_key(model)
            if provider_key:
                kwargs["api_key"] = provider_key
        if disable_reasoning:
            kwargs["reasoning"] = {"enabled": False}
        if model.startswith("openrouter/"):
            kwargs["provider"] = {
                "sort": "throughput",
                "allow_fallbacks": True,
                "require_parameters": True,
            }
            kwargs["extra_headers"] = {
                "HTTP-Referer": self.settings.OR_SITE_URL,
                "X-Title": self.settings.OR_APP_NAME,
            }

        t0 = time.monotonic()
        try:
            coro = acompletion(**kwargs)
            if timeout is not None:
                response = await asyncio.wait_for(coro, timeout=timeout)
            else:
                response = await coro
        except TimeoutError:
            raise LLMClientError(f"Timeout: no response from {model} within {timeout}s")
        connect_s = round(time.monotonic() - t0, 2)

        last_chunk = None
        ttfb = None
        yielded_content = False
        actual_model: str | None = None
        finish_reason: str | None = None
        usage: object | None = None
        visible_started = False
        chunk_count = 0
        chunk_gaps: list[float] = []
        last_event_at: float | None = None
        visible_ttfb: float | None = None
        aiter = response.__aiter__()
        while True:
            try:
                chunk = await asyncio.wait_for(
                    aiter.__anext__(),
                    timeout=STREAM_TIMEOUT_SECONDS
                    if not visible_started
                    else CHUNK_TIMEOUT_SECONDS,
                )
            except StopAsyncIteration:
                break
            except TimeoutError:
                raise LLMClientError(
                    f"Stream stalled: no visible output from {model} within "
                    f"{STREAM_TIMEOUT_SECONDS if not visible_started else CHUNK_TIMEOUT_SECONDS}s"
                )
            if ttfb is None:
                ttfb = round(time.monotonic() - t0, 2)
            now = time.monotonic()
            if last_event_at is not None:
                chunk_gaps.append(round(now - last_event_at, 3))
            last_event_at = now
            chunk_count += 1
            last_chunk = chunk
            actual_model = _field(chunk, "model") or actual_model
            usage = _field(chunk, "usage") or usage
            choices = _field(chunk, "choices") or []
            if choices:
                finish_reason = _field(choices[0], "finish_reason") or finish_reason
                delta = _field(choices[0], "delta")
                content = _field(delta, "content")
            else:
                content = None
            if content and content.strip():
                yielded_content = True
                visible_started = True
                if visible_ttfb is None:
                    visible_ttfb = round(time.monotonic() - t0, 2)
                yield content

        total_s = round(time.monotonic() - t0, 2)
        metrics_response = {
            "model": actual_model or model,
            "choices": ([{"finish_reason": finish_reason}] if finish_reason else []),
            "usage": usage,
        }
        metrics = await _log_llm_metrics(
            model,
            metrics_response if last_chunk is not None else None,
            total_s,
            streaming=True,
            connect_s=connect_s,
            ttfb=ttfb,
            fallback=fallback,
            extra={
                "chunk_count": chunk_count,
                "visible_ttfb_s": visible_ttfb,
                "chunk_gap_p50_s": _percentile(chunk_gaps, 0.50),
                "chunk_gap_p95_s": _percentile(chunk_gaps, 0.95),
                "visible_tokens_per_second": _visible_tokens_per_second(
                    usage, total_s, visible_ttfb
                ),
                "endpoint": endpoint,
                "request_id": request_id,
                "attempt": attempt,
            },
        )
        if trace is not None:
            trace.append(_diagnostic_trace(metrics))
        if not yielded_content:
            raise EmptyLLMResponseError(f"Empty response from {model}")

    @staticmethod
    def _classify_exception(e: Exception) -> LLMClientError:
        if isinstance(e, LLMClientError):
            return e
        if isinstance(e, RateLimitError):
            return RateLimitExceededError(f"Rate limit exceeded: {e}")
        if isinstance(e, AuthenticationError):
            return AuthenticationFailedError(f"Authentication failed: {e}")
        if isinstance(e, (TimeoutError, asyncio.TimeoutError)) or "timeout" in str(e).lower():
            return LLMTimeoutError(str(e))
        if isinstance(e, (ConnectionError, OSError)) or any(
            token in str(e).lower() for token in ("connection", "disconnect", "502", "503", "504")
        ):
            return LLMConnectionError(str(e))
        return LLMClientError(str(e))

    def _provider_api_key(self, model: str) -> str | None:
        """Resolve server credential per request; never mutate process env."""
        if model.startswith("openrouter/"):
            return self.settings.OPENROUTER_API_KEY or None
        if model.startswith(("anthropic/", "claude")):
            return self.settings.ANTHROPIC_API_KEY or None
        if model.startswith(("openai/", "gpt-")):
            return self.settings.OPENAI_API_KEY or None
        if model.startswith(("google/", "gemini")):
            return self.settings.GOOGLE_API_KEY or None
        return None

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
        fallback: bool = False,
        disable_reasoning: bool = False,
    ) -> str:
        """Make LLM API call via LiteLLM."""
        if api_key:
            validate_byok_model(model)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if api_key:
            kwargs["api_key"] = api_key
        else:
            provider_key = self._provider_api_key(model)
            if provider_key:
                kwargs["api_key"] = provider_key
        if disable_reasoning:
            kwargs["reasoning"] = {"enabled": False}
        if model.startswith("openrouter/"):
            kwargs["provider"] = {
                "sort": "throughput",
                "allow_fallbacks": True,
                "require_parameters": True,
            }
            kwargs["extra_headers"] = {
                "HTTP-Referer": self.settings.OR_SITE_URL,
                "X-Title": self.settings.OR_APP_NAME,
            }

        t0 = time.monotonic()
        try:
            coro = acompletion(**kwargs)
            if timeout is not None:
                response = await asyncio.wait_for(coro, timeout=timeout)
            else:
                response = await coro
        except TimeoutError:
            raise LLMClientError(f"Timeout: no response from {model} within {timeout}s")
        total_s = round(time.monotonic() - t0, 2)

        content = response.choices[0].message.content or ""
        await _log_llm_metrics(
            model,
            response,
            total_s,
            streaming=False,
            connect_s=total_s,
            ttfb=total_s,
            fallback=fallback,
        )
        if not content.strip():
            raise EmptyLLMResponseError(f"Empty response from {model}")
        return content


async def _log_llm_metrics(
    model: str,
    response: object,
    total_s: float,
    streaming: bool,
    connect_s: float | None = None,
    ttfb: float | None = None,
    fallback: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    usage_values = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "reasoning_tokens": None,
        "total_tokens": None,
    }
    try:
        cost = completion_cost(completion_response=response)
    except Exception:
        pass
    try:
        usage = _field(response, "usage")
        if usage:
            usage_values["prompt_tokens"] = _field(usage, "prompt_tokens")
            usage_values["completion_tokens"] = _field(usage, "completion_tokens")
            usage_values["total_tokens"] = _field(usage, "total_tokens")
            usage_values["reasoning_tokens"] = _field(usage, "reasoning_tokens")
            if usage_values["reasoning_tokens"] is None:
                details = _field(usage, "completion_tokens_details")
                usage_values["reasoning_tokens"] = _field(details, "reasoning_tokens")
    except Exception:
        pass

    actual_model = _field(response, "model") or model
    choices = _field(response, "choices") or []
    finish_reason = _field(choices[0], "finish_reason") if choices else None
    metrics = {
        "model": model,
        "requested_model": model,
        "actual_model": actual_model,
        "provider": actual_model.split("/", 1)[0] if isinstance(actual_model, str) else None,
        "fallback": fallback,
        "finish_reason": finish_reason,
        "connect_s": connect_s,
        "ttfb_s": ttfb,
        "total_s": total_s,
        "tokens": usage_values["total_tokens"],
        **usage_values,
        "cost_usd": round(cost, 6) if cost else None,
        "streaming": streaming,
    }
    if extra:
        metrics.update(extra)
    logger.info(
        "LLM call: requested=%s, actual=%s, fallback=%s, finish=%s, "
        "connect=%.2fs, ttfb=%s, total=%.2fs, completion=%s, reasoning=%s, "
        "tokens=%s, cost=$%s",
        model,
        actual_model,
        fallback,
        finish_reason,
        connect_s or 0,
        f"{ttfb:.2f}s" if ttfb else "N/A",
        total_s,
        usage_values["completion_tokens"],
        usage_values["reasoning_tokens"],
        usage_values["total_tokens"],
        f"{cost:.6f}" if cost else "N/A",
    )
    await log_event("llm_call", "system", "system", metrics)
    return metrics


def _field(value: object, name: str) -> Any:
    """Read one field from LiteLLM objects or dictionaries."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _diagnostic_trace(metrics: dict[str, Any]) -> dict[str, Any]:
    """Keep provider result fields needed by live diagnostics."""
    fields = (
        "requested_model",
        "actual_model",
        "provider",
        "fallback",
        "finish_reason",
        "prompt_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "total_tokens",
        "chunk_count",
        "visible_ttfb_s",
        "chunk_gap_p50_s",
        "chunk_gap_p95_s",
    )
    return {field: metrics.get(field) for field in fields}


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def _visible_tokens_per_second(
    usage: object | None,
    total_s: float,
    visible_ttfb: float | None,
) -> float | None:
    completion_tokens = _field(usage, "completion_tokens")
    if not isinstance(completion_tokens, (int, float)):
        return None
    visible_duration = max(total_s - (visible_ttfb or 0), 0.001)
    return round(float(completion_tokens) / visible_duration, 2)


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
