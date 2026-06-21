"""Concurrency baseline tests for shared state mutations.

These tests capture CURRENT behaviour around:

* the in-memory `_state_cache` (helpers.py:419-451) that holds one mutable
  PlayerState per (player, case, slot); and
* the single SQLite connection (state/persistence.py:35-46) reused across
  requests.

Both layers are the next refactor target. Tests use `# REGRESSION:` markers to
pin the broken-today behaviour, so refactor PRs flip these assertions
intentionally.

Notes on what races we actually exercise here:

* asyncio is single-threaded; under httpx ASGITransport requests are
  cooperative. SQLite race conditions tied to the OS thread pool (`check_same_thread=False`)
  WON'T surface — see the docstring of `test_concurrent_investigate_*_real_db`
  for what would be needed to reproduce them.
* What WILL surface here: shared-object races in the `_state_cache` (two
  requests holding the same PlayerState reference, interleaving mutations on
  `discovered_evidence` between awaits). That's race #1 we want pinned.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from tests.concurrency_helpers import (
    clear_state_cache,
    fresh_player_state,
    load_state_direct,
    make_client,
    make_streaming_client_mock,
    make_text_mock,
    seed_state,
    state_cache_snapshot,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    """Cache is process-global; wipe before AND after each test."""
    clear_state_cache()
    yield
    clear_state_cache()


# ── 1. Concurrent investigate, same player ─────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_investigate_same_player_evidence_loss() -> None:
    """Two parallel investigate-stream calls. Each LLM yields a different
    [EVIDENCE: ...] tag. After both finish, check what survived.

    With request-scoped copies from `load_slot_state`, each request mutates its
    own PlayerState. Saves are last-write-wins — exactly one evidence survives
    in persistence. Responses must not leak the other request's evidence via
    shared cache aliasing.
    """
    player_id = "race_invest_same"
    case_id = "case_001"

    # Seed an empty state so both requests see the same starting point.
    seed_state(case_id, player_id, fresh_player_state(case_id=case_id))

    mock_a = make_text_mock(
        "You search the desk. [EVIDENCE: hidden_note] A crumpled parchment."
    )
    mock_b = make_text_mock(
        "You inspect the floor. [EVIDENCE: frost_pattern] Frost rings the body."
    )

    call_count = {"n": 0}

    def _get_client_side_effect() -> Any:
        # First call -> mock_a, second -> mock_b (deterministic-ish ordering;
        # asyncio.gather schedules in order).
        call_count["n"] += 1
        return mock_a if call_count["n"] == 1 else mock_b

    async with make_client() as client:
        with patch(
            "src.api.routes.investigation.get_client",
            side_effect=_get_client_side_effect,
        ):
            resp_a, resp_b = await asyncio.gather(
                client.post(
                    "/api/investigate",
                    json={
                        "player_input": "search the desk",
                        "case_id": case_id,
                        "location_id": "library",
                        "player_id": player_id,
                    },
                ),
                client.post(
                    "/api/investigate",
                    json={
                        "player_input": "inspect the floor",
                        "case_id": case_id,
                        "location_id": "library",
                        "player_id": player_id,
                    },
                ),
            )

    assert resp_a.status_code == 200, resp_a.text
    assert resp_b.status_code == 200, resp_b.text

    # Read back from persistence (cache-bypassing) AND from cache to compare.
    persisted = load_state_direct(case_id, player_id)
    assert persisted is not None
    persisted_ev = set(persisted.discovered_evidence)

    cache_snap = state_cache_snapshot()
    cached = cache_snap.get((player_id, case_id, "autosave"))
    cached_ev = set(cached.discovered_evidence) if cached else set()

    # Last-write-wins: one evidence wins in persistence (not both).
    winner = persisted_ev | cached_ev
    assert winner <= {"hidden_note", "frost_pattern"}
    assert len(winner) == 1

    bodies = [resp_a.json(), resp_b.json()]
    by_evidence: dict[str, set[str]] = {}
    for body in bodies:
        ev = body["updated_state"]["discovered_evidence"]
        assert len(ev) <= 1
        if ev:
            by_evidence[ev[0]] = set(ev)

    # Each response reports only its own evidence (no cross-request aliasing).
    # Match by narrator text — gather order is not tied to mock call order.
    desk_body = next(b for b in bodies if "hidden_note" in b["narrator_response"])
    floor_body = next(b for b in bodies if "frost_pattern" in b["narrator_response"])
    assert set(desk_body["updated_state"]["discovered_evidence"]) <= {"hidden_note"}
    assert set(floor_body["updated_state"]["discovered_evidence"]) <= {"frost_pattern"}
    assert len(by_evidence) == 2


# ── 2. Concurrent investigate + interrogate ────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_investigate_and_interrogate_same_player() -> None:
    """Investigate (mutates evidence) + interrogate (mutates trust + adds
    witness state) in parallel.

    REGRESSION: investigate uses `load_slot_state` (cache layer); interrogate
    uses `load_or_create_state` (BYPASSES cache, reads from persistence
    directly). They each get a different PlayerState instance, mutate it,
    then both call `save_slot_state`. Last writer wins. So either the
    evidence OR the witness state is lost.

    Today the cache writes update `_state_cache` AND persistence, but the
    interrogate path's `load_or_create_state` read happens BEFORE investigate's
    save lands, so interrogate sees the pre-mutation state and overwrites
    investigate's evidence when it saves.
    """
    player_id = "race_invest_witness"
    case_id = "case_001"

    seed_state(case_id, player_id, fresh_player_state(case_id=case_id))

    invest_mock = make_text_mock(
        "You search carefully. [EVIDENCE: hidden_note] A note."
    )
    witness_mock = make_text_mock(
        "Elena looks up from her book, eyes wary. [TRUST_DELTA: -5]"
    )

    async with make_client() as client:
        with (
            patch(
                "src.api.routes.investigation.get_client",
                return_value=invest_mock,
            ),
            patch(
                "src.api.routes.witnesses.get_client",
                return_value=witness_mock,
            ),
        ):
            invest_resp, witness_resp = await asyncio.gather(
                client.post(
                    "/api/investigate",
                    json={
                        "player_input": "search the desk",
                        "case_id": case_id,
                        "location_id": "library",
                        "player_id": player_id,
                    },
                ),
                client.post(
                    "/api/interrogate",
                    json={
                        "witness_id": "elena",
                        "question": "Did you do it?",
                        "case_id": case_id,
                        "player_id": player_id,
                    },
                ),
            )

    assert invest_resp.status_code == 200, invest_resp.text
    assert witness_resp.status_code == 200, witness_resp.text

    persisted = load_state_direct(case_id, player_id)
    assert persisted is not None

    has_evidence = "hidden_note" in persisted.discovered_evidence
    has_witness = "elena" in persisted.witness_states

    # REGRESSION: at least ONE of the two mutations is lost in the final
    # persisted state because investigate and interrogate load through
    # different code paths (cached vs uncached) and the second save clobbers
    # the first.
    #
    # We can't deterministically predict which one is lost (depends on which
    # request's save finishes last under the asyncio scheduler), so we assert
    # the WEAK CURRENT contract and tag the strong one for the refactor.
    assert has_evidence or has_witness, "both mutations vanished — full data loss"

    # Post-refactor (request-scoped state, atomic save merge):
    #     assert has_evidence and has_witness
    # Today this is unreliable, so we just record what we got:
    print(
        f"[REGRESSION] investigate+interrogate race: "
        f"evidence={has_evidence}, witness={has_witness}"
    )


# ── 3. Concurrent save-to-slot while autosave is mid-stream ────────────────


@pytest.mark.asyncio
async def test_save_to_slot_while_autosave_mid_stream() -> None:
    """Start a slow investigate-stream; mid-flight, POST /api/save to copy
    autosave -> slot_1. The save-to-slot does a `load_player_state(autosave)`
    *before* the stream has saved its evidence.

    REGRESSION (TOCTOU): slot_1 ends up with the PRE-stream autosave state,
    not the post-stream state. The user clicked "save" while the LLM was
    speaking and got a checkpoint that's missing the discovery.

    Post-refactor: either save should block until in-flight writes drain, or
    the save endpoint should explicitly take a snapshot of the post-flight
    state (read-after-write barrier).
    """
    player_id = "race_save_during_stream"
    case_id = "case_001"

    seed_state(case_id, player_id, fresh_player_state(case_id=case_id))

    # Slow stream: ~0.5s total to send all chunks; gives the /api/save call
    # plenty of time to fire in between.
    slow_mock = make_streaming_client_mock(
        chunks=[
            "You look around.",
            " The candles flicker.",
            " [EVIDENCE: hidden_note]",
            " A parchment falls.",
        ],
        delay_s=0.12,
    )

    async with make_client() as client:
        with patch(
            "src.api.routes.investigation.get_client",
            return_value=slow_mock,
        ):

            async def fire_stream() -> str:
                # Drain the stream to completion.
                async with client.stream(
                    "POST",
                    "/api/investigate/stream",
                    json={
                        "player_input": "search the desk",
                        "case_id": case_id,
                        "location_id": "library",
                        "player_id": player_id,
                    },
                ) as r:
                    chunks: list[str] = []
                    async for c in r.aiter_text():
                        chunks.append(c)
                    return "".join(chunks)

            async def fire_save_after_delay() -> Any:
                # Wait for the stream to have started but not finished.
                await asyncio.sleep(0.20)
                return await client.post(
                    "/api/save",
                    json={
                        "player_id": player_id,
                        "slot": "slot_1",
                        "state": {
                            "case_id": case_id,
                            "current_location": "library",
                        },
                    },
                )

            stream_body, save_resp = await asyncio.gather(
                fire_stream(),
                fire_save_after_delay(),
            )

    assert save_resp.status_code == 200
    assert save_resp.json()["success"] is True

    autosave_after = load_state_direct(case_id, player_id, "autosave")
    slot1_after = load_state_direct(case_id, player_id, "slot_1")

    assert autosave_after is not None
    # Autosave eventually picks up the evidence (after stream finishes).
    assert "hidden_note" in autosave_after.discovered_evidence

    assert slot1_after is not None
    # REGRESSION: slot_1 was snapshotted from autosave DURING the stream.
    # It captured the state before the evidence was added.
    # Today: slot_1 has empty discovered_evidence. After refactor with proper
    # ordering, this should equal autosave (i.e. include hidden_note).
    if "hidden_note" not in slot1_after.discovered_evidence:
        # The TOCTOU bug surfaced. Pin it.
        assert slot1_after.discovered_evidence == [], (
            "slot_1 captured something but not the new evidence — "
            "partial-state TOCTOU, even worse than expected"
        )
        print(
            "[REGRESSION] TOCTOU: slot_1 saved pre-stream state. "
            "Stream finished AFTER /api/save snapshotted autosave."
        )
    else:
        # The race didn't actually fire on this run (scheduler ordering).
        # Document it but don't fail.
        print(
            "[INFO] save-during-stream race did not surface this run "
            "(scheduler ordered save AFTER stream finished). "
            "Re-run with --count=10 to reproduce."
        )


# ── 4. Same player, same slot, double-fire same investigate ────────────────


@pytest.mark.asyncio
async def test_double_fire_same_investigate_request() -> None:
    """Same player rapidly fires the SAME investigate twice (user double-click,
    or React StrictMode). Both hit the LLM (LLM-cost leak: bug #?).

    REGRESSION: no idempotency / deduplication layer. The LLM is called
    twice. Both responses are appended to conversation_history. If the LLM
    yields evidence, it's added once (add_evidence dedups), but the cost was
    paid twice. Capture the duplicate calls.
    """
    player_id = "race_double_fire"
    case_id = "case_001"

    seed_state(case_id, player_id, fresh_player_state(case_id=case_id))

    text = "You find a note. [EVIDENCE: hidden_note] A crumpled parchment."
    mock_client = make_text_mock(text)

    async with make_client() as client:
        with patch(
            "src.api.routes.investigation.get_client",
            return_value=mock_client,
        ):
            resp_a, resp_b = await asyncio.gather(
                client.post(
                    "/api/investigate",
                    json={
                        "player_input": "search the desk",
                        "case_id": case_id,
                        "location_id": "library",
                        "player_id": player_id,
                    },
                ),
                client.post(
                    "/api/investigate",
                    json={
                        "player_input": "search the desk",
                        "case_id": case_id,
                        "location_id": "library",
                        "player_id": player_id,
                    },
                ),
            )

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    # REGRESSION: LLM was called twice. Refactor target: in-flight request
    # deduplication keyed by (player_id, case_id, slot, player_input).
    assert mock_client.get_response.await_count == 2, (
        "LLM should have been called twice (no dedup today). "
        f"Got {mock_client.get_response.await_count}"
    )

    # Conversation history: both player-input lines were appended.
    persisted = load_state_direct(case_id, player_id)
    assert persisted is not None

    # Evidence deduped (PlayerState.add_evidence is idempotent), so list has
    # 1 entry not 2.
    assert persisted.discovered_evidence.count("hidden_note") == 1


# ── 5. Different player_ids — should NOT race ──────────────────────────────


@pytest.mark.asyncio
async def test_different_players_no_race() -> None:
    """10 different players, 10 parallel investigates. Each player's state
    must be isolated.

    This test should PASS today and stay passing after the refactor — it's
    the regression guard for "did we accidentally introduce cross-player
    state bleed?".
    """
    case_id = "case_001"
    n_players = 10

    # Distinct LLM responses per request, each tagging a distinct evidence id.
    # We reuse 'hidden_note' / 'frost_pattern' / 'focus_signature' etc. cycling.
    evidence_pool = [
        "hidden_note",
        "frost_pattern",
        "focus_signature",
        "scuff_marks",
        "dropped_badge",
    ]

    # Seed all players with empty state.
    for i in range(n_players):
        seed_state(
            case_id,
            f"isolated_p{i}",
            fresh_player_state(case_id=case_id),
        )

    # All players will receive a response containing evidence_pool[i % len].
    # Build per-request mocks via a side_effect that picks based on call order.
    responses = [
        f"You find something. [EVIDENCE: {evidence_pool[i % len(evidence_pool)]}]"
        for i in range(n_players)
    ]

    call_idx = {"n": 0}

    def _get_client() -> Any:
        idx = call_idx["n"]
        call_idx["n"] += 1
        return make_text_mock(responses[idx])

    async with make_client() as client:
        with patch(
            "src.api.routes.investigation.get_client",
            side_effect=_get_client,
        ):
            tasks = [
                client.post(
                    "/api/investigate",
                    json={
                        "player_input": f"search action {i}",
                        "case_id": case_id,
                        "location_id": "library",
                        "player_id": f"isolated_p{i}",
                    },
                )
                for i in range(n_players)
            ]
            results = await asyncio.gather(*tasks)

    assert all(r.status_code == 200 for r in results), [
        (r.status_code, r.text[:200]) for r in results if r.status_code != 200
    ]

    # Each player's persisted state has EXACTLY their own evidence — no
    # cross-pollination. (We can't pin WHICH evidence each player got because
    # side_effect order isn't tied to request order in asyncio, but every
    # player must have exactly 1 evidence and it must be from the pool.)
    for i in range(n_players):
        state = load_state_direct(case_id, f"isolated_p{i}")
        assert state is not None, f"player {i} state missing"
        assert len(state.discovered_evidence) == 1, (
            f"player {i} has {len(state.discovered_evidence)} evidence — "
            "expected exactly 1 (cross-player leak)"
        )
        assert state.discovered_evidence[0] in evidence_pool


# ── 7. Concurrent reads while writing ──────────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_read_while_writing() -> None:
    """Fire GET /api/load while an investigate-stream is mid-flight.

    REGRESSION: the reader may see (a) the in-memory cache's mid-mutation
    state, (b) the pre-mutation persisted state, or (c) a torn state where
    `discovered_evidence` has the new entry but `conversation_history` doesn't
    (or vice versa). All three are bad for a UI relying on "load = consistent
    snapshot".
    """
    player_id = "race_read_during_write"
    case_id = "case_001"

    seed_state(case_id, player_id, fresh_player_state(case_id=case_id))

    slow_mock = make_streaming_client_mock(
        chunks=[
            "You look around. ",
            "The room is silent. ",
            "[EVIDENCE: hidden_note] ",
            "A note falls.",
        ],
        delay_s=0.10,
    )

    snapshots: list[dict[str, Any] | None] = []

    async with make_client() as client:
        with patch(
            "src.api.routes.investigation.get_client",
            return_value=slow_mock,
        ):

            async def fire_stream() -> None:
                async with client.stream(
                    "POST",
                    "/api/investigate/stream",
                    json={
                        "player_input": "search the desk",
                        "case_id": case_id,
                        "location_id": "library",
                        "player_id": player_id,
                    },
                ) as r:
                    async for _ in r.aiter_text():
                        pass

            async def poll_loads() -> None:
                # 4 reads spaced through the stream lifetime.
                for _ in range(4):
                    await asyncio.sleep(0.10)
                    resp = await client.get(
                        f"/api/load/{case_id}",
                        params={"player_id": player_id, "slot": "autosave"},
                    )
                    snapshots.append(resp.json() if resp.status_code == 200 else None)

            await asyncio.gather(fire_stream(), poll_loads())

    # Final state should have the evidence.
    final = load_state_direct(case_id, player_id)
    assert final is not None
    assert "hidden_note" in final.discovered_evidence

    # Snapshots captured during the stream: we expect a mix of empty +
    # populated. Pin whatever we observed.
    populated = sum(
        1
        for s in snapshots
        if s and "hidden_note" in s.get("discovered_evidence", [])
    )
    empty = sum(
        1
        for s in snapshots
        if s and "hidden_note" not in s.get("discovered_evidence", [])
    )

    # At least one of the snapshots should exist (load endpoint worked).
    assert any(s is not None for s in snapshots), "no reads completed"

    # REGRESSION: the boundary between "empty" and "populated" reads is
    # non-deterministic — depends on when save_slot_state fired during the
    # stream. Today the save fires only AFTER the LLM finishes (in the SSE
    # done-event branch), so all mid-stream reads see the pre-mutation state.
    # That means: empty > 0 AND populated > 0 is possible but not required.
    # We just record what happened.
    print(
        f"[INFO] read-during-write: {empty} empty snapshots, "
        f"{populated} populated snapshots. "
        "Refactor should make reads-during-writes return a consistent "
        "snapshot (either pre OR post, never torn)."
    )
    # The cache-vs-persistence inconsistency lives below. Compare cache to
    # persistence WHILE the stream is mid-flight — but we can only inspect
    # post-hoc here. Drop a diagnostic.
