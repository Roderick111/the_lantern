"""Anonymous session bootstrap endpoint.

Issues a signed player token. Public — no auth required. Frontend calls this on
first load (or whenever localStorage lacks a token) and stores the result.

Hardened: existing_player_id is only honored when accompanied by a current_token
that verifies ownership of the same player_id. Otherwise fresh UUID is issued
to prevent arbitrary player ID takeover (IDOR).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.api.auth import mint_token, new_player_id, verify_token
from src.api.rate_limit import SESSION_RATE, limiter

router = APIRouter()


class SessionRequest(BaseModel):
    """Optional existing player_id to mint a token for (legacy migration only).

    current_token: if supplied and verifies to existing_player_id, reuse is allowed.
    Without valid proof, existing_player_id is ignored and fresh id issued.
    """

    existing_player_id: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9_-]+$",
        max_length=64,
        description="Pre-token player_id from localStorage — preserves existing saves (restricted).",
    )
    current_token: str | None = Field(
        default=None,
        description="Current valid token proving ownership for reuse of existing_player_id.",
    )


class SessionResponse(BaseModel):
    player_id: str
    token: str


@router.post("/session", response_model=SessionResponse)
@limiter.limit(SESSION_RATE)
async def create_session(request: Request, body: SessionRequest) -> SessionResponse:
    """Mint a signed token (with iat/exp claims). Reuses existing only with proof."""
    player_id: str | None = None
    if body.current_token:
        verified = verify_token(
            body.current_token, allow_legacy=True
        ) or verify_token(body.current_token, allow_expired=True, allow_legacy=True)
        if verified:
            if body.existing_player_id is None or verified == body.existing_player_id:
                player_id = verified
    if player_id is None:
        # Hardened path: ignore unproven existing_player_id, always fresh
        player_id = new_player_id()
    return SessionResponse(player_id=player_id, token=mint_token(player_id))
