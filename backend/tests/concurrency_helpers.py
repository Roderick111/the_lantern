"""Helpers for concurrency / race-condition tests.

NOT a conftest.py — must be imported explicitly. Provides:

* `make_client`           — fresh httpx AsyncClient against the FastAPI app
* `slow_stream_mock`      — async generator that sleeps between yielded chunks
* `make_text_mock`        — non-streaming response, configurable per-call
* `make_evaluator_mock`   — fixed verdict-evaluator result (avoid real LLM)
* `make_graves_mock`       — fixed mentor feedback text
* `clear_state_cache`     — wipe `_state_cache` between tests
* `fresh_player_state`    — build a minimal PlayerState for direct seeding
* `seed_state`            — drop a PlayerState into the mocked persistence layer
* `load_state_direct`     — read back from mocked persistence
* `bypass_state_cache_load` / `bypass_state_cache_save` — monkeypatch the cache
  layer to talk straight to mocked persistence (so writes/reads through the
  cache + DB path are exercised without the cache stashing stale objects
  between concurrent calls).

These helpers are deliberately permissive: tests can pick the level of mocking
they need (cache-on vs cache-off; one mocked LLM payload per request).
"""

from __future__ import annotations

import asyncio
import importlib
import json
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.state.player_state import PlayerState

# ── Client ────────────────────────────────────────────────────────────────────


def make_client() -> AsyncClient:
    """Build an httpx AsyncClient bound to the FastAPI app.

    The caller is responsible for using it as an async context manager.
    """
    from src.main import app

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test", timeout=30.0)


# ── LLM mocks ─────────────────────────────────────────────────────────────────


def slow_stream_mock(
    chunks: list[str],
    delay_s: float = 0.05,
) -> Callable[..., AsyncIterator[str]]:
    """Return an async-generator factory yielding `chunks` with sleep between."""

    async def _gen(*_args: Any, **_kwargs: Any) -> AsyncIterator[str]:
        for chunk in chunks:
            await asyncio.sleep(delay_s)
            yield chunk

    return _gen


def make_streaming_client_mock(
    chunks: list[str],
    delay_s: float = 0.05,
) -> AsyncMock:
    """Build a LLMClient-shaped AsyncMock whose `get_response_stream` is slow."""
    client = AsyncMock()
    client.get_response_stream = slow_stream_mock(chunks, delay_s=delay_s)
    # Some routes hit `get_response` (non-stream). Provide a sane default.
    full_text = "".join(chunks)
    client.get_response = AsyncMock(return_value=full_text)
    return client


def make_text_mock(text: str) -> AsyncMock:
    """Non-streaming LLM mock returning a fixed string."""
    client = AsyncMock()
    client.get_response = AsyncMock(return_value=text)

    async def _stream(*_a: Any, **_kw: Any) -> AsyncIterator[str]:
        yield text

    client.get_response_stream = _stream
    return client


def make_evaluator_result(
    score: int = 50,
    quality: str = "fair",
) -> dict[str, Any]:
    """Canned evaluator output shaped like `evaluate_reasoning_llm` return."""
    return {
        "score": score,
        "quality": quality,
        "summary": "test summary",
        "strengths": [],
        "weaknesses": [],
        "fallacies": [],
    }


# ── State cache + persistence helpers ────────────────────────────────────────


def clear_state_cache() -> None:
    """Wipe the module-level `_state_cache` between tests."""
    from src.api import helpers

    helpers._state_cache.clear()


def state_cache_snapshot() -> dict[tuple[str, str, str], PlayerState]:
    """Return a shallow copy of `_state_cache` for assertions."""
    from src.api import helpers

    return dict(helpers._state_cache)


def fresh_player_state(
    case_id: str = "case_001",
    current_location: str = "library",
    **overrides: Any,
) -> PlayerState:
    """Build a minimal valid PlayerState (matches model_dump round-trip)."""
    state = PlayerState(case_id=case_id, current_location=current_location)
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


def seed_state(
    case_id: str,
    player_id: str,
    state: PlayerState,
    slot: str = "autosave",
) -> None:
    """Push state into the mocked persistence (`_mem_store` in conftest)."""
    from tests.conftest import _mem_store

    state_json = json.loads(json.dumps(state.model_dump(mode="json"), default=str))
    slot_key = "autosave" if slot == "default" else slot
    _mem_store[(player_id, case_id, slot_key)] = state_json


def load_state_direct(
    case_id: str,
    player_id: str,
    slot: str = "autosave",
) -> PlayerState | None:
    """Read back from `_mem_store`, bypassing the in-memory state cache."""
    from tests.conftest import _mem_store

    slot_key = "autosave" if slot == "default" else slot
    data = _mem_store.get((player_id, case_id, slot_key))
    if data is None:
        return None
    return PlayerState(**data)


# ── Bypass-cache patches ─────────────────────────────────────────────────────
#
# `helpers.load_slot_state` consults `_state_cache` first. For race tests the
# cache hides DB-level races (and adds its own). These helpers patch the cache
# layer to delegate straight to mocked persistence. Tests choose: cache-on or
# cache-off.


def bypass_state_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `load_slot_state` / `save_slot_state` skip the cache entirely.

    Each call reads/writes through the mocked persistence layer (`_mem_store`),
    so concurrent requests see fresh state on every read — surfacing the DB-side
    last-write-wins race rather than the cache-shared-object race.
    """
    from src.api import helpers

    def _load(case_id: str, player_id: str, slot: str = "autosave"):
        return load_state_direct(case_id, player_id, slot)

    def _save(state: PlayerState, player_id: str, slot: str = "autosave") -> None:
        seed_state(state.case_id, player_id, state, slot)

    monkeypatch.setattr(helpers, "load_slot_state", _load)
    monkeypatch.setattr(helpers, "save_slot_state", _save)

    # Routes import these names directly; patch import sites too.
    for mod_path in (
        "src.api.routes.investigation",
        "src.api.routes.witnesses",
        "src.api.routes.verdict",
        "src.api.routes.saves",
        "src.api.routes.mnemonic_delving",
        "src.api.routes.briefing",
        "src.api.routes.matthew",
        "src.api.routes.evidence",
    ):
        try:
            mod = importlib.import_module(mod_path)
        except ImportError:
            continue
        if hasattr(mod, "load_slot_state"):
            monkeypatch.setattr(f"{mod_path}.load_slot_state", _load, raising=False)
        if hasattr(mod, "save_slot_state"):
            monkeypatch.setattr(f"{mod_path}.save_slot_state", _save, raising=False)


# ── SSE parsing ──────────────────────────────────────────────────────────────


def parse_sse_events(body: str) -> list[dict[str, Any]]:
    """Parse SSE-formatted text body into a list of decoded JSON payloads.

    Ignores comments (lines starting with `:`).
    """
    events: list[dict[str, Any]] = []
    for line in body.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[len("data: ") :].strip()
        if not payload:
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return events


def find_done_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the SSE event with `done: true`, if any."""
    for ev in events:
        if ev.get("done"):
            return ev
    return None


# ── Iteration helper for stress loops ─────────────────────────────────────────


def stress_iterations(n: int = 1) -> Iterator[int]:
    """Yield 0..n-1 — small helper to make stress loops obvious in tests."""
    yield from range(n)
