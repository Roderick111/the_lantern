"""Tests for src.api.llm_client.

Covers fallback whitelist, mid-stream fallback guard, per-chunk timeout,
and error classification.
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest
from litellm.exceptions import AuthenticationError, RateLimitError

from tests.llm_helpers import (
    SequentialAcompletion,
    fake_stream_from,
    fake_stream_one_then_hang,
    fake_stream_then_raise,
    make_acompletion_raising,
    make_fake_response,
    make_settings,
    reset_llm_singletons,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_client(monkeypatch: pytest.MonkeyPatch):
    """Yield a fresh LLMClient with deterministic settings + clean singletons."""
    reset_llm_singletons()

    fake_settings = make_settings()
    monkeypatch.setattr("src.api.llm_client.get_llm_settings", lambda: fake_settings)

    from src.api.llm_client import LLMClient

    client = LLMClient()
    yield client, fake_settings

    reset_llm_singletons()


# ---------------------------------------------------------------------------
# Non-streaming fallback behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_key_retriable_error_engages_fallback(fresh_client):
    """Server-side key + RateLimitError → fallback called.

    This part of the existing behavior is intentional and correct.
    """
    client, settings = fresh_client

    primary_err = RateLimitError(
        message="rate limited", model=settings.DEFAULT_MODEL, llm_provider="openrouter"
    )
    fake = SequentialAcompletion([primary_err, make_fake_response("from-fallback")])

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        result = await client.get_response(prompt="hello")

    assert result == "from-fallback"
    assert len(fake.calls) == 2
    assert fake.calls[0]["model"] == settings.DEFAULT_MODEL
    assert fake.calls[1]["model"] == settings.FALLBACK_MODEL


@pytest.mark.asyncio
async def test_disable_reasoning_reaches_non_streaming_provider(fresh_client):
    client, _ = fresh_client
    fake = SequentialAcompletion([make_fake_response("plain")])

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        result = await client.get_response(prompt="hello", disable_reasoning=True)

    assert result == "plain"
    assert fake.calls[0]["reasoning"] == {"enabled": False}


@pytest.mark.asyncio
async def test_server_key_auth_error_does_not_fallback(fresh_client):
    """AuthenticationError is not retryable — fallback must NOT be attempted."""
    client, settings = fresh_client
    from src.api.llm_client import AuthenticationFailedError

    auth_err = AuthenticationError(
        message="bad key", model=settings.DEFAULT_MODEL, llm_provider="openrouter"
    )
    fake = SequentialAcompletion([auth_err, make_fake_response("from-fallback")])

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        with pytest.raises(AuthenticationFailedError):
            await client.get_response(prompt="hello")

    assert len(fake.calls) == 1, "fallback should NOT be attempted on auth error"


@pytest.mark.asyncio
async def test_server_key_generic_error_no_fallback(fresh_client):
    """Generic Exception (not retryable) does NOT trigger fallback."""
    client, settings = fresh_client
    from src.api.llm_client import LLMClientError

    fake = SequentialAcompletion([Exception("boom"), make_fake_response("ok")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        with pytest.raises(LLMClientError):
            await client.get_response(prompt="hi")

    assert len(fake.calls) == 1, "non-retryable error should not trigger fallback"


@pytest.mark.asyncio
async def test_server_key_timeout_engages_fallback(fresh_client):
    """TimeoutError is retryable — fallback should be called."""
    client, settings = fresh_client

    fake = SequentialAcompletion([TimeoutError("timed out"), make_fake_response("ok")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        result = await client.get_response(prompt="hi")

    assert result == "ok"
    assert fake.calls[1]["model"] == settings.FALLBACK_MODEL


@pytest.mark.asyncio
async def test_empty_response_engages_fallback(fresh_client):
    """Empty provider output is failure, not a valid narrator response."""
    client, settings = fresh_client
    fake = SequentialAcompletion([make_fake_response(""), make_fake_response("from-fallback")])

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        result = await client.get_response(prompt="hi")

    assert result == "from-fallback"
    assert len(fake.calls) == 2
    assert fake.calls[1]["model"] == settings.FALLBACK_MODEL


@pytest.mark.asyncio
async def test_disabled_fallback_propagates_error(fresh_client, monkeypatch: pytest.MonkeyPatch):
    """When ENABLE_FALLBACK is False, primary error wraps to LLMClientError."""
    client, settings = fresh_client
    settings.ENABLE_FALLBACK = False

    from src.api.llm_client import LLMClientError

    fake = make_acompletion_raising(Exception("boom"))
    with patch("src.api.llm_client.acompletion", fake):
        with pytest.raises(LLMClientError):
            await client.get_response(prompt="hi")


@pytest.mark.asyncio
async def test_both_primary_and_fallback_fail(fresh_client):
    """Both retryable calls fail → LLMClientError with 'Both primary and fallback failed'."""
    client, _ = fresh_client
    from src.api.llm_client import LLMClientError

    fake = SequentialAcompletion([TimeoutError("primary"), TimeoutError("fallback")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        with pytest.raises(LLMClientError, match="Both primary and fallback failed"):
            await client.get_response(prompt="hi")


# ---------------------------------------------------------------------------
# Streaming + fallback mid-stream concatenation (REGRESSION)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_streaming_mid_stream_no_fallback_after_chunks_yielded(fresh_client):
    """Primary yields chunks then raises → no fallback (yielded_any guard).

    Once the client has received chunks from the primary model, falling back
    would concatenate incoherent text from two different models. The guard
    re-raises instead.
    """
    client, _ = fresh_client
    from src.api.llm_client import RateLimitExceededError

    primary_stream = fake_stream_then_raise(
        ["Hello ", "from primary "],
        RateLimitError(message="cut off", model="p", llm_provider="openrouter"),
    )
    fallback_stream = fake_stream_from(["chunk-A ", "chunk-B ", "chunk-C"])

    fake = SequentialAcompletion([primary_stream, fallback_stream])

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        chunks = []
        with pytest.raises(RateLimitExceededError):
            async for c in client.get_response_stream(prompt="hi"):
                chunks.append(c)

    assert chunks == ["Hello ", "from primary "]
    assert len(fake.calls) == 1, "fallback should NOT be attempted mid-stream"


@pytest.mark.asyncio
async def test_streaming_no_fallback_when_byok(fresh_client):
    """BYOK streaming: no fallback attempted on any error."""
    client, _ = fresh_client

    primary_stream = fake_stream_then_raise(["only-primary "], Exception("boom"))
    fallback_stream = fake_stream_from(["should-not-appear"])
    fake = SequentialAcompletion([primary_stream, fallback_stream])

    from src.api.llm_client import LLMClientError

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        with pytest.raises(LLMClientError):
            chunks = []
            async for c in client.get_response_stream(
                prompt="hi", api_key="user-key", model="user/model"
            ):
                chunks.append(c)

    # Only primary stream should have been consumed
    assert len(fake.calls) == 1
    assert fake.calls[0]["model"] == "user/model"
    assert fake.calls[0]["api_key"] == "user-key"


@pytest.mark.asyncio
async def test_disable_reasoning_reaches_streaming_provider(fresh_client):
    client, _ = fresh_client
    fake = SequentialAcompletion([fake_stream_from(["plain"])])

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        chunks = [
            chunk
            async for chunk in client.get_response_stream(prompt="hello", disable_reasoning=True)
        ]

    assert chunks == ["plain"]
    assert fake.calls[0]["reasoning"] == {"enabled": False}


@pytest.mark.asyncio
async def test_empty_stream_engages_fallback(fresh_client):
    """Stream with no text engages normal provider fallback."""
    client, settings = fresh_client
    fake = SequentialAcompletion([fake_stream_from([]), fake_stream_from(["from-fallback"])])

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        chunks = [chunk async for chunk in client.get_response_stream(prompt="hi")]

    assert chunks == ["from-fallback"]
    assert len(fake.calls) == 2
    assert fake.calls[1]["model"] == settings.FALLBACK_MODEL


@pytest.mark.asyncio
async def test_stream_trace_records_provider_metadata_and_fallback(fresh_client):
    """Trace captures each provider attempt without another LLM call."""
    client, settings = fresh_client
    from tests.llm_helpers import FakeStreamChunk

    async def completed_fallback():
        yield FakeStreamChunk(
            text="from-fallback",
            model="resolved/fallback-model",
            finish_reason="length",
        )

    fake = SequentialAcompletion([fake_stream_from([]), completed_fallback()])
    trace: list[dict] = []

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        chunks = [chunk async for chunk in client.get_response_stream(prompt="hi", trace=trace)]

    assert chunks == ["from-fallback"]
    assert all(call["stream_options"] == {"include_usage": True} for call in fake.calls)
    assert trace[0] == {
        "requested_model": settings.DEFAULT_MODEL,
        "actual_model": settings.DEFAULT_MODEL,
        "provider": "openrouter",
        "fallback": False,
        "finish_reason": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "reasoning_tokens": None,
        "total_tokens": None,
        "chunk_count": 0,
        "visible_ttfb_s": None,
        "chunk_gap_p50_s": None,
        "chunk_gap_p95_s": None,
    }
    assert trace[1] == {
        "requested_model": settings.FALLBACK_MODEL,
        "actual_model": "resolved/fallback-model",
        "provider": "resolved",
        "fallback": True,
        "finish_reason": "length",
        "prompt_tokens": 5,
        "completion_tokens": 5,
        "reasoning_tokens": 2,
        "total_tokens": 10,
        "chunk_count": 1,
        "visible_ttfb_s": 0.0,
        "chunk_gap_p50_s": None,
        "chunk_gap_p95_s": None,
    }
    assert len(trace) == 2


# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_streaming_connect_timeout_wraps_to_llm_client_error(fresh_client):
    """`asyncio.TimeoutError` during connect → LLMClientError('Timeout: ...').

    Note: client disables fallback for the BYOK path. To make the assertion
    deterministic, we test the BYOK case so we don't fall back.
    """
    client, _ = fresh_client

    from src.api.llm_client import LLMClientError

    fake = make_acompletion_raising(TimeoutError())
    with patch("src.api.llm_client.acompletion", fake):
        with pytest.raises(LLMClientError, match="Timeout"):
            chunks = []
            async for c in client.get_response_stream(
                prompt="hi", api_key="user-key", model="user/model"
            ):
                chunks.append(c)


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_no_per_chunk_timeout_is_enforced(fresh_client):
    """REGRESSION: client does NOT enforce a per-chunk timeout.

    Mock primary to yield one chunk then hang forever. We wrap the iteration
    in `asyncio.wait_for(timeout=2)` from OUTSIDE — that should be the only
    thing that fires. If the client implemented a per-chunk timeout, it would
    raise instead. We assert the *outer* `asyncio.TimeoutError` propagates.

    After refactor: client should enforce its own per-chunk timeout, so the
    iteration should raise `LLMClientError` BEFORE our outer wait_for trips.
    """
    client, _ = fresh_client

    stream = fake_stream_one_then_hang("first ")
    fake = SequentialAcompletion([stream])

    async def consume() -> list[str]:
        out: list[str] = []
        with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
            async for c in client.get_response_stream(
                prompt="hi", api_key="user-key", model="user/model"
            ):
                out.append(c)
        return out

    # Outer timeout MUST trip (current client has no inner per-chunk timeout)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(consume(), timeout=2.0)


# ---------------------------------------------------------------------------
# Stream content + ordering (keepalive integration is in helpers.py)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_streaming_preserves_chunk_order(fresh_client):
    """Slow stream still delivers chunks in order with no drops."""
    client, _ = fresh_client

    async def slow_stream():
        for t in ["a", "b", "c", "d"]:
            await asyncio.sleep(0.001)
            from tests.llm_helpers import FakeStreamChunk

            yield FakeStreamChunk(text=t)

    fake = SequentialAcompletion([slow_stream()])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        chunks = [
            c
            async for c in client.get_response_stream(
                prompt="hi", api_key="user-key", model="user/model"
            )
        ]

    assert chunks == ["a", "b", "c", "d"]


@pytest.mark.asyncio
async def test_streaming_drops_empty_content_chunks(fresh_client):
    """Chunks with None/empty delta.content are skipped (current behavior)."""
    client, _ = fresh_client

    from tests.llm_helpers import FakeStreamChunk

    async def gen():
        yield FakeStreamChunk(text=None)  # skipped
        yield FakeStreamChunk(text="real")
        yield FakeStreamChunk(text="")  # skipped (falsy)
        yield FakeStreamChunk(text="end")

    fake = SequentialAcompletion([gen()])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        chunks = [
            c
            async for c in client.get_response_stream(
                prompt="hi", api_key="user-key", model="user/model"
            )
        ]

    assert chunks == ["real", "end"]


# ---------------------------------------------------------------------------
# SSE keepalive format (helpers.py contract)
# ---------------------------------------------------------------------------


def test_sse_keepalive_format_starts_with_colon():
    """SSE keepalive comment must start with ':' per SSE spec."""
    from src.api.helpers import SSE_KEEPALIVE

    assert SSE_KEEPALIVE.startswith(":"), "SSE comments start with ':'"
    assert SSE_KEEPALIVE.endswith("\n\n"), "SSE messages end with blank line"


# ---------------------------------------------------------------------------
# get_client() singleton side-effects (REGRESSION)
# ---------------------------------------------------------------------------


def test_get_client_mutates_os_environ(monkeypatch: pytest.MonkeyPatch):
    """REGRESSION: get_client() writes provider keys into os.environ.

    `LLMClient._setup_environment()` injects API keys into the process
    environment as a side effect of construction. This complicates testing
    and means key rotation requires process restart.

    After refactor: env should NOT be touched; LiteLLM should receive keys
    via per-call kwargs only.
    """
    # Clear keys first so we can detect them being injected
    for k in ("OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)

    reset_llm_singletons()

    fake_settings = make_settings(
        OPENROUTER_API_KEY="injected-or-key",
        ANTHROPIC_API_KEY="injected-anthropic-key",
        OPENAI_API_KEY="injected-openai-key",
        GOOGLE_API_KEY="injected-google-key",
    )
    monkeypatch.setattr("src.api.llm_client.get_llm_settings", lambda: fake_settings)

    from src.api.llm_client import get_client

    get_client()

    # Provider credentials stay request-scoped; client construction has no
    # process-wide environment side effects.
    assert os.environ.get("OPENROUTER_API_KEY") is None
    assert os.environ.get("ANTHROPIC_API_KEY") is None
    assert os.environ.get("OPENAI_API_KEY") is None
    assert os.environ.get("GOOGLE_API_KEY") is None
    assert os.environ.get("OR_SITE_URL") != fake_settings.OR_SITE_URL
    assert os.environ.get("OR_APP_NAME") != fake_settings.OR_APP_NAME

    reset_llm_singletons()


def test_get_client_is_singleton(monkeypatch: pytest.MonkeyPatch):
    """get_client() returns the same instance across calls."""
    reset_llm_singletons()
    monkeypatch.setattr("src.api.llm_client.get_llm_settings", lambda: make_settings())

    from src.api.llm_client import get_client

    a = get_client()
    b = get_client()
    assert a is b

    reset_llm_singletons()
