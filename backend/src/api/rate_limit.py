"""Rate limiting configuration."""

import os

from slowapi import Limiter
from starlette.requests import Request


def _trusted_proxy_enabled() -> bool:
    """Only trust X-Forwarded-For when explicitly behind a configured reverse proxy."""
    return os.environ.get("TRUSTED_PROXY", "").lower() in ("1", "true", "yes")


def _client_ip(request: Request) -> str:
    """Resolve client IP — honors X-Forwarded-For only when TRUSTED_PROXY is set."""
    if _trusted_proxy_enabled():
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit_key(request: Request) -> str:
    """Key by authenticated player_id when available, else client IP."""
    player_id = getattr(request.state, "player_id", None)
    if player_id:
        return f"player:{player_id}"
    return _client_ip(request)


limiter = Limiter(key_func=_rate_limit_key)

LLM_RATE = "10/minute"
VERIFY_KEY_RATE = "5/minute"
STANDARD_RATE = "100/minute"
SESSION_RATE = "20/minute"
SAVE_LOAD_RATE = "60/minute"
