"""End-to-end SSE tests for /api/investigate/stream.

Capture current streaming behavior so the upcoming refactor wave does
not silently regress it. Some assertions are intentionally weak where
the current production behavior is known to be wrong — those are
tagged with `# REGRESSION`.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src import state as _state_pkg  # noqa: F401 — keep package import live
from src.main import app
from src.state import persistence as _persistence
from tests.sse_helpers import (
    build_mock_llm_client,
    collect_sse_stream,
    iter_sse_frames,
)


def load_player_state(case_id: str, player_id: str, slot: str = "autosave"):
    """Indirect lookup — picks up the conftest monkeypatch at call time."""
    return _persistence.load_player_state(case_id, player_id, slot)


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def chunks_with_evidence() -> list[str]:
    """Four chunks ending with an [EVIDENCE: hidden_note] tag.

    `hidden_note` is a real evidence ID in case_001.yaml/library.
    """
    return [
        "You ",
        "examine ",
        "the desk. ",
        "[EVIDENCE: hidden_note]",
    ]


class TestInvestigateStreamHappyPath:
    """Capture the canonical SSE wire format."""

    @pytest.mark.asyncio
    async def test_first_frame_is_text_last_is_done(
        self, client: AsyncClient, chunks_with_evidence: list[str]
    ) -> None:
        mock_client = build_mock_llm_client(chunks_with_evidence)
        mock_client.get_response_stream = MagicMock(
            side_effect=mock_client.get_response_stream
        )
        with patch("src.api.routes.investigation.get_client", return_value=mock_client):
            parsed = await collect_sse_stream(
                client,
                "POST",
                "/api/investigate/stream",
                json_body={
                    "player_input": "search the desk thoroughly",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": "test_sse_invest_happy",
                },
            )

        # First frame must be a text chunk
        assert parsed.first.get("text") == "You "
        # Last frame must signal done
        assert parsed.last.get("done") is True
        # Intermediate frames are pure text chunks
        text_chunks = [f["text"] for f in parsed.text_frames]
        assert text_chunks == [
            "You ",
            "examine ",
            "the desk. ",
            "[EVIDENCE: hidden_note]",
        ]
        call_kwargs = mock_client.get_response_stream.call_args.kwargs
        assert call_kwargs["max_tokens"] == 600
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["disable_reasoning"] is True

    @pytest.mark.asyncio
    async def test_done_frame_has_expected_meta(
        self, client: AsyncClient, chunks_with_evidence: list[str]
    ) -> None:
        mock_client = build_mock_llm_client(chunks_with_evidence)
        with patch("src.api.routes.investigation.get_client", return_value=mock_client):
            parsed = await collect_sse_stream(
                client,
                "POST",
                "/api/investigate/stream",
                json_body={
                    "player_input": "search the desk",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": "test_sse_invest_meta",
                },
            )

        done = parsed.done_frame
        assert done is not None
        assert "new_evidence" in done
        assert "evidence_names" in done
        assert "updated_state" in done
        assert "meta" in done
        assert "latency_ms" in done["meta"]


class TestInvestigateStreamEvidence:
    """Tagged [EVIDENCE: id] in the stream lands in state + done frame."""

    @pytest.mark.asyncio
    async def test_evidence_tag_appears_in_done_frame(
        self, client: AsyncClient, chunks_with_evidence: list[str]
    ) -> None:
        mock_client = build_mock_llm_client(chunks_with_evidence)
        with patch("src.api.routes.investigation.get_client", return_value=mock_client):
            parsed = await collect_sse_stream(
                client,
                "POST",
                "/api/investigate/stream",
                json_body={
                    "player_input": "look under the desk for clues",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": "test_sse_invest_evidence",
                },
            )

        done = parsed.done_frame
        assert done is not None
        assert "hidden_note" in done["new_evidence"]
        assert done["evidence_names"].get("hidden_note")

    @pytest.mark.asyncio
    async def test_evidence_persisted_to_state(
        self, client: AsyncClient, chunks_with_evidence: list[str]
    ) -> None:
        player_id = "test_sse_invest_evidence_persist"
        mock_client = build_mock_llm_client(chunks_with_evidence)
        with patch("src.api.routes.investigation.get_client", return_value=mock_client):
            await collect_sse_stream(
                client,
                "POST",
                "/api/investigate/stream",
                json_body={
                    "player_input": "look under the desk",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )

        # Verify state was saved with the new evidence
        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert "hidden_note" in state.discovered_evidence

    @pytest.mark.asyncio
    async def test_malformed_spell_marker_is_rejected_without_second_llm_call(
        self, client: AsyncClient
    ) -> None:
        mock_client = build_mock_llm_client(
            ["The frost forms a starburst. [EVIDENCE_pattern]"]
        )
        mock_client.get_response = AsyncMock(return_value="[EVIDENCE: frost_pattern]")

        with (
            patch("src.api.routes.investigation.get_client", return_value=mock_client),
            patch(
                "src.api.routes.investigation_logic.calculate_spell_outcome",
                return_value="SUCCESS",
            ),
        ):
            parsed = await collect_sse_stream(
                client,
                "POST",
                "/api/investigate/stream",
                json_body={
                    "player_input": "Essence, speak on the window",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": "test_sse_rite_marker_retry",
                },
            )

        assert mock_client.get_response.await_count == 0
        assert parsed.done_frame is not None
        assert parsed.done_frame["new_evidence"] == []


class TestInvestigateStreamKeepalive:
    """When the LLM stalls > _KEEPALIVE_INTERVAL, emit `:keepalive`."""

    @pytest.mark.asyncio
    async def test_keepalive_emitted_between_chunks(
        self, client: AsyncClient
    ) -> None:
        # Patch interval to a small value AND make chunks slow enough to trip it.
        chunks = ["alpha ", "beta ", "gamma."]
        mock_client = build_mock_llm_client(chunks, delay_between=0.15)
        with (
            patch("src.api.helpers._KEEPALIVE_INTERVAL", 0.05),
            patch("src.api.routes.investigation.get_client", return_value=mock_client),
        ):
            parsed = await collect_sse_stream(
                client,
                "POST",
                "/api/investigate/stream",
                json_body={
                    "player_input": "search slowly",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": "test_sse_invest_keepalive",
                },
            )

        assert parsed.keepalive_count >= 1, (
            f"Expected at least one :keepalive line. "
            f"Raw lines: {parsed.raw_lines!r}"
        )
        # The data stream still completes
        assert parsed.done_frame is not None


class TestInvestigateStreamErrorMidStream:
    """LLM raises after 2 chunks — capture current broken behavior."""

    @pytest.mark.asyncio
    async def test_emits_error_frame_and_skips_done(
        self, client: AsyncClient
    ) -> None:
        player_id = "test_sse_invest_error_mid"
        mock_client = build_mock_llm_client(
            ["You ", "examine ", "the ", "<unused>"],
            raise_after=2,
            raise_exc=RuntimeError("simulated LLM crash"),
        )
        with patch("src.api.routes.investigation.get_client", return_value=mock_client):
            parsed = await collect_sse_stream(
                client,
                "POST",
                "/api/investigate/stream",
                json_body={
                    "player_input": "look around",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )

        # (a) error frame emitted
        assert parsed.error_frame is not None
        assert "error" in parsed.error_frame
        # (b) no done frame
        assert parsed.done_frame is None

    @pytest.mark.asyncio
    async def test_state_not_persisted_on_error(
        self, client: AsyncClient
    ) -> None:
        # REGRESSION: After an LLM error mid-stream the conversation /
        # narrator turn is NOT saved. The refactor will flip this to
        # `assert state is not None` (save partial-but-flagged state) OR
        # at minimum log the error to the state's conversation history.
        player_id = "test_sse_invest_error_persist"
        mock_client = build_mock_llm_client(
            ["You ", "examine ", "the ", "<unused>"],
            raise_after=2,
            raise_exc=RuntimeError("simulated LLM crash"),
        )
        with patch("src.api.routes.investigation.get_client", return_value=mock_client):
            await collect_sse_stream(
                client,
                "POST",
                "/api/investigate/stream",
                json_body={
                    "player_input": "look around",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )

        state = load_player_state("case_001", player_id, "autosave")
        # REGRESSION: current behavior — no state written when error fires
        # before save_slot_state. Refactor target: persist a marker.
        assert state is None


class TestInvestigateStreamClientDisconnect:
    """Client drops the connection mid-flight.

    NOTE: httpx.ASGITransport runs the app in-process and does NOT cleanly
    propagate `http.disconnect` to the StreamingResponse generator
    (Starlette's check requires the route to call `request.is_disconnected()`
    explicitly, which investigation.py does not). As a result, in this
    test environment the server-side generator runs to completion AFTER
    the client closes its end — and so state IS persisted.

    The production bug only surfaces with a real HTTP transport where
    the generator's `asend()` raises on the dropped socket. We capture
    the test-environment baseline here; the regression assertion below
    documents what production currently does.
    """

    @pytest.mark.asyncio
    async def test_state_persisted_in_test_env_despite_disconnect(
        self, client: AsyncClient
    ) -> None:
        # REGRESSION: In production (real HTTP transport), nothing is
        # persisted when the client disconnects before `save_slot_state`
        # runs — because the generator gets cancelled mid-flight. In this
        # test (ASGITransport, in-process), the generator runs to
        # completion even after the client closes, so state IS saved.
        # The refactor will flip this to assert the production behavior
        # is fixed (partial-state persistence on disconnect).
        player_id = "test_sse_invest_disconnect"
        chunks = ["You ", "examine ", "the ", "desk. ", "[EVIDENCE: hidden_note]"]
        mock_client = build_mock_llm_client(chunks, delay_between=0.05)
        with patch("src.api.routes.investigation.get_client", return_value=mock_client):
            seen_text_frames = 0
            async for frame in iter_sse_frames(
                client,
                "POST",
                "/api/investigate/stream",
                json_body={
                    "player_input": "search the desk",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            ):
                if "text" in frame:
                    seen_text_frames += 1
                    if seen_text_frames >= 1:
                        break

            # Let the in-process generator finish what it started.
            await asyncio.sleep(0.5)

        state = load_player_state("case_001", player_id, "autosave")
        # REGRESSION: test-env baseline — in-process generator finishes
        # and persists. Production behavior on real HTTP is the opposite.
        assert state is not None

    @pytest.mark.asyncio
    async def test_disconnect_does_not_emit_done_frame_to_client(
        self, client: AsyncClient
    ) -> None:
        # Document the client-visible side of disconnect: after the
        # client breaks out of the iteration, it never sees the done
        # frame (regardless of what the server does internally).
        chunks = ["You ", "examine ", "the ", "desk. ", "[EVIDENCE: hidden_note]"]
        mock_client = build_mock_llm_client(chunks, delay_between=0.05)
        seen_frames: list[dict] = []
        with patch("src.api.routes.investigation.get_client", return_value=mock_client):
            async for frame in iter_sse_frames(
                client,
                "POST",
                "/api/investigate/stream",
                json_body={
                    "player_input": "search the desk",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": "test_sse_invest_disconnect_view",
                },
            ):
                seen_frames.append(frame)
                if len(seen_frames) >= 1:
                    break

        # Client only saw the first chunk — no done frame ever reached it.
        assert all(not f.get("done") for f in seen_frames)
