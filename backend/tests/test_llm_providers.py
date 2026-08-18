"""Multi-provider regression tests for LLMClient.

The client itself doesn't gate on provider — it just passes whatever model
string `settings.DEFAULT_MODEL` holds through to LiteLLM. These tests pin
that behavior so the upcoming refactor (which may introduce provider routing,
header injection, key selection) doesn't regress.

Coverage per provider: anthropic, openrouter, openai, google.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

from src.config.llm_settings import LLMProvider
from tests.llm_helpers import (
    SequentialAcompletion,
    make_fake_response,
    make_settings,
    reset_llm_singletons,
)

# ---------------------------------------------------------------------------
# Per-provider settings fixtures
# ---------------------------------------------------------------------------


def _build_client(monkeypatch: pytest.MonkeyPatch, **overrides):
    """Build a fresh LLMClient with the given settings overrides."""
    reset_llm_singletons()
    fake_settings = make_settings(**overrides)
    monkeypatch.setattr(
        "src.api.llm_client.get_llm_settings", lambda: fake_settings
    )
    from src.api.llm_client import LLMClient

    return LLMClient(), fake_settings


# ---------------------------------------------------------------------------
# Provider: anthropic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_anthropic_passes_anthropic_model(
    monkeypatch: pytest.MonkeyPatch,
):
    client, settings = _build_client(
        monkeypatch,
        DEFAULT_LLM_PROVIDER=LLMProvider.ANTHROPIC,
        ANTHROPIC_API_KEY="anthropic-key",
        OPENROUTER_API_KEY="",
        DEFAULT_MODEL="anthropic/claude-sonnet-4-5",
        FALLBACK_MODEL="anthropic/claude-haiku-4-5",
    )

    fake = SequentialAcompletion([make_fake_response("ok")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        await client.get_response(prompt="hi")

    assert fake.calls[0]["model"].startswith("anthropic/"), (
        f"expected anthropic/* model, got {fake.calls[0]['model']}"
    )
    assert fake.calls[0]["model"] == settings.DEFAULT_MODEL

    reset_llm_singletons()


@pytest.mark.asyncio
async def test_provider_anthropic_env_setup(
    monkeypatch: pytest.MonkeyPatch,
):
    """Anthropic key stays request-scoped instead of mutating process env."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _build_client(
        monkeypatch,
        DEFAULT_LLM_PROVIDER=LLMProvider.ANTHROPIC,
        ANTHROPIC_API_KEY="anthropic-specific-key",
    )

    assert os.environ.get("ANTHROPIC_API_KEY") is None
    reset_llm_singletons()


