"""End-to-end SSE tests for /api/present-evidence/stream.

Covers the unified fuzzy secret scorer pathway during streaming.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.helpers import save_slot_state
from src.main import app
from src.state import persistence as _persistence
from src.state.player_state import PlayerState
from tests.sse_helpers import build_mock_llm_client, collect_sse_stream


def load_player_state(case_id: str, player_id: str, slot: str = "autosave"):
    """Indirect lookup — picks up the conftest monkeypatch at call time."""
    return _persistence.load_player_state(case_id, player_id, slot)


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _seed_state_with_evidence(player_id: str, evidence_id: str) -> None:
    """Pre-seed PlayerState so present-evidence's 400-check passes.

    The endpoint rejects evidence not in `state.discovered_evidence`.
    """
    state = PlayerState(case_id="case_001", current_location="library")
    state.add_evidence(evidence_id)
    save_slot_state(state, player_id, "autosave")


class TestPresentEvidenceStreamHappyPath:
    @pytest.mark.asyncio
    async def test_returns_done_frame(self, client: AsyncClient) -> None:
        player_id = "test_sse_present_happy"
        _seed_state_with_evidence(player_id, "hidden_note")

        chunks = ["I... ", "I don't know what to say."]
        mock_client = build_mock_llm_client(chunks)
        with patch("src.api.routes.witnesses.get_client", return_value=mock_client):
            parsed = await collect_sse_stream(
                client,
                "POST",
                "/api/present-evidence/stream",
                json_body={
                    "witness_id": "elena",
                    "evidence_id": "hidden_note",
                    "case_id": "case_001",
                    "player_id": player_id,
                },
            )

        assert parsed.done_frame is not None
        assert "trust" in parsed.done_frame
        assert "secrets_revealed" in parsed.done_frame

    @pytest.mark.asyncio
    async def test_rejects_undiscovered_evidence(self, client: AsyncClient) -> None:
        """Present-evidence endpoint guards against undiscovered evidence."""
        # NOT seeding state — evidence is undiscovered.
        chunks = ["whatever"]
        mock_client = build_mock_llm_client(chunks)
        with patch("src.api.routes.witnesses.get_client", return_value=mock_client):
            async with client.stream(
                "POST",
                "/api/present-evidence/stream",
                json={
                    "witness_id": "elena",
                    "evidence_id": "hidden_note",
                    "case_id": "case_001",
                    "player_id": "test_sse_present_reject",
                },
            ) as response:
                # Drain so the connection closes cleanly.
                async for _ in response.aiter_text():
                    pass
                assert response.status_code == 400


class TestPresentEvidenceStreamSecretRevelation:
    """Elena's `tutoring_a_peer` secret is gated on the unified scorer.

    Keywords:
      - "tutoring rowan"
      - "defensive magic lessons"
      - "iron lodge hexing"

    The LLM's response below contains the phrase "tutoring rowan
    defensive magic lessons" affirmatively, with no denial pattern.
    After stemming, both keyword phrases score 1.0.
    """

    @pytest.mark.asyncio
    async def test_secret_revealed_in_done_frame(self, client: AsyncClient) -> None:
        player_id = "test_sse_present_secret"
        _seed_state_with_evidence(player_id, "hidden_note")

        # Affirmative confession matching the secret's keywords.
        chunks = [
            "Fine. Yes. I admit it. ",
            "I was teaching Rowan defensive magic lessons ",
            "because Iron Lodges kept hexing him in the corridors.",
        ]
        mock_client = build_mock_llm_client(chunks)
        with patch("src.api.routes.witnesses.get_client", return_value=mock_client):
            parsed = await collect_sse_stream(
                client,
                "POST",
                "/api/present-evidence/stream",
                json_body={
                    "witness_id": "elena",
                    "evidence_id": "hidden_note",
                    "case_id": "case_001",
                    "player_id": player_id,
                },
            )

        done = parsed.done_frame
        assert done is not None
        assert "tutoring_a_peer" in done["secrets_revealed"], (
            f"Expected secret 'tutoring_a_peer' in {done['secrets_revealed']!r}"
        )

    @pytest.mark.asyncio
    async def test_secret_persisted_to_witness_state(
        self, client: AsyncClient
    ) -> None:
        player_id = "test_sse_present_secret_persist"
        _seed_state_with_evidence(player_id, "hidden_note")

        chunks = [
            "Alright. ",
            "I have been teaching Rowan defensive magic lessons. ",
            "He needed it.",
        ]
        mock_client = build_mock_llm_client(chunks)
        with patch("src.api.routes.witnesses.get_client", return_value=mock_client):
            await collect_sse_stream(
                client,
                "POST",
                "/api/present-evidence/stream",
                json_body={
                    "witness_id": "elena",
                    "evidence_id": "hidden_note",
                    "case_id": "case_001",
                    "player_id": player_id,
                },
            )

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        elena_state = state.witness_states.get("elena")
        assert elena_state is not None
        assert "tutoring_a_peer" in elena_state.secrets_revealed
