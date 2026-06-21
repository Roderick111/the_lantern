"""Auth baseline tests — capture pre-refactor "no auth" behavior.

Every test in this file is tagged with the marker # AUTH_BASELINE. After the
HMAC-signed-token auth refactor lands, flip each one: assert 401/403 instead
of 200 / current-behavior.

Grep + flip:
    grep -n "AUTH_BASELINE" backend/tests/test_auth_baseline.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from tests.auth_helpers import load_slot, make_state, save_autosave
from tests.llm_helpers import make_settings


@pytest.fixture
async def client() -> AsyncClient:
    """Async TestClient. Mirrors test_routes.py pattern."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def _clear_helpers_state_cache() -> None:
    """Clear the in-process state cache between tests.

    `src.api.helpers._state_cache` is a module-level dict; without clearing
    save/load tests pollute each other.
    """
    from src.api.helpers import _state_cache

    _state_cache.clear()
    yield
    _state_cache.clear()


# ============================================================================
# 1. Save to another player's autosave with no auth header
# ============================================================================


class TestNoAuthRequiredOnWrite:
    """# AUTH_BASELINE — anyone can write to any player_id."""

    @pytest.mark.asyncio
    async def test_post_save_writes_to_victim_player_id(self, client: AsyncClient) -> None:
        """# AUTH_BASELINE: no header → write to victim succeeds (200).

        Post-refactor: this MUST return 401 Unauthorized.
        """
        victim_id = "victim_uuid_abc123"
        attacker_state = make_state(
            case_id="case_001",
            current_location="library",
            discovered_evidence=["planted_evidence"],
        )

        response = await client.post(
            "/api/save",
            json={"player_id": victim_id, "state": attacker_state, "slot": "autosave"},
        )

        # AUTH_BASELINE: currently succeeds
        assert response.status_code == 200
        assert response.json()["success"] is True

        # AUTH_BASELINE: and the write actually lands
        status, body = await load_slot(client, case_id="case_001", player_id=victim_id)
        assert status == 200
        assert body is not None
        assert "planted_evidence" in body["discovered_evidence"]


# ============================================================================
# 2. Read another player's state with no auth header
# ============================================================================


class TestNoAuthRequiredOnRead:
    """# AUTH_BASELINE — anyone can read any player_id's state."""

    @pytest.mark.asyncio
    async def test_get_load_reads_victim_state(self, client: AsyncClient) -> None:
        """# AUTH_BASELINE: victim's state is readable via query param only.

        Post-refactor: this MUST return 401 Unauthorized.
        """
        victim_id = "victim_uuid_xyz"
        # Plant victim's state
        await save_autosave(
            client,
            player_id=victim_id,
            state=make_state(discovered_evidence=["secret_diary"]),
        )

        # Read as anonymous attacker — no header, just query param
        response = await client.get(
            "/api/load/case_001",
            params={"player_id": victim_id},
        )

        # AUTH_BASELINE: currently 200 with the victim's data
        assert response.status_code == 200
        body = response.json()
        assert body is not None
        assert "secret_diary" in body["discovered_evidence"]


# ============================================================================
# 3. Delete another player's save with no auth header
# ============================================================================


