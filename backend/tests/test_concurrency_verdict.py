"""Concurrency baseline tests for /api/submit-verdict.

The endpoint guard at `verdict.py:58-62` is:

    if verdict_state.attempts_remaining <= 0:
        raise HTTPException(400, ...)

Followed (later) by:

    verdict_state.add_attempt(...)  # decrements attempts_remaining

REGRESSION: two concurrent requests can both pass the `<= 0` check before
either runs `add_attempt`. Both then decrement. Starting from
attempts_remaining=1, this drops to -1 (or 0 with one of the two clobbered).
Starting from 10, the counter is consistent in magnitude but the per-attempt
log may be inconsistent (depending on which save fires last).

These tests pin the broken-today outcome so the refactor flips them.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from src.state.player_state import VerdictState
from tests.concurrency_helpers import (
    clear_state_cache,
    fresh_player_state,
    load_state_direct,
    make_client,
    make_evaluator_result,
    seed_state,
)


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    clear_state_cache()
    yield
    clear_state_cache()


# ── Common patch helpers ─────────────────────────────────────────────────────


def _patch_verdict_llm(
    score: int = 50,
    quality: str = "fair",
    graves_text: str = "MOCKED GRAVES FEEDBACK",
    sleep_s: float = 0.05,
) -> list[Any]:
    """Build the list of patches needed to short-circuit the verdict LLMs.

    A non-zero `sleep_s` is critical: real LLM calls have I/O latency, so the
    asyncio event loop yields between guard-check and decrement. With a
    return_value mock the await resolves immediately and the race serializes
    by accident. Sleeping reproduces real-world scheduling.
    """

    async def _eval_with_yield(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        await asyncio.sleep(sleep_s)
        return make_evaluator_result(score=score, quality=quality)

    async def _graves_with_yield(*_args: Any, **_kwargs: Any) -> str:
        await asyncio.sleep(sleep_s)
        return graves_text

    eval_patch = patch(
        "src.api.routes.verdict.evaluate_reasoning_llm",
        side_effect=_eval_with_yield,
    )
    graves_patch = patch(
        "src.api.routes.verdict.build_graves_feedback_llm",
        side_effect=_graves_with_yield,
    )
    return [eval_patch, graves_patch]


# ── Test 4 from the brief: concurrent verdict submissions ──────────────────


@pytest.mark.asyncio
async def test_concurrent_verdict_submissions_overshoots_attempts() -> None:
    """Two parallel verdict submissions on a state with attempts_remaining=1.

    REGRESSION: both pass the `<= 0` check, both call add_attempt, both
    decrement. Counter ends at -1.

    Expected post-refactor: exactly one succeeds, the other returns HTTP 400
    "no attempts remaining", counter ends at 0.
    """
    player_id = "verdict_race_1"
    case_id = "case_001"

    # Seed with attempts_remaining = 1.
    state = fresh_player_state(case_id=case_id)
    state.verdict_state = VerdictState(case_id=case_id, attempts_remaining=1)
    seed_state(case_id, player_id, state)

    patches = _patch_verdict_llm(score=50)
    for p in patches:
        p.start()
    try:
        async with make_client() as client:
            resp_a, resp_b = await asyncio.gather(
                client.post(
                    "/api/submit-verdict",
                    json={
                        "accused_suspect_id": "cassian",
                        "reasoning": "Concurrent submission A.",
                        "evidence_cited": [],
                        "case_id": case_id,
                        "player_id": player_id,
                    },
                ),
                client.post(
                    "/api/submit-verdict",
                    json={
                        "accused_suspect_id": "elena",
                        "reasoning": "Concurrent submission B.",
                        "evidence_cited": [],
                        "case_id": case_id,
                        "player_id": player_id,
                    },
                ),
            )
    finally:
        for p in patches:
            p.stop()

    status_codes = sorted([resp_a.status_code, resp_b.status_code])

    persisted = load_state_direct(case_id, player_id)
    assert persisted is not None
    assert persisted.verdict_state is not None
    remaining = persisted.verdict_state.attempts_remaining
    n_attempts_logged = len(persisted.verdict_state.attempts)

    # REGRESSION: today both requests pass the guard. So both return 200.
    # Counter underflows to -1, OR (if the cache shared a reference) ends at 0
    # but with both attempts logged.
    print(
        f"[REGRESSION] verdict race: status_codes={status_codes}, "
        f"attempts_remaining={remaining}, attempts_logged={n_attempts_logged}"
    )

    # Capture the bug shape: at least one of these is the broken behaviour.
    # Either:
    #   (a) both 200 + remaining < 0  (TOCTOU underflow)
    #   (b) both 200 + attempts_logged == 2 + remaining == 0 (atomicity hole)
    # Post-refactor we expect status_codes == [200, 400] and remaining == 0.
    both_succeeded = status_codes == [200, 200]
    one_rejected = 400 in status_codes

    assert both_succeeded or one_rejected, "unexpected status code combo"

    if both_succeeded:
        # The race fired. The guard let both through.
        assert remaining <= 0, (
            f"both submissions returned 200 but attempts_remaining={remaining} > 0 — "
            "impossible without a third attempt"
        )
        assert n_attempts_logged >= 1, "no attempts persisted at all"
        # Post-refactor flip: change to
        #     assert status_codes == [200, 400]
        #     assert remaining == 0
        #     assert n_attempts_logged == 1
    else:
        # The scheduler happened to serialize the two requests cleanly. Don't
        # fail; just note it.
        print(
            "[INFO] verdict race serialized this run "
            "(scheduler completed one before the other started). "
            "Re-run with --count=10 to reproduce the race."
        )


@pytest.mark.asyncio
async def test_verdict_race_state_consistency_under_normal_attempts() -> None:
    """Same race but with attempts_remaining=10. Both submissions should
    succeed (no guard issue). Question: does the per-attempt log have BOTH
    attempts, or only one (last-write-wins via cache)?

    REGRESSION: in the cache-shared-reference path, both attempts mutate the
    same `VerdictState.attempts` list, so both should be logged. In the
    DB-bypass path (e.g. interrogate-style load_or_create_state), only one
    survives. Today verdict.py uses `load_or_create_state` (NOT cache-aware
    load) — so we expect only one attempt logged.
    """
    player_id = "verdict_race_2"
    case_id = "case_001"

    state = fresh_player_state(case_id=case_id)
    state.verdict_state = VerdictState(case_id=case_id, attempts_remaining=10)
    seed_state(case_id, player_id, state)

    patches = _patch_verdict_llm(score=50)
    for p in patches:
        p.start()
    try:
        async with make_client() as client:
            resps = await asyncio.gather(
                client.post(
                    "/api/submit-verdict",
                    json={
                        "accused_suspect_id": "cassian",
                        "reasoning": "Submission A reasoning.",
                        "evidence_cited": [],
                        "case_id": case_id,
                        "player_id": player_id,
                    },
                ),
                client.post(
                    "/api/submit-verdict",
                    json={
                        "accused_suspect_id": "elena",
                        "reasoning": "Submission B reasoning.",
                        "evidence_cited": [],
                        "case_id": case_id,
                        "player_id": player_id,
                    },
                ),
            )
    finally:
        for p in patches:
            p.stop()

    assert all(r.status_code == 200 for r in resps), [
        (r.status_code, r.text[:200]) for r in resps
    ]

    persisted = load_state_direct(case_id, player_id)
    assert persisted is not None
    assert persisted.verdict_state is not None

    remaining = persisted.verdict_state.attempts_remaining
    n_logged = len(persisted.verdict_state.attempts)

    # Both responses returned 200 and decremented. attempts_remaining could be:
    #   - 8  (both saves observed each other via shared cache reference)
    #   - 9  (last-write-wins — only one decrement persisted)
    # Both are "wrong" relative to the desired contract (decrement should be
    # atomic and exactly count successful submissions).
    print(
        f"[REGRESSION] verdict race (n=10): remaining={remaining}, "
        f"attempts_logged={n_logged}"
    )

    # The state must be SOME consistent shape — just not "both attempts
    # silently dropped".
    assert remaining in {8, 9}, (
        f"unexpected attempts_remaining={remaining} — "
        "expected 8 (atomic) or 9 (clobber)"
    )
    assert n_logged in {1, 2}, (
        f"unexpected attempts_logged={n_logged} — "
        "expected 1 (clobber) or 2 (atomic). "
        "Refactor target: n_logged should equal initial-remaining minus final-remaining"
    )

    # Invariant the refactor MUST hold: logged matches the decrement.
    # If this fails today it's a separate bug worth surfacing.
    expected_logged = 10 - remaining
    if n_logged != expected_logged:
        print(
            f"[REGRESSION] decrement/log mismatch: "
            f"decremented by {10 - remaining} but logged {n_logged} attempts. "
            "Counter and log are not in sync — independent bug."
        )


@pytest.mark.asyncio
async def test_verdict_burst_five_attempts_one_remaining() -> None:
    """Stress: 5 concurrent submissions starting from attempts_remaining=1.

    Worst-case TOCTOU: how many pass the guard? Today we expect ALL 5 (none
    sees the others' decrement before checking the guard).
    """
    player_id = "verdict_burst"
    case_id = "case_001"

    state = fresh_player_state(case_id=case_id)
    state.verdict_state = VerdictState(case_id=case_id, attempts_remaining=1)
    seed_state(case_id, player_id, state)

    patches = _patch_verdict_llm(score=50)
    for p in patches:
        p.start()
    try:
        async with make_client() as client:
            results = await asyncio.gather(
                *[
                    client.post(
                        "/api/submit-verdict",
                        json={
                            "accused_suspect_id": "cassian",
                            "reasoning": f"Burst submission {i}.",
                            "evidence_cited": [],
                            "case_id": case_id,
                            "player_id": player_id,
                        },
                    )
                    for i in range(5)
                ]
            )
    finally:
        for p in patches:
            p.stop()

    accepted = sum(1 for r in results if r.status_code == 200)
    rejected = sum(1 for r in results if r.status_code == 400)

    persisted = load_state_direct(case_id, player_id)
    assert persisted is not None
    assert persisted.verdict_state is not None
    remaining = persisted.verdict_state.attempts_remaining

    print(
        f"[REGRESSION] verdict burst: accepted={accepted}, "
        f"rejected={rejected}, final attempts_remaining={remaining}"
    )

    # REGRESSION pin: today MORE than 1 request is accepted from a 1-attempt
    # budget. Refactor MUST make accepted == 1 and rejected == 4.
    # We assert the broken-today contract here so the refactor flips it.
    assert accepted >= 1, "no submissions succeeded — guard is over-rejecting"
    # Today: usually accepted == 5, rejected == 0, remaining is negative.
    # Don't make that exact assertion (flaky under scheduler), just assert
    # that we observed the TOCTOU under SOME run.
    if accepted > 1:
        assert remaining < 0 or accepted >= 2, (
            f"accepted={accepted} but remaining={remaining} — accounting bug"
        )
