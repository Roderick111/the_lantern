"""Session token refresh preserves player_id after expiry."""

import time

from src.api.auth import TOKEN_EXPIRY_SECONDS, mint_token, verify_token


def test_verify_token_rejects_expired_without_allow_expired() -> None:
    """Expired v1 tokens are rejected in normal auth path."""
    player_id = "player_refresh_test"
    token = mint_token(player_id)

    # Simulate expiry by patching is not needed — mint fresh then verify with allow_expired=False
    # after time travel. Instead decode and re-mint logic: use verify with allow_expired after
    # we craft an expired token via internal claims (integration via mint + manual exp in past).

    parts = token.split(".")
    assert len(parts) == 3
    ver, b64, sig = parts


    import hmac
    from hashlib import sha256

    from src.api.auth import _decode_claims, _encode_claims, _get_secret

    claims = _decode_claims(b64)
    claims["exp"] = int(time.time()) - 10
    claims["iat"] = int(time.time()) - TOKEN_EXPIRY_SECONDS - 10
    new_b64 = _encode_claims(claims)
    payload = f"{ver}.{new_b64}"
    new_sig = hmac.new(_get_secret(), payload.encode("utf-8"), sha256).hexdigest()
    expired_token = f"{payload}.{new_sig}"

    assert verify_token(expired_token) is None
    assert verify_token(expired_token, allow_expired=True) == player_id


def test_create_session_reuses_player_id_with_expired_token() -> None:
    """POST /api/session accepts recently expired token for refresh."""
    from httpx import ASGITransport, AsyncClient

    from src.main import app

    player_id = "session_refresh_player"
    token = mint_token(player_id)

    parts = token.split(".")
    ver, b64, sig = parts

    import hmac
    import time
    from hashlib import sha256

    from src.api.auth import _decode_claims, _encode_claims, _get_secret

    claims = _decode_claims(b64)
    claims["exp"] = int(time.time()) - 60
    new_b64 = _encode_claims(claims)
    payload = f"{ver}.{new_b64}"
    new_sig = hmac.new(_get_secret(), payload.encode("utf-8"), sha256).hexdigest()
    expired_token = f"{payload}.{new_sig}"

    async def _run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/session",
                json={
                    "existing_player_id": player_id,
                    "current_token": expired_token,
                },
            )
            assert r.status_code == 200
            data = r.json()
            assert data["player_id"] == player_id
            assert verify_token(data["token"]) == player_id

    import asyncio

    asyncio.run(_run())
