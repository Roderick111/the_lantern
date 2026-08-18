"""Shared API error mapping and redaction helpers."""

from __future__ import annotations

import re

from fastapi import HTTPException

from src.api.llm_client import (
    AuthenticationFailedError,
    EmptyLLMResponseError,
    LLMClientError,
    LLMConnectionError,
    LLMTimeoutError,
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


def llm_stream_error_payload(
    exc: Exception,
    *,
    request_id: str | None = None,
    partial: bool = False,
) -> dict[str, object]:
    """SSE error payload with stable code and retry semantics."""
    code = "llm_connection"
    message = "Connection failed — try again."
    retryable = True
    if isinstance(exc, AuthenticationFailedError):
        code, message, retryable = "llm_auth", "Check your API key in Settings.", False
    elif isinstance(exc, RateLimitExceededError):
        code, message = "llm_rate_limit", "Rate limited — wait and try again."
    elif isinstance(exc, UnsupportedModelError):
        code, message, retryable = "llm_model", str(exc), False
    elif isinstance(exc, EmptyLLMResponseError):
        code, message = "llm_empty", "No response received — try again."
    elif isinstance(exc, LLMTimeoutError) or isinstance(exc, TimeoutError):
        code, message = "llm_timeout", "Response took too long — try again."
    elif isinstance(exc, LLMConnectionError):
        code, message = "llm_connection", "Connection failed — try again."
    elif isinstance(exc, LLMClientError):
        code, message = "llm_connection", "LLM service unavailable — try again."
    payload: dict[str, object] = {
        "error": message,
        "code": code,
        "retryable": retryable,
        "partial": partial,
    }
    if request_id is not None:
        payload["request_id"] = request_id
    return payload
