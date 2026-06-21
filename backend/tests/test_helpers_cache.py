"""Tests for in-memory state cache isolation in api.helpers."""

from src.api.helpers import clear_state_cache, load_slot_state, save_slot_state
from src.state.player_state import PlayerState


def test_load_slot_state_returns_isolated_copies() -> None:
    """Mutating one loaded state must not affect a subsequent load."""
    clear_state_cache()
    player_id = "cache_isolation_player"
    case_id = "case_001"

    base = PlayerState(case_id=case_id, current_location="library")
    base.discovered_evidence.append("evidence_a")
    save_slot_state(base, player_id, "autosave")

    first = load_slot_state(case_id, player_id, "autosave")
    second = load_slot_state(case_id, player_id, "autosave")

    assert first is not None
    assert second is not None
    assert first is not second
    assert first.discovered_evidence is not second.discovered_evidence

    first.discovered_evidence.append("evidence_b")

    third = load_slot_state(case_id, player_id, "autosave")
    assert third is not None
    assert "evidence_b" not in third.discovered_evidence