"""BYOK (Bring Your Own Key) regression tests + verify_api_key behavior.

Captures the current behavior of:
  - BYOK paths skipping fallback unconditionally (correct)
  - verify_api_key returning raw upstream exception strings (LEAK — REGRESSION)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from litellm.exceptions import AuthenticationError

from tests.llm_helpers import (
    SequentialAcompletion,
    make_fake_response,
    make_settings,
    reset_llm_singletons,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_client(monkeypatch: pytest.MonkeyPatch):
    reset_llm_singletons()
    fake_settings = make_settings()
    monkeypatch.setattr(
        "src.api.llm_client.get_llm_settings", lambda: fake_settings
    )
    from src.api.llm_client import LLMClient

    client = LLMClient()
    yield client, fake_settings
    reset_llm_singletons()


# ---------------------------------------------------------------------------
# BYOK — non-streaming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_byok_skips_fallback_on_any_exception(fresh_client):
    """User-provided api_key + model → no fallback on error (llm_client.py:111-114)."""
    client, _ = fresh_client

    from src.api.llm_client import LLMClientError

    fake = SequentialAcompletion([Exception("user key invalid"), make_fake_response("never")])

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        with pytest.raises(LLMClientError, match="user key invalid"):
            await client.get_response(
                prompt="hi",
                api_key="user-key",
                model="user/model",
            )

    # Crucially: fallback was NOT attempted
    assert len(fake.calls) == 1
    assert fake.calls[0]["model"] == "user/model"
    assert fake.calls[0]["api_key"] == "user-key"


@pytest.mark.asyncio
async def test_byok_propagates_auth_error(fresh_client):
    """BYOK + AuthenticationError → wrapped, not retried."""
    client, _ = fresh_client
    from src.api.llm_client import LLMClientError

    err = AuthenticationError(message="bad", model="user/model", llm_provider="openrouter")
    fake = SequentialAcompletion([err, make_fake_response("nope")])

    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        with pytest.raises(LLMClientError):
            await client.get_response(
                prompt="hi", api_key="user-key", model="user/model"
            )

    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_byok_passes_api_key_and_model_to_acompletion(fresh_client):
    """BYOK kwargs make it to LiteLLM acompletion verbatim."""
    client, _ = fresh_client

    fake = SequentialAcompletion([make_fake_response("ok")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        result = await client.get_response(
            prompt="hi", api_key="sk-user-123", model="user/special-model"
        )

    assert result == "ok"
    call = fake.calls[0]
    assert call["model"] == "user/special-model"
    assert call["api_key"] == "sk-user-123"


@pytest.mark.asyncio
async def test_byok_with_system_prompt_builds_messages(fresh_client):
    """System prompt prepended as first message when provided."""
    client, _ = fresh_client

    fake = SequentialAcompletion([make_fake_response("ok")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        await client.get_response(
            prompt="user-text",
            system="system-text",
            api_key="k",
            model="user/model",
        )

    messages = fake.calls[0]["messages"]
    assert messages[0] == {"role": "system", "content": "system-text"}
    assert messages[1] == {"role": "user", "content": "user-text"}


@pytest.mark.asyncio
async def test_no_byok_omits_api_key_kwarg(fresh_client):
    """Server-side path passes configured credential per request."""
    client, settings = fresh_client

    fake = SequentialAcompletion([make_fake_response("ok")])
    with patch("src.api.llm_client.acompletion", new=AsyncMock(side_effect=fake)):
        await client.get_response(prompt="hi")

    call = fake.calls[0]
    assert call["api_key"] == settings.OPENROUTER_API_KEY
    assert call["model"] == settings.DEFAULT_MODEL


# ---------------------------------------------------------------------------
# verify_api_key — the key-leak REGRESSION
# ---------------------------------------------------------------------------


@pytest.fixture
def test_client():
    """FastAPI TestClient with mocked persistence (per conftest)."""
    from fastapi.testclient import TestClient

    from src.main import app

    return TestClient(app)


def test_verify_api_key_happy_path(test_client):
    """Valid call → VerifyKeyResponse(valid=True, error=None)."""
    fake = AsyncMock(return_value=make_fake_response("hi"))

    with patch("litellm.acompletion", fake):
        response = test_client.post(
            "/api/llm/verify",
            json={"provider": "openrouter", "api_key": "sk-ok"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["error"] is None


def test_verify_api_key_unknown_provider_returns_friendly_error(test_client):
    """Unknown provider → valid=False with explicit message; no acompletion call."""
    fake = AsyncMock(return_value=make_fake_response("hi"))
    with patch("litellm.acompletion", fake):
        response = test_client.post(
            "/api/llm/verify",
            json={"provider": "totally-fake", "api_key": "k"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "Unknown provider" in data["error"]
    fake.assert_not_called()


def test_verify_api_key_does_not_leak_exception_details(test_client):
    """FIXED: error string is now sanitized — no key fragments or raw messages leak."""
    leaked_key_fragment = "sk-ant-abc123-SECRET"
    raw_msg = f"Invalid key '{leaked_key_fragment}' rejected by upstream"

    fake = AsyncMock(side_effect=Exception(raw_msg))
    with patch("litellm.acompletion", fake):
        response = test_client.post(
            "/api/llm/verify",
            json={"provider": "anthropic", "api_key": leaked_key_fragment},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert leaked_key_fragment not in data["error"]
    assert raw_msg not in data["error"]


def test_verify_api_key_auth_error_sanitized(test_client):
    """FIXED: AuthenticationError returns generic 'Invalid API key' message."""
    err = AuthenticationError(
        message="invalid api key sk-abc",
        model="anthropic/claude-haiku-4-5",
        llm_provider="anthropic",
    )
    fake = AsyncMock(side_effect=err)
    with patch("litellm.acompletion", fake):
        response = test_client.post(
            "/api/llm/verify",
            json={"provider": "anthropic", "api_key": "sk-abc"},
        )

    data = response.json()
    assert data["valid"] is False
    assert "sk-abc" not in data["error"]
    assert data["error"] == "Invalid API key"


def test_verify_api_key_uses_correct_test_model_per_provider(test_client):
    """`_VERIFY_MODELS` maps provider → cheap probe model."""
    expected = {
        "openrouter": "openrouter/google/gemini-2.0-flash-001",
        "anthropic": "anthropic/claude-haiku-4-5",
        "openai": "openai/gpt-4o-mini",
        "google": "gemini/gemini-2.0-flash",
    }
    for provider, model in expected.items():
        fake = AsyncMock(return_value=make_fake_response("hi"))
        with patch("litellm.acompletion", fake):
            response = test_client.post(
                "/api/llm/verify",
                json={"provider": provider, "api_key": "k"},
            )
        assert response.status_code == 200
        assert fake.call_args.kwargs["model"] == model, (
            f"provider {provider} should test with {model}"
        )


def test_verify_api_key_user_supplied_model_wins(test_client):
    """Caller can override the probe model."""
    fake = AsyncMock(return_value=make_fake_response("hi"))
    with patch("litellm.acompletion", fake):
        test_client.post(
            "/api/llm/verify",
            json={
                "provider": "anthropic",
                "api_key": "k",
                "model": "anthropic/claude-opus-4",
            },
        )

    assert fake.call_args.kwargs["model"] == "anthropic/claude-opus-4"