# ---------------------------------------------------------------------------
# Provider: openrouter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_openrouter_passes_openrouter_model(
    monkeypatch: pytest.MonkeyPatch,
):
    client, settings = _build_client(
        monkeypatch,
        DEFAULT_LLM_PROVIDER=LLMProvider.OPENROUTER,
        OPENROUTER_API_KEY="or-key",
        DEFAULT_MODEL="openrouter/x-ai/grok-4.1-fast",
        FALLBACK_MODEL="openrouter/google/gemma-2-9b-it",
    )

    fake = SequentialAcompletion([make_fake_response("ok")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        await client.get_response(prompt="hi")

    assert fake.calls[0]["model"].startswith("openrouter/")
    assert fake.calls[0]["model"] == settings.DEFAULT_MODEL

    reset_llm_singletons()


@pytest.mark.asyncio
async def test_provider_openrouter_metadata_headers_propagate(
    monkeypatch: pytest.MonkeyPatch,
):
    """OpenRouter metadata does not leak through process-wide env vars."""
    # Clear so we can verify writes
    for k in ("OPENROUTER_API_KEY", "OR_SITE_URL", "OR_APP_NAME"):
        monkeypatch.delenv(k, raising=False)

    _build_client(
        monkeypatch,
        DEFAULT_LLM_PROVIDER=LLMProvider.OPENROUTER,
        OPENROUTER_API_KEY="or-key-xyz",
        OR_SITE_URL="https://my-test-app.example",
        OR_APP_NAME="MyTestApp",
    )

    assert os.environ.get("OPENROUTER_API_KEY") is None
    assert os.environ.get("OR_SITE_URL") != "https://my-test-app.example"
    assert os.environ.get("OR_APP_NAME") != "MyTestApp"

    reset_llm_singletons()


# ---------------------------------------------------------------------------
# Provider: openai
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_openai_passes_openai_model(
    monkeypatch: pytest.MonkeyPatch,
):
    client, settings = _build_client(
        monkeypatch,
        DEFAULT_LLM_PROVIDER=LLMProvider.OPENAI,
        OPENAI_API_KEY="openai-key",
        OPENROUTER_API_KEY="",
        DEFAULT_MODEL="openai/gpt-4o-mini",
        FALLBACK_MODEL="openai/gpt-4o",
    )

    fake = SequentialAcompletion([make_fake_response("ok")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        await client.get_response(prompt="hi")

    assert fake.calls[0]["model"].startswith("openai/")
    assert fake.calls[0]["model"] == settings.DEFAULT_MODEL

    reset_llm_singletons()


@pytest.mark.asyncio
async def test_provider_openai_env_setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _build_client(
        monkeypatch,
        DEFAULT_LLM_PROVIDER=LLMProvider.OPENAI,
        OPENAI_API_KEY="openai-specific-key",
    )

    assert os.environ.get("OPENAI_API_KEY") is None
    reset_llm_singletons()


# ---------------------------------------------------------------------------
# Provider: google
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_google_passes_gemini_model(
    monkeypatch: pytest.MonkeyPatch,
):
    """Google provider uses `gemini/*` model namespace (per llm_config _VERIFY_MODELS)."""
    client, settings = _build_client(
        monkeypatch,
        DEFAULT_LLM_PROVIDER=LLMProvider.GOOGLE,
        GOOGLE_API_KEY="google-key",
        OPENROUTER_API_KEY="",
        DEFAULT_MODEL="gemini/gemini-2.0-flash",
        FALLBACK_MODEL="gemini/gemini-1.5-flash",
    )

    fake = SequentialAcompletion([make_fake_response("ok")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        await client.get_response(prompt="hi")

    # The model string is whatever DEFAULT_MODEL says — pin it
    assert fake.calls[0]["model"] == settings.DEFAULT_MODEL
    assert "gemini" in fake.calls[0]["model"]

    reset_llm_singletons()


@pytest.mark.asyncio
async def test_provider_google_env_setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    _build_client(
        monkeypatch,
        DEFAULT_LLM_PROVIDER=LLMProvider.GOOGLE,
        GOOGLE_API_KEY="google-specific-key",
    )

    assert os.environ.get("GOOGLE_API_KEY") is None
    reset_llm_singletons()


# ---------------------------------------------------------------------------
# Cross-provider — fallback model is honored regardless of provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_model_used_across_providers(monkeypatch: pytest.MonkeyPatch):
    """Fallback target is the configured FALLBACK_MODEL regardless of primary."""
    client, settings = _build_client(
        monkeypatch,
        DEFAULT_LLM_PROVIDER=LLMProvider.ANTHROPIC,
        ANTHROPIC_API_KEY="anthropic-key",
        OPENROUTER_API_KEY="or-key",
        DEFAULT_MODEL="anthropic/claude-sonnet-4-5",
        FALLBACK_MODEL="openrouter/google/gemma-2-9b-it",
    )

    fake = SequentialAcompletion([
        TimeoutError("primary timed out"),
        make_fake_response("from-fallback"),
    ])

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        result = await client.get_response(prompt="hi")

    assert result == "from-fallback"
    assert fake.calls[0]["model"] == "anthropic/claude-sonnet-4-5"
    # Fallback can cross provider boundary
    assert fake.calls[1]["model"] == "openrouter/google/gemma-2-9b-it"

    reset_llm_singletons()


# ---------------------------------------------------------------------------
# Model override (BYOK) bypasses settings.DEFAULT_MODEL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_byok_model_override_wins_over_settings(monkeypatch: pytest.MonkeyPatch):
    """When caller supplies `model=`, it overrides settings.DEFAULT_MODEL."""
    client, _ = _build_client(
        monkeypatch,
        DEFAULT_LLM_PROVIDER=LLMProvider.OPENROUTER,
        DEFAULT_MODEL="openrouter/server-default",
    )

    fake = SequentialAcompletion([make_fake_response("ok")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        await client.get_response(
            prompt="hi",
            api_key="user-key",
            model="anthropic/user-picked",
        )

    assert fake.calls[0]["model"] == "anthropic/user-picked"

    reset_llm_singletons()
