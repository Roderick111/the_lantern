"""Shared helpers for auth-baseline and save-slot tests.

These tests intentionally exercise the pre-refactor "anyone can act as any
player_id" surface. Helpers are kept small + intentionally documented so the
post-refactor flip (AUTH_BASELINE -> 401/403) is mechanical.

Pure helper module — no pytest fixtures here (ruff false-positives on
fixture import shadowing). Test files declare their own fixtures.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from httpx import AsyncClient

# ============================================================================
# Marker tags (grep these later when flipping post-refactor)
# ============================================================================
# AUTH_BASELINE — captures the CURRENT no-auth contract. Post-refactor: flip.
# REGRESSION    — captures undesirable current behavior. Post-refactor: flip.


# ----------------------------------------------------------------------------
# Sample state payloads
# ----------------------------------------------------------------------------


def make_state(
    *,
    case_id: str = "case_001",
    current_location: str = "library",
    discovered_evidence: list[str] | None = None,
    visited_locations: list[str] | None = None,
) -> dict[str, Any]:
    """Build a minimal-but-valid PlayerState dict for SaveRequest.state."""
    return {
        "case_id": case_id,
        "current_location": current_location,
        "discovered_evidence": discovered_evidence or [],
        "visited_locations": visited_locations or [current_location],
    }


async def save_autosave(
    client: AsyncClient,
    *,
    player_id: str,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """POST /api/save → autosave slot. Returns response JSON."""
    payload = {
        "player_id": player_id,
        "state": state or make_state(),
        "slot": "autosave",
    }
    r = await client.post("/api/save", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


async def load_slot(
    client: AsyncClient,
    *,
    case_id: str,
    player_id: str,
    slot: str = "autosave",
) -> tuple[int, Any]:
    """GET /api/load/{case_id}. Returns (status_code, json_body)."""
    r = await client.get(
        f"/api/load/{case_id}",
        params={"player_id": player_id, "slot": slot},
    )
    return r.status_code, r.json()


def db_path() -> Path:
    """Resolve the SQLite path used by production code.

    Mirrors `src.state.persistence._DB_PATH` resolution logic.
    """
    saves_dir = Path("/app/saves")
    if saves_dir.exists():
        return saves_dir / "lantern.db"
    env_path = os.environ.get("LANTERN_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).parent.parent / "saves" / "lantern.db"
