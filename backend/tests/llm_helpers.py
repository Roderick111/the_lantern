"""Shared test helpers for LLM client tests.

Provides fake LiteLLM responses, fake streaming generators, and patch fixtures
to capture behavior of `src.api.llm_client` before its planned refactor
(error classification, fallback whitelist, mid-stream abort).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Fake LiteLLM response objects (non-streaming)
# ---------------------------------------------------------------------------


@dataclass
class FakeMessage:
    content: str


@dataclass
class FakeChoice:
    message: FakeMessage
    delta: FakeMessage | None = None
    finish_reason: str | None = "stop"


@dataclass
class FakeUsage:
    total_tokens: int = 10
    prompt_tokens: int = 5
    completion_tokens: int = 5
    reasoning_tokens: int = 2


@dataclass
class FakeResponse:
    """Mimics a LiteLLM non-streaming completion response."""

    content: str = "ok"
    model: str = "test/model"

    @property
    def choices(self) -> list[FakeChoice]:
        return [FakeChoice(message=FakeMessage(content=self.content))]

    @property
    def usage(self) -> FakeUsage:
        return FakeUsage()


def make_fake_response(content: str = "ok", model: str = "test/model") -> FakeResponse:
    return FakeResponse(content=content, model=model)


# ---------------------------------------------------------------------------
# Fake streaming chunks
# ---------------------------------------------------------------------------


@dataclass
class FakeStreamDelta:
    content: str | None


@dataclass
class FakeStreamChoice:
    delta: FakeStreamDelta
    finish_reason: str | None = None


@dataclass
class FakeStreamChunk:
    """Mimics a LiteLLM streaming chunk."""

    text: str | None
    model: str = "test/model"
    finish_reason: str | None = None

    @property
    def choices(self) -> list[FakeStreamChoice]:
        return [
            FakeStreamChoice(
                delta=FakeStreamDelta(content=self.text),
                finish_reason=self.finish_reason,
            )
        ]

    @property
    def usage(self) -> FakeUsage:
        return FakeUsage()


async def fake_stream_from(texts: Iterable[str]) -> AsyncIterator[FakeStreamChunk]:
    """Build an async iterator yielding fake chunks for each text in `texts`."""
    for t in texts:
        yield FakeStreamChunk(text=t)


async def fake_stream_then_raise(
    texts: Iterable[str], exc: BaseException
) -> AsyncIterator[FakeStreamChunk]:
    """Yield chunks then raise. Used to test mid-stream fallback bug."""
    for t in texts:
        yield FakeStreamChunk(text=t)
    raise exc


async def fake_stream_one_then_hang(text: str) -> AsyncIterator[FakeStreamChunk]:
    """Yield one chunk, then hang forever. Proves no per-chunk timeout exists."""
    yield FakeStreamChunk(text=text)
    # Sleep forever — current client has no per-chunk timeout
    await asyncio.sleep(3600)


# ---------------------------------------------------------------------------
# acompletion patch builders
# ---------------------------------------------------------------------------


def make_acompletion_returning(value: Any) -> AsyncMock:
    """Build an AsyncMock for `litellm.acompletion` that resolves to value."""
    return AsyncMock(return_value=value)


def make_acompletion_raising(exc: BaseException) -> AsyncMock:
    """Build an AsyncMock for `litellm.acompletion` that raises exc."""
    return AsyncMock(side_effect=exc)


class SequentialAcompletion:
    """Sequential SYNC fake for `litellm.acompletion`.

    Each invocation pops the next result from `results`:
      - BaseException subclass → raised (AsyncMock awaiter re-raises it)
      - anything else → returned (FakeResponse for non-stream; async iterator
        for streaming — LiteLLM's acompletion(stream=True) returns the iterator
        as the awaited value, which is what we mimic here)

    IMPORTANT: must be sync. `AsyncMock(side_effect=async_callable)` does NOT
    auto-await the inner coroutine — it returns the raw coroutine object.
    Sync side_effect returning a plain value is what AsyncMock awaits to.

    Use with `patch(target, new=AsyncMock(side_effect=instance))`.

    Records each call's kwargs in `self.calls`.
    """

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if not self._results:
            raise RuntimeError("SequentialAcompletion exhausted")
        result = self._results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def patch_acompletion(seq: SequentialAcompletion):
    """Convenience: build a context manager that patches acompletion with an
    AsyncMock wrapping the SequentialAcompletion instance.
    """
    from unittest.mock import AsyncMock
    from unittest.mock import patch as _patch

    return _patch(
        "src.api.llm_client.acompletion",
        new=AsyncMock(side_effect=seq),
    )


# ---------------------------------------------------------------------------
# Reset helpers — singletons in llm_client / llm_settings
# ---------------------------------------------------------------------------


def reset_llm_singletons() -> None:
    """Clear cached singletons so a fresh LLMClient picks up monkeypatched env."""
    import src.api.llm_client as lc
    import src.config.llm_settings as ls

    ls._settings = None
    lc._client = None


def make_settings(**overrides: Any) -> MagicMock:
    """Build a MagicMock that quacks like LLMSettings, with sensible defaults."""
    from src.config.llm_settings import LLMProvider

    settings = MagicMock()
    settings.DEFAULT_LLM_PROVIDER = overrides.get(
        "DEFAULT_LLM_PROVIDER", LLMProvider.OPENROUTER
    )
    settings.OPENROUTER_API_KEY = overrides.get("OPENROUTER_API_KEY", "or-test-key")
    settings.ANTHROPIC_API_KEY = overrides.get("ANTHROPIC_API_KEY", "")
    settings.OPENAI_API_KEY = overrides.get("OPENAI_API_KEY", "")
    settings.GOOGLE_API_KEY = overrides.get("GOOGLE_API_KEY", "")
    settings.DEFAULT_MODEL = overrides.get(
        "DEFAULT_MODEL", "openrouter/test/primary"
    )
    settings.FALLBACK_MODEL = overrides.get(
        "FALLBACK_MODEL", "openrouter/test/fallback"
    )
    settings.ENABLE_FALLBACK = overrides.get("ENABLE_FALLBACK", True)
    settings.OR_SITE_URL = overrides.get("OR_SITE_URL", "https://example.test")
    settings.OR_APP_NAME = overrides.get("OR_APP_NAME", "TestApp")
    return settings
