"""End-to-end SSE tests for /api/interrogate/stream.

Capture current streaming behavior — trust delta extraction, base
trust adjustment, secret revelation through the unified scorer.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.state import persistence as _persistence
from tests.sse_helpers import build_mock_llm_client, collect_sse_stream


def load_player_state(case_id: str, player_id: str, slot: str = "autosave"):
    """Indirect lookup — picks up the conftest monkeypatch at call time."""
    return _persistence.load_player_state(case_id, player_id, slot)


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestInterrogateStreamHappyPath:
    @pytest.mark.asyncio
    async def test_emits_text_then_done(self, client: AsyncClient) -> None:
        chunks = ["I was ", "in the library. ", "Reading."]
        mock_client = build_mock_llm_client(chunks)
        with patch("src.api.routes.witnesses_logic.get_client", return_value=mock_client):
            parsed = await collect_sse_stream(
                client,
                "POST",
                "/api/interrogate/stream",
                json_body={
                    "witness_id": "elena",
                    "question": "Where were you?",
                    "case_id": "case_001",
                    "player_id": "test_sse_interrog_happy",
                },
            )

        # First text frame may be buffered/combined, but a done frame must exist.
        assert parsed.done_frame is not None
        # Some text was streamed
        assert len(parsed.text_frames) >= 1
        # Joined text matches what the LLM emitted (witness route buffers
        # chunks looking for trust tags, so individual frame boundaries can
        # differ — assert the assembled content instead).
        assembled = "".join(f["text"] for f in parsed.text_frames)
        assert assembled == "I was in the library. Reading."


class TestInterrogateStreamTrustDelta:
    """`[TRUST_DELTA: -10]` in the response moves witness trust."""

    @pytest.mark.asyncio
    async def test_negative_trust_delta_extracted(
        self, client: AsyncClient
    ) -> None:
        # Elena's base_trust = 55. With -10 → 45.
        chunks = [
            "How dare you accuse me! ",
            "I would never do such a thing. ",
            "[TRUST_DELTA: -10]",
        ]
        mock_client = build_mock_llm_client(chunks)
        with patch("src.api.routes.witnesses_logic.get_client", return_value=mock_client):
            parsed = await collect_sse_stream(
                client,
                "POST",
                "/api/interrogate/stream",
                json_body={
                    "witness_id": "elena",
                    "question": "Did you attack Professor Vane?",
                    "case_id": "case_001",
                    "player_id": "test_sse_interrog_trust",
                },
            )

        done = parsed.done_frame
        assert done is not None
        assert done["trust_delta"] == -10
        # Elena starts at 55, -10 → 45
        assert done["trust"] == 45

        # Trust tag should be stripped from streamed text frames
        assembled = "".join(f["text"] for f in parsed.text_frames)
        assert "TRUST_DELTA" not in assembled

    @pytest.mark.asyncio
    async def test_witness_state_persisted_with_new_trust(
        self, client: AsyncClient
    ) -> None:
        player_id = "test_sse_interrog_trust_persist"
        chunks = ["I had nothing to do with it. ", "[TRUST_DELTA: -10]"]
        mock_client = build_mock_llm_client(chunks)
        with patch("src.api.routes.witnesses_logic.get_client", return_value=mock_client):
            await collect_sse_stream(
                client,
                "POST",
                "/api/interrogate/stream",
                json_body={
                    "witness_id": "elena",
                    "question": "Did you do it?",
                    "case_id": "case_001",
                    "player_id": player_id,
                },
            )

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        elena_state = state.witness_states.get("elena")
        assert elena_state is not None
        assert elena_state.trust == 45
