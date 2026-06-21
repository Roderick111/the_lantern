"""HMAC-signed player tokens for anonymous session auth.

Token format (v1): ``v1.<base64url_json_claims>.<hmac_sha256_hex>``.

Claims: pid (player_id), iat (issued at), exp (expiry 30 days), optional jti.

Legacy tokens (player_id.sig) continue to verify for backward compat (no expiry).

Players never log in — instead the server mints a UUID + signed token on first
visit (`POST /api/session`). The token proves the client owns the player_id;
without it, requests can't read or mutate that player's saves.
"""

from __future__ import annotations

import base64
import hmac
import json
import os
import time
import uuid
from hashlib import sha256

_MIN_SECRET_LEN = 32

TOKEN_EXPIRY_SECONDS = 30 * 24 * 3600  # 30 days


def _get_secret() -> bytes:
    """Return the configured HMAC secret as bytes. Raises if missing or weak."""
    secret = os.environ.get("PLAYER_TOKEN_SECRET", "")
    if len(secret) < _MIN_SECRET_LEN:
        raise RuntimeError(
            f"PLAYER_TOKEN_SECRET must be set and at least {_MIN_SECRET_LEN} chars. "
            "Generate one with: python -c 'import secrets;print(secrets.token_hex(32))'"
        )
    return secret.encode("utf-8")


def _encode_claims(claims: dict) -> str:
    """Encode claims dict to urlsafe base64 without padding."""
    data = json.dumps(claims, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _decode_claims(b64: str) -> dict:
    """Decode urlsafe base64 claims (add padding as needed)."""
    padding = "=" * ((4 - len(b64) % 4) % 4)
    data = base64.urlsafe_b64decode(b64 + padding)
    return json.loads(data)


def new_player_id() -> str:
    """Generate a fresh URL-safe player_id."""
    return uuid.uuid4().hex


def mint_token(player_id: str) -> str:
    """Mint a signed token for the given player_id. Includes iat + exp claims."""
    now = int(time.time())
    exp = now + TOKEN_EXPIRY_SECONDS
    claims = {
        "pid": player_id,
        "iat": now,
        "exp": exp,
        # jti omitted for simplicity; can add uuid4 for revocation later
    }
    b64 = _encode_claims(claims)
    payload = f"v1.{b64}"
    sig = hmac.new(_get_secret(), payload.encode("utf-8"), sha256).hexdigest()
    return f"{payload}.{sig}"


TOKEN_REFRESH_GRACE_SECONDS = 7 * 24 * 3600  # 7 days after expiry


def verify_token(token: str, *, allow_expired: bool = False) -> str | None:
    """Verify a signed token. Returns player_id if valid and not expired, None otherwise.

    Supports legacy (player_id.sig) and v1 (v1.b64.sig) formats.

    When ``allow_expired`` is True, v1 tokens with valid HMAC but past ``exp`` are
    accepted if within ``TOKEN_REFRESH_GRACE_SECONDS`` (session refresh only).
    """
    if not token or "." not in token:
        return None
    parts = token.split(".")
    if len(parts) == 2:
        # Legacy format: no claims/expiry
        player_id, sig = parts
        if not player_id or not sig:
            return None
        expected = hmac.new(_get_secret(), player_id.encode("utf-8"), sha256).hexdigest()
        if hmac.compare_digest(sig, expected):
            return player_id
        return None
    if len(parts) != 3:
        return None
    ver, b64, sig = parts
    if ver != "v1":
        return None
    payload = f"{ver}.{b64}"
    expected = hmac.new(_get_secret(), payload.encode("utf-8"), sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        claims = _decode_claims(b64)
        player_id = claims.get("pid")
        if not player_id:
            return None
        exp = claims.get("exp")
        if exp is not None:
            now = int(time.time())
            if now > int(exp):
                if not allow_expired or now > int(exp) + TOKEN_REFRESH_GRACE_SECONDS:
                    return None
        return player_id
    except Exception:
        return None
