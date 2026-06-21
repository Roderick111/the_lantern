"""Shared API error mapping and redaction helpers."""

from __future__ import annotations

import re

from fastapi import HTTPException

from src.api.llm_client import (
    AuthenticationFailedError,
    LLMClientError,
    RateLimitExceededError,
    UnsupportedModelError,
)

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.I),
)


def redact_secrets(text: str, *, limit: int = 200) -> str:
    """Strip likely API key fragments before logging or returning to clients."""
    out = text[:limit]
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out


def llm_http_exception(exc: Exception) -> HTTPException:
    """Map LLM client errors to actionable HTTP responses."""
    if isinstance(exc, AuthenticationFailedError):
        return HTTPException(
            status_code=401,
            detail="LLM authentication failed. Check your API key in Settings.",
        )
    if isinstance(exc, RateLimitExceededError):
        return HTTPException(
            status_code=429,
            detail="LLM rate limit exceeded. Wait a moment and try again.",
        )
    if isinstance(exc, UnsupportedModelError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, LLMClientError):
        return HTTPException(
            status_code=503,
            detail="LLM service temporarily unavailable.",
        )
    return HTTPException(status_code=503, detail="LLM service temporarily unavailable.")


def llm_stream_error_payload(exc: Exception) -> dict[str, str]:
    """SSE/JSON error payload with stable codes for the frontend."""
    if isinstance(exc, AuthenticationFailedError):
        return {"error": "Check your API key in Settings.", "code": "llm_auth"}
    if isinstance(exc, RateLimitExceededError):
        return {"error": "Rate limited — wait and try again.", "code": "llm_rate_limit"}
    if isinstance(exc, UnsupportedModelError):
        return {"error": str(exc), "code": "llm_model"}
    return {"error": "An error occurred while processing your request.", "code": "llm_error"}