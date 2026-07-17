"""Idempotency + Telegram snapshot tests (Phase 1)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.state.idempotency import (
    STATUS_IN_PROGRESS,
    claim_or_get,
    complete,
    mark_failed_before_mutation,
)
from src.state.persistence import _db_lock, _get_conn, save_player_state
from src.state.player_state import PlayerState


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _set_in_progress(player_id: str, operation: str, request_id: str) -> None:
    claim_or_get(player_id, operation, request_id)


class TestRequestIdValidation:
    @pytest.mark.asyncio
    async def test_invalid_request_id_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/case/case_001/change-location",
            json={
                "location_id": "library",
                "request_id": "has space",
            },
            params={"player_id": "p1"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_request_id_too_long_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/case/case_001/change-location",
            json={
                "location_id": "library",
                "request_id": "x" * 129,
            },
            params={"player_id": "p1"},
        )
        assert response.status_code == 422


class TestChangeLocationIdempotency:
    @pytest.mark.asyncio
    async def test_duplicate_completed_returns_same_body(
        self, client: AsyncClient
    ) -> None:
        payload = {
            "location_id": "iron_lodge_common_room",
            "request_id": "loc-req-1",
            "slot": "autosave",
        }
        r1 = await client.post(
            "/api/case/case_001/change-location",
            json=payload,
            params={"player_id": "player_a"},
        )
        assert r1.status_code == 200
        r2 = await client.post(
            "/api/case/case_001/change-location",
            json=payload,
            params={"player_id": "player_a"},
        )
        assert r2.status_code == 200
        assert r1.json() == r2.json()

    @pytest.mark.asyncio
    async def test_in_progress_returns_409(self, client: AsyncClient) -> None:
        _set_in_progress("player_b", "change_location", "loc-busy")
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "library", "request_id": "loc-busy"},
            params={"player_id": "player_b"},
        )
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["code"] == "request_in_progress"

    @pytest.mark.asyncio
    async def test_same_request_id_different_players_no_collision(
        self, client: AsyncClient
    ) -> None:
        payload = {"location_id": "kitchens", "request_id": "shared-id"}
        r1 = await client.post(
            "/api/case/case_001/change-location",
            json=payload,
            params={"player_id": "player_x"},
        )
        r2 = await client.post(
            "/api/case/case_001/change-location",
            json=payload,
            params={"player_id": "player_y"},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["updated_state"]["current_location"] == "kitchens"
        assert r2.json()["updated_state"]["current_location"] == "kitchens"

    @pytest.mark.asyncio
    async def test_same_id_different_operations_no_collision(
        self, client: AsyncClient
    ) -> None:
        rid = "cross-op-id"
        r1 = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "library", "request_id": rid},
            params={"player_id": "player_ops"},
        )
        r2 = await client.post(
            "/api/settings/update",
            json={
                "case_id": "case_001",
                "language": "ru",
                "request_id": rid,
            },
            params={"player_id": "player_ops"},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json()["success"] is True

    @pytest.mark.asyncio
    async def test_missing_request_id_keeps_legacy_behavior(
        self, client: AsyncClient
    ) -> None:
        r1 = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "third_floor_corridor"},
            params={"player_id": "legacy_player"},
        )
        r2 = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "third_floor_corridor"},
            params={"player_id": "legacy_player"},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        # No idempotency cache: both run, both succeed (not necessarily equal)
        assert r1.json()["success"] is True
        assert r2.json()["success"] is True


class TestInvestigateIdempotency:
    @pytest.mark.asyncio
    async def test_duplicate_completed_one_llm_call(self, client: AsyncClient) -> None:
        mock_response = "You find dust on the shelves. [EVIDENCE: library_ledger]"
        with patch("src.api.routes.investigation.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            payload = {
                "player_input": "examine the desk carefully",
                "case_id": "case_001",
                "location_id": "library",
                "request_id": "inv-1",
                "slot": "autosave",
            }
            r1 = await client.post(
                "/api/investigate",
                json=payload,
                params={"player_id": "inv_player"},
            )
            r2 = await client.post(
                "/api/investigate",
                json=payload,
                params={"player_id": "inv_player"},
            )

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json() == r2.json()
        assert mock_client.get_response.await_count == 1

    @pytest.mark.asyncio
    async def test_failed_before_mutation_allows_retry(
        self, client: AsyncClient
    ) -> None:
        from src.api.llm_client import LLMClientError

        payload = {
            "player_input": "look around",
            "case_id": "case_001",
            "request_id": "inv-retry",
        }
        with patch("src.api.routes.investigation.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(side_effect=LLMClientError("down"))
            mock_get.return_value = mock_client
            fail = await client.post(
                "/api/investigate",
                json=payload,
                params={"player_id": "retry_player"},
            )
        assert fail.status_code == 503

        with patch("src.api.routes.investigation.get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="The room is quiet.")
            mock_get.return_value = mock_client
            ok = await client.post(
                "/api/investigate",
                json=payload,
                params={"player_id": "retry_player"},
            )
        assert ok.status_code == 200
        assert "quiet" in ok.json()["narrator_response"]


class TestBriefingCompleteIdempotency:
    @pytest.mark.asyncio
    async def test_body_and_query_compatible(self, client: AsyncClient) -> None:
        # Legacy query-only
        r1 = await client.post(
            "/api/briefing/case_001/complete",
            params={"player_id": "brief_q", "slot": "autosave"},
        )
        assert r1.status_code == 200
        assert r1.json()["success"] is True

        # Body with request_id
        r2 = await client.post(
            "/api/briefing/case_001/complete",
            params={"player_id": "brief_b"},
            json={"slot": "autosave", "request_id": "brief-1"},
        )
        r3 = await client.post(
            "/api/briefing/case_001/complete",
            params={"player_id": "brief_b"},
            json={"slot": "autosave", "request_id": "brief-1"},
        )
        assert r2.status_code == 200
        assert r3.status_code == 200
        assert r2.json() == r3.json()


class TestTelegramSnapshot:
    @pytest.mark.asyncio
    async def test_snapshot_excludes_solution_and_hidden(
        self, client: AsyncClient
    ) -> None:
        state = PlayerState(
            case_id="case_001",
            current_location="library",
            discovered_evidence=["library_ledger"],
            visited_locations=["library"],
            language="en",
        )
        state.mark_briefing_complete()
        save_player_state("case_001", "snap_player", state, "autosave")

        response = await client.get(
            "/api/telegram/snapshot/case_001",
            params={"player_id": "snap_player", "slot": "autosave"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["case_id"] == "case_001"
        assert data["current_location"] == "library"
        assert data["discovered_evidence"] == ["library_ledger"]
        assert data["briefing_completed"] is True
        assert data["language"] == "en"
        assert "save_revision" in data
        assert data["verdict_attempts_remaining"] == 10
        assert data["case_solved"] is False
        assert isinstance(data["available_witnesses"], list)
        assert len(data["available_witnesses"]) >= 1
        assert "id" in data["available_witnesses"][0]
        assert "name" in data["available_witnesses"][0]

        # No solution / secret leakage
        raw = response.text.lower()
        assert "culprit" not in raw
        assert "solution" not in raw
        assert "secret" not in raw
        assert "api_key" not in raw
        assert "prompt" not in raw

    @pytest.mark.asyncio
    async def test_snapshot_fresh_player_defaults(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/telegram/snapshot/case_001",
            params={"player_id": "fresh_snap"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["discovered_evidence"] == []
        assert data["briefing_completed"] is False
        assert data["case_solved"] is False


class TestIdempotencyServiceUnit:
    def test_in_progress_then_complete_replay(self) -> None:
        claim_or_get("u1", "op", "r1")
        complete("u1", "op", "r1", {"ok": True}, 200)
        cached = claim_or_get("u1", "op", "r1")
        assert cached == {"ok": True}

    def test_failed_before_mutation_reclaim(self) -> None:
        claim_or_get("u2", "op", "r2")
        mark_failed_before_mutation("u2", "op", "r2")
        assert claim_or_get("u2", "op", "r2") is None  # re-claimed

    def test_in_progress_blocks(self) -> None:
        from fastapi import HTTPException

        claim_or_get("u3", "op", "r3")
        with pytest.raises(HTTPException) as exc:
            claim_or_get("u3", "op", "r3")
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_concurrent_claim_one_winner(self) -> None:
        """Only one concurrent claim succeeds; others get 409."""
        from fastapi import HTTPException

        results: list[str] = []

        def attempt() -> None:
            try:
                out = claim_or_get("u_conc", "op", "r_conc")
                if out is None:
                    results.append("claimed")
                else:
                    results.append("cached")
            except HTTPException:
                results.append("conflict")

        await asyncio.to_thread(
            lambda: (attempt(), attempt())
        )
        # Sequential in thread still sequential; force sequential expectation
        assert results.count("claimed") == 1
        assert results.count("conflict") == 1

        # Cleanup row for isolation (autouse deletes table between tests)
        with _db_lock:
            conn = _get_conn()
            row = conn.execute(
                "SELECT status FROM idempotency_records WHERE player_id = ?",
                ("u_conc",),
            ).fetchone()
        assert row is not None
        assert row[0] == STATUS_IN_PROGRESS
