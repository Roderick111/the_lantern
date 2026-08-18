"""FastAPI dependencies for request-scoped configuration."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, Request

from src.api.auth import verify_token


@dataclass
class UserLLMConfig:
    """User-provided LLM configuration from request headers (BYOK)."""

    api_key: str | None = None
    model: str | None = None


def get_user_llm_config(
    x_user_api_key: str | None = Header(None),
    x_user_model: str | None = Header(None),
) -> UserLLMConfig:
    """Extract user LLM config from request headers."""
    return UserLLMConfig(api_key=x_user_api_key, model=x_user_model)


def get_authenticated_player_id(
    request: Request,
    x_player_token: str | None = Header(default=None),
) -> str:
    """Verify ``X-Player-Token`` header and return the player_id.

    Raises 401 if missing or invalid. Clients bootstrap a token via
    ``POST /api/session`` (public endpoint).
    """
    if not x_player_token:
        raise HTTPException(status_code=401, detail="X-Player-Token header required")
    player_id = verify_token(x_player_token)
    if player_id is None:
        raise HTTPException(status_code=401, detail="Invalid player token")
    request.state.player_id = player_id
    return player_id
