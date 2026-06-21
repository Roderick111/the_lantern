"""Save-slot semantics tests.

Cover behavior that is currently undertested:
- autosave-on-every-action
- manual save = copy-from-autosave snapshot
- snapshot independence after further play
- empty / corrupt / malformed save handling
- VALID_SLOTS enforcement
- reset semantics (autosave gone, named slots preserved)

Markers:
- # REGRESSION — flags behavior that should likely change after refactor.
  Post-refactor, flip the assertion to the desired outcome.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from tests.auth_helpers import load_slot, make_state, save_autosave


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
# 7. Autosave continuously overwrites on every investigate action
# ============================================================================


class TestAutosaveOverwritesOnEveryAction:
    """Each /api/investigate call must rewrite autosave with the latest state."""

    @pytest.mark.asyncio
    async def test_three_sequential_investigates_update_autosave(
        self, client: AsyncClient
    ) -> None:
        from src.state.persistence import load_player_state

        player_id = "test_autosave_overwrite"

        responses = [
            "First action. [EVIDENCE: hidden_note]",
            "Second action. [EVIDENCE: frost_pattern]",
            "Third action. [EVIDENCE: melted_wax]",
        ]
        expected_evidence_at_step = [
            {"hidden_note"},
            {"hidden_note", "frost_pattern"},
            {"hidden_note", "frost_pattern", "melted_wax"},
        ]

        for narrator_text, expected in zip(responses, expected_evidence_at_step):
            with patch("src.api.routes.investigation.get_client") as mock_get_client:
                mock_llm = AsyncMock()
                mock_llm.get_response = AsyncMock(return_value=narrator_text)
                mock_get_client.return_value = mock_llm

                r = await client.post(
                    "/api/investigate",
                    json={
                        "player_input": "search the area",
                        "case_id": "case_001",
                        "location_id": "library",
                        "player_id": player_id,
                    },
                )
                assert r.status_code == 200

            # After each call, autosave reflects everything found so far.
            state = load_player_state("case_001", player_id, "autosave")
            assert state is not None
            assert set(state.discovered_evidence) >= expected, (
                f"After step expecting {expected}, autosave had {state.discovered_evidence}"
            )


# ============================================================================
# 8 & 9. Manual save snapshot semantics
# ============================================================================


class TestManualSaveSnapshot:
    """Named slots are immutable snapshots taken from autosave at save-time."""

    @pytest.mark.asyncio
    async def test_save_to_slot2_copies_autosave(self, client: AsyncClient) -> None:
        """slot_2 reflects autosave contents at save-time."""
        player_id = "test_slot2_copy"

        # Populate autosave
        await save_autosave(
            client,
            player_id=player_id,
            state=make_state(discovered_evidence=["ev_alpha", "ev_beta"]),
        )

        # Manual save into slot_2 — body.state is ignored for named slots;
        # contents come from autosave.
        r = await client.post(
            "/api/save",
            json={
                "player_id": player_id,
                "state": make_state(discovered_evidence=["ignored"]),
                "slot": "slot_2",
            },
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

        # Load slot_2 — should match autosave, not the request body.
        status, body = await load_slot(
            client, case_id="case_001", player_id=player_id, slot="slot_2"
        )
        assert status == 200
        assert body is not None
        assert set(body["discovered_evidence"]) == {"ev_alpha", "ev_beta"}

    @pytest.mark.asyncio
    async def test_slot2_snapshot_survives_further_autosave_mutation(
        self, client: AsyncClient
    ) -> None:
        """After snapshotting to slot_2, further play changes autosave but not slot_2.

        IMPORTANT side-effect: load_game(slot_2) currently COPIES slot_2 back
        into autosave (saves.py:128). So we must NOT load slot_2 mid-test;
        instead, read directly via persistence to verify the snapshot held.
        """
        from src.state.persistence import load_player_state

        player_id = "test_slot2_independence"

        # 1. Autosave state X
        await save_autosave(
            client,
            player_id=player_id,
            state=make_state(discovered_evidence=["ev_x1", "ev_x2"]),
        )

        # 2. Snapshot to slot_2
        r = await client.post(
            "/api/save",
            json={
                "player_id": player_id,
                "state": make_state(),
                "slot": "slot_2",
            },
        )
        assert r.status_code == 200

        # 3. Continue playing — autosave mutates
        await save_autosave(
            client,
            player_id=player_id,
            state=make_state(discovered_evidence=["ev_x1", "ev_x2", "ev_y3"]),
        )

        # 4. Read slot_2 directly from persistence (no copy-to-autosave side-effect).
        snapshot = load_player_state("case_001", player_id, "slot_2")
        assert snapshot is not None
        assert set(snapshot.discovered_evidence) == {"ev_x1", "ev_x2"}, (
            "slot_2 snapshot must NOT reflect post-snapshot autosave mutations"
        )

        # And autosave has the new state
        autosave = load_player_state("case_001", player_id, "autosave")
        assert autosave is not None
        assert "ev_y3" in autosave.discovered_evidence


# ============================================================================
# 10. Load slot_1 when empty
# ============================================================================


class TestLoadEmptySlot:
    """Loading an unpopulated slot — document current behavior."""

    @pytest.mark.asyncio
    async def test_load_empty_slot_returns_null(self, client: AsyncClient) -> None:
        """Current: returns 200 + null body (NOT 404).

        StateResponse is `StateResponse | None` and the route returns None
        when load_player_state returns None.
        """
        r = await client.get(
            "/api/load/case_001",
            params={"player_id": "fresh_player_never_saved", "slot": "slot_1"},
        )
        assert r.status_code == 200
        assert r.json() is None


# ============================================================================
# 11. Delete removes slot from list
# ============================================================================


class TestDeleteRemovesFromList:
    """DELETE /api/case/.../saves/{slot} → list no longer mentions that slot."""

    @pytest.mark.asyncio
    async def test_delete_slot1_removes_from_list(self, client: AsyncClient) -> None:
        player_id = "test_delete_listing"

        # Populate autosave first (named slots copy from autosave)
        await save_autosave(client, player_id=player_id, state=make_state())

        # Manual save to slot_1
        r = await client.post(
            "/api/save",
            json={"player_id": player_id, "state": make_state(), "slot": "slot_1"},
        )
        assert r.status_code == 200

        # List shows slot_1
        r = await client.get(
            "/api/case/case_001/saves/list",
            params={"player_id": player_id},
        )
        assert r.status_code == 200
        slots_before = {s["slot"] for s in r.json()["saves"]}
        assert "slot_1" in slots_before

        # Delete slot_1
        r = await client.delete(
            "/api/case/case_001/saves/slot_1",
            params={"player_id": player_id},
        )
        assert r.status_code == 200

        # List no longer shows slot_1
        r = await client.get(
            "/api/case/case_001/saves/list",
            params={"player_id": player_id},
        )
        assert r.status_code == 200
        slots_after = {s["slot"] for s in r.json()["saves"]}
        assert "slot_1" not in slots_after


# ============================================================================
# 12. Delete autosave — currently ALLOWED
# ============================================================================


class TestDeleteAutosaveBehavior:
    """# REGRESSION — autosave is deletable today.

    Current code: `delete_save_slot_endpoint` permits slot='autosave' (it's
    in `valid_slots`). UI is supposed to gate this but the backend does
    not. Document current behavior so the refactor can flip to 403.
    """

    @pytest.mark.asyncio
    async def test_delete_autosave_currently_succeeds(self, client: AsyncClient) -> None:
        """# REGRESSION: autosave deletion should likely be forbidden.

        Post-refactor target: 403 Forbidden.
        """
        player_id = "test_delete_autosave"

        await save_autosave(client, player_id=player_id, state=make_state())

        r = await client.delete(
            "/api/case/case_001/saves/autosave",
            params={"player_id": player_id},
        )

        # REGRESSION: currently allowed
        assert r.status_code == 200
        assert r.json()["success"] is True


# ============================================================================
# 13. Corrupt save row → load returns None silently
# ============================================================================


class TestCorruptSaveHandling:
    """Corrupt save rows surface as CorruptSaveError → HTTP 400 on load route."""

    @pytest.mark.asyncio
    async def test_corrupt_save_invalid_schema_via_route_returns_400(
        self, client: AsyncClient
    ) -> None:
        """Schema-invalid JSON dict → load route returns 400."""
        import json

        from src.state.persistence import _get_conn

        player_id = "test_corrupt_save"

        conn = _get_conn()
        conn.execute(
            "INSERT INTO saves (player_id, case_id, slot, state, updated_at) VALUES (?, ?, ?, ?, ?)",
            (
                player_id,
                "case_001",
                "autosave",
                json.dumps({"garbage": True, "x": 42}),
                "2026-06-20T12:00:00",
            ),
        )
        conn.commit()

        r = await client.get(
            "/api/load/case_001",
            params={"player_id": player_id, "slot": "autosave"},
        )

        assert r.status_code == 400, (
            f"Corrupt save should produce 400, got {r.status_code}: {r.text}"
        )

    @pytest.mark.asyncio
    async def test_corrupt_save_invalid_json_via_route_returns_400(
        self, client: AsyncClient
    ) -> None:
        """Non-JSON state TEXT → load route returns 400."""
        from src.state.persistence import _get_conn

        player_id = "test_corrupt_json"

        conn = _get_conn()
        conn.execute(
            "INSERT INTO saves (player_id, case_id, slot, state, updated_at) VALUES (?, ?, ?, ?, ?)",
            (player_id, "case_001", "autosave", "not-valid-json{{{", "2026-06-20T12:00:00"),
        )
        conn.commit()

        r = await client.get(
            "/api/load/case_001",
            params={"player_id": player_id, "slot": "autosave"},
        )

        assert r.status_code == 400

    def test_load_player_state_raises_corrupt_save_error_for_invalid_json(self) -> None:
        """load_player_state raises CorruptSaveError for invalid JSON blobs."""

        from src.state.persistence import CorruptSaveError, _get_conn, load_player_state

        player_id = "test_corrupt_persistence"

        conn = _get_conn()
        conn.execute(
            "INSERT INTO saves (player_id, case_id, slot, state, updated_at) VALUES (?, ?, ?, ?, ?)",
            (player_id, "case_001", "autosave", "not-json", "2026-06-20T12:00:00"),
        )
        conn.commit()

        with pytest.raises(CorruptSaveError, match="invalid JSON"):
            load_player_state("case_001", player_id, "autosave")


# ============================================================================
# 14. Malformed state dict (missing required PlayerState fields)
# ============================================================================


class TestMalformedSaveRequest:
    """POST /api/save with state={} → behavior."""

    @pytest.mark.asyncio
    async def test_empty_state_dict(self, client: AsyncClient) -> None:
        """Empty state dict → caught inside route, returned as SaveResponse(success=False).

        PlayerState requires `case_id` + `current_location`. Construction
        raises ValidationError, which the route catches in its bare except
        and returns SaveResponse(success=False).
        """
        r = await client.post(
            "/api/save",
            json={
                "player_id": "test_empty_state",
                "state": {},
                "slot": "autosave",
            },
        )

        # SaveRequest itself is valid (state: dict[str, Any]). 200 returned
        # with success=False inside the body.
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is False
        assert "fail" in body["message"].lower() or "error" in body["message"].lower() or body["message"]


# ============================================================================
# 15. VALID_SLOTS enforcement
# ============================================================================


class TestValidSlotsEnforcement:
    """Unknown slot names rejected."""

    @pytest.mark.asyncio
    async def test_unknown_slot_on_save_via_route(self, client: AsyncClient) -> None:
        """Unknown slot names are rejected at the schema layer via SaveSlotName Literal."""
        r = await client.post(
            "/api/save",
            json={
                "player_id": "test_bad_slot",
                "state": make_state(),
                "slot": "hacker_slot_99",
            },
        )
        assert r.status_code == 422

    def test_unknown_slot_rejected_at_persistence_layer(self) -> None:
        """VALID_SLOTS guard exists in persistence.py source.

        Source-level assertion (not runtime): autouse fixture has
        swapped the functions for mocks, so we can't invoke the real
        guard. Read the .py file directly. This is intentionally a
        source contract test — if someone deletes the VALID_SLOTS guard,
        this fails.
        """
        from pathlib import Path

        from src.state import persistence

        # Constant still defined with the canonical four slots.
        assert persistence.VALID_SLOTS == {
            "slot_1",
            "slot_2",
            "slot_3",
            "autosave",
            "default",
        }

        # Read the actual source file (bypass monkeypatched module attrs).
        source = Path(persistence.__file__).read_text()

        # All three CRUD functions reference VALID_SLOTS in their body.
        for fn_name in (
            "save_player_state",
            "load_player_state",
            "delete_player_save",
        ):
            fn_start = source.index(f"def {fn_name}(")
            # 50 lines max per function (project rule)
            fn_body = source[fn_start : fn_start + 3000]
            assert "VALID_SLOTS" in fn_body, (
                f"{fn_name} no longer checks VALID_SLOTS — slot validation regressed"
            )

    @pytest.mark.asyncio
    async def test_unknown_slot_on_delete(self, client: AsyncClient) -> None:
        """DELETE with unknown slot → 400 from explicit valid_slots check."""
        r = await client.delete(
            "/api/case/case_001/saves/hacker_slot_99",
            params={"player_id": "anyone"},
        )
        assert r.status_code == 400
        assert "invalid slot" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_pattern_invalid_slot_on_save(self, client: AsyncClient) -> None:
        """Slots with hyphens or punctuation fail the Pydantic pattern (422)."""
        r = await client.post(
            "/api/save",
            json={
                "player_id": "test_bad_pattern",
                "state": make_state(),
                "slot": "slot-1",  # hyphen — fails ^[a-zA-Z0-9_]+$
            },
        )
        assert r.status_code == 422


# ============================================================================
# 16. Reset clears autosave only — named slots survive
# ============================================================================


class TestResetPreservesNamedSlots:
    """Reset deletes autosave; slot_1/2/3 snapshots remain intact."""

    @pytest.mark.asyncio
    async def test_reset_preserves_slot1(self, client: AsyncClient) -> None:
        from src.state.persistence import load_player_state

        player_id = "test_reset_preserves"

        # Populate autosave + slot_1
        await save_autosave(
            client,
            player_id=player_id,
            state=make_state(discovered_evidence=["snapshot_evidence"]),
        )
        r = await client.post(
            "/api/save",
            json={
                "player_id": player_id,
                "state": make_state(),
                "slot": "slot_1",
            },
        )
        assert r.status_code == 200

        # Reset the case
        r = await client.post(
            "/api/case/case_001/reset",
            params={"player_id": player_id},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

        # Autosave gone
        autosave = load_player_state("case_001", player_id, "autosave")
        assert autosave is None, "Reset should clear autosave"

        # slot_1 preserved
        slot1 = load_player_state("case_001", player_id, "slot_1")
        assert slot1 is not None, "Reset must NOT touch named slots"
        assert "snapshot_evidence" in slot1.discovered_evidence

    @pytest.mark.asyncio
    async def test_reset_invalidates_cache(self, client: AsyncClient) -> None:
        from src.api.helpers import _cache_key, _state_cache, load_slot_state

        player_id = "test_reset_cache"

        # Populate database
        await save_autosave(
            client,
            player_id=player_id,
            state=make_state(discovered_evidence=["some_evidence"]),
        )

        # Call load_slot_state to load into the cache
        state = load_slot_state("case_001", player_id, "autosave")
        assert state is not None

        # Confirm it is cached
        key = _cache_key("case_001", player_id, "autosave")
        assert key in _state_cache

        # Reset the case
        r = await client.post(
            "/api/case/case_001/reset",
            params={"player_id": player_id},
        )
        assert r.status_code == 200

        # Cache key should be gone
        assert key not in _state_cache


# ============================================================================
# Bonus: verify list endpoint shape for parity
# ============================================================================


class TestListSavesShape:
    """Confirm the list response shape matches SaveSlotsListResponse."""

    @pytest.mark.asyncio
    async def test_list_empty_returns_empty_saves_array(
        self, client: AsyncClient
    ) -> None:
        r = await client.get(
            "/api/case/case_001/saves/list",
            params={"player_id": "totally_new_player_for_list"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["case_id"] == "case_001"
        assert body["saves"] == []