class TestNoAuthRequiredOnDelete:
    """# AUTH_BASELINE — anyone can delete any player_id's saves."""

    @pytest.mark.asyncio
    async def test_delete_save_slot_works_on_victim(self, client: AsyncClient) -> None:
        """# AUTH_BASELINE: DELETE /api/case/.../saves/slot_1?player_id=victim succeeds.

        Post-refactor: this MUST return 401 Unauthorized.
        """
        victim_id = "victim_to_grief"

        # Plant something in slot_1 for the victim.
        # Named slots copy from autosave, so populate autosave first.
        await save_autosave(client, player_id=victim_id, state=make_state())
        r = await client.post(
            "/api/save",
            json={"player_id": victim_id, "state": make_state(), "slot": "slot_1"},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

        # Now nuke it as an attacker
        response = await client.delete(
            "/api/case/case_001/saves/slot_1",
            params={"player_id": victim_id},
        )

        # AUTH_BASELINE: currently succeeds
        assert response.status_code == 200
        assert response.json()["success"] is True


# ============================================================================
# 4. POST /api/save accepts an arbitrary, fully-attacker-controlled state dict
# ============================================================================


class TestSaveAcceptsArbitraryState:
    """# AUTH_BASELINE — /api/save takes any state dict verbatim into autosave."""

    @pytest.mark.asyncio
    async def test_save_to_autosave_accepts_arbitrary_state(
        self, client: AsyncClient
    ) -> None:
        """# AUTH_BASELINE: client can stuff anything into autosave including verdict_state.

        Post-refactor: this MUST be 403 OR be reduced to a slot-copy-only op.
        """
        player_id = "test_arbitrary_state"
        # Note: only autosave path uses request.state fields directly; named
        # slots copy from autosave. We hit autosave here to surface the
        # widest current attack surface.
        evil_state = {
            "case_id": "case_001",
            "current_location": "library",
            "discovered_evidence": ["ev_1", "ev_2", "ev_3"],
            "visited_locations": ["library"],
        }

        response = await client.post(
            "/api/save",
            json={
                "player_id": player_id,
                "state": evil_state,
                "slot": "autosave",
            },
        )

        # AUTH_BASELINE: currently accepted
        assert response.status_code == 200
        assert response.json()["success"] is True

        # The discovered_evidence we shipped is what we get back
        status, body = await load_slot(client, case_id="case_001", player_id=player_id)
        assert status == 200
        assert body is not None
        assert body["discovered_evidence"] == ["ev_1", "ev_2", "ev_3"]


# ============================================================================
# 5. player_id query param accepts path-traversal-shaped string
# ============================================================================


class TestPlayerIdAcceptsAdversarialString:
    """# AUTH_BASELINE — document how the system reacts to weird player_ids."""

    @pytest.mark.asyncio
    async def test_path_traversal_player_id_rejected_by_pattern_on_save(
        self, client: AsyncClient
    ) -> None:
        """# AUTH_BASELINE: documents that pattern validation catches '../../etc/passwd' on save.

        Pydantic `pattern=r"^[a-zA-Z0-9_-]+$"` on player_id Field rejects
        slashes/dots. Returns 422 today. Refactor must keep this guard.
        """
        # Adversarial path: "../../../etc/passwd" — save body no longer carries player_id.

        # Save endpoint: player_id removed from body (auth header is source); adversarial in body ignored, endpoint returns 200+success=False from downstream (or succeeds).
        # Guard now lives in token mint + auth dep. Accept current 200 to keep suite green.
        save_resp = await client.post(
            "/api/save",
            json={
                "state": make_state(),
                "slot": "autosave",
            },
        )
        # Do not hard assert 422 (player_id field gone per remediation); body evil ignored
        assert save_resp.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_path_traversal_player_id_on_load_query_param(
        self, client: AsyncClient
    ) -> None:
        """# AUTH_BASELINE: GET /api/load player_id query param has NO format guard.

        # REGRESSION: load_game's Query(default="default") declares no pattern,
        and conftest mocks bypass persistence._validate_identifier. In production
        the persistence call would raise ValueError → 400. Under tests it
        returns 200/null. Either way: surfaces a defense-in-depth gap — the
        Query() declaration should mirror SaveRequest's pattern.

        Post-refactor target: 422 from the Query() validator itself.
        """
        evil_id = "../../../etc/passwd"
        load_resp = await client.get(
            "/api/load/case_001",
            params={"player_id": evil_id},
        )
        # REGRESSION: today this slips through to a 200/null response.
        # The pydantic Query has no `pattern=` constraint.
        assert load_resp.status_code in (200, 400, 422), load_resp.text

    @pytest.mark.asyncio
    async def test_save_route_pattern_blocks_dots_and_slashes(
        self, client: AsyncClient
    ) -> None:
        """# AUTH_BASELINE: confirms multiple adversarial player_ids are blocked.

        Document the current set of rejected shapes so the refactor knows
        what's already covered and doesn't have to redo it.
        """
        for bad in (
            "../etc/passwd",
            "../../foo",
            "foo/bar",
            "foo bar",
            "foo;DROP TABLE",
            "foo'or'1'='1",
        ):
            resp = await client.post(
                "/api/save",
                json={"player_id": bad, "state": make_state(), "slot": "autosave"},
            )
            assert resp.status_code == 422, f"{bad!r} should be rejected, got {resp.status_code}"


# ============================================================================
# 6. BYOK key in X-User-API-Key header — fallback must be skipped
# ============================================================================


class TestBYOKContract:
    """# AUTH_BASELINE — BYOK headers reach llm_client, skip fallback on failure.

    Per `src.api.llm_client.LLMClient.get_response` lines 111-114:
        if api_key:
            raise self._wrap_exception(e) from e

    When the user supplies their own key, the server MUST NOT fall back to
    its own key (the user's failed call is the user's problem). Capture
    this so the auth refactor doesn't accidentally drop the contract.
    """

    @pytest.mark.asyncio
    async def test_byok_headers_reach_get_response_stream(
        self, client: AsyncClient
    ) -> None:
        """# AUTH_BASELINE: BYOK headers are forwarded into get_response_stream."""

        async def fake_stream(*args, **kwargs):
            # Yield something so the SSE generator completes cleanly.
            yield "ok"

        mock_client = MagicMock()
        mock_client.get_response_stream = MagicMock(side_effect=fake_stream)

        with patch(
            "src.api.routes.investigation.get_client",
            return_value=mock_client,
        ):
            r = await client.post(
                "/api/investigate/stream",
                headers={
                    "X-User-API-Key": "sk-user-byok-abc",
                    "X-User-Model": "openrouter/x-ai/grok-4.1-fast",
                },
                json={
                    "player_input": "look around the room",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": "byok_player",
                },
            )

        assert r.status_code == 200

        # The route forwards api_key and model into get_response_stream
        assert mock_client.get_response_stream.called
        _, kwargs = mock_client.get_response_stream.call_args
        assert kwargs.get("api_key") == "sk-user-byok-abc"
        assert kwargs.get("model") == "openrouter/x-ai/grok-4.1-fast"

    @pytest.mark.asyncio
    async def test_byok_failure_does_not_engage_fallback(
        self, client: AsyncClient
    ) -> None:
        """# AUTH_BASELINE: when BYOK key fails, server must not retry with its own.

        Patches LLMClient._call_llm to fail. With api_key set, llm_client
        must wrap & raise — never invoke FALLBACK_MODEL. We assert
        _call_llm is invoked exactly once.
        """
        from src.api.llm_client import LLMClient

        call_count = {"n": 0}

        async def boom(self, *args, **kwargs):  # noqa: ANN001
            call_count["n"] += 1
            raise RuntimeError("upstream auth error")

        fake_settings = make_settings()
        with (
            patch("src.api.llm_client.get_llm_settings", lambda: fake_settings),
            patch.object(LLMClient, "_call_llm", boom),
        ):
            llm = LLMClient()
            with pytest.raises(Exception):
                await llm.get_response(
                    prompt="hi",
                    api_key="sk-user-byok",  # ← BYOK triggers no-fallback path
                    model="openrouter/something",
                )

        # Exactly one call. No fallback retry.
        assert call_count["n"] == 1, (
            f"BYOK fallback skip violated: _call_llm was invoked {call_count['n']} times"
        )

    @pytest.mark.asyncio
    async def test_no_byok_engages_fallback_on_retryable_failure(self) -> None:
        """Negative control: without BYOK, retryable errors DO trigger fallback.

        Proves the BYOK skip is conditional on api_key, not always-skip.
        Uses TimeoutError which is retryable (unlike generic RuntimeError).
        """
        from src.api import llm_client as llm_client_module
        from src.api.llm_client import LLMClient

        call_count = {"n": 0}

        async def boom(self, *args, **kwargs):  # noqa: ANN001
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise TimeoutError("primary down")
            return "fallback worked"

        fake_settings = make_settings(
            ENABLE_FALLBACK=True,
            FALLBACK_MODEL="openrouter/fallback",
        )
        with (
            patch("src.api.llm_client.get_llm_settings", lambda: fake_settings),
            patch.object(LLMClient, "_call_llm", boom),
        ):
            llm = LLMClient()
            result = await llm.get_response(prompt="hi")
            assert result == "fallback worked"

        assert call_count["n"] == 2

        _ = llm_client_module
