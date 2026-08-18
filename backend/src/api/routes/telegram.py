"""Internal Telegram gateway endpoints.

Compact snapshots only — never expose solution, hidden evidence, secrets, or keys.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_authenticated_player_id
from src.api.helpers import load_localized_case_or_404, load_slot_state
from src.api.schemas import (
    TelegramEvidenceSnapshot,
    TelegramLocationSnapshot,
    TelegramSnapshotResponse,
    TelegramWitnessSnapshot,
)
from src.case_store.loader import (
    build_evidence_index,
    get_first_location_id,
    get_location,
    get_witness,
    list_locations,
    list_witnesses,
)
from src.state.player_state import PlayerState

router = APIRouter()


@router.get(
    "/telegram/snapshot/{case_id}",
    response_model=TelegramSnapshotResponse,
)
async def get_telegram_snapshot(
    case_id: str,
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = Query(default="autosave", pattern=r"^[a-zA-Z0-9_]+$"),
) -> TelegramSnapshotResponse:
    """Compact case snapshot for Telegram gateway job recovery."""
    state = load_slot_state(case_id, player_id, slot)
    language = getattr(state, "language", "en") if state else "en"
    case_data = load_localized_case_or_404(case_id, language)

    if state is None:
        first_location = get_first_location_id(case_data)
        state = PlayerState(case_id=case_id, current_location=first_location)

    briefing_completed = False
    if state.briefing_state is not None:
        briefing_completed = state.briefing_state.briefing_completed

    attempts_remaining = 10
    case_solved = False
    if state.verdict_state is not None:
        attempts_remaining = state.verdict_state.attempts_remaining
        case_solved = state.verdict_state.case_solved

    witness_ids = list_witnesses(case_data)
    available_witnesses: list[TelegramWitnessSnapshot] = []
    for witness_id in witness_ids:
        witness = get_witness(case_data, witness_id)
        available_witnesses.append(
            TelegramWitnessSnapshot(
                id=witness_id,
                name=witness.get("name", "Unknown"),
                description=witness.get("description", ""),
            )
        )

    current_location = get_location(case_data, state.current_location)
    available_locations = [
        TelegramLocationSnapshot(
            id=location["id"],
            name=location.get("name", location["id"]),
            description=location.get("description", ""),
        )
        for location in list_locations(case_data)
    ]
    evidence_index = build_evidence_index(case_data)
    location_map = {location["id"]: location for location in list_locations(case_data)}
    evidence_details = [
        TelegramEvidenceSnapshot(
            id=evidence_id,
            name=evidence_index[evidence_id].get("name", evidence_id),
            description=evidence_index[evidence_id].get("description", ""),
            location_found=evidence_index[evidence_id].get("location_found", ""),
            type=evidence_index[evidence_id].get("type", ""),
            location_name=location_map.get(
                evidence_index[evidence_id].get("location_found", ""),
                {},
            ).get("name", ""),
        )
        for evidence_id in state.discovered_evidence
        if evidence_id in evidence_index
    ]
    case_section = case_data.get("case", case_data)

    return TelegramSnapshotResponse(
        case_id=case_id,
        case_title=case_section.get("title", ""),
        case_description=case_section.get("description", ""),
        current_location=state.current_location,
        current_location_view=TelegramLocationSnapshot(
            id=state.current_location,
            name=current_location.get("name", state.current_location),
            description=current_location.get("description", ""),
        ),
        available_locations=available_locations,
        visited_locations=list(state.visited_locations),
        discovered_evidence=list(state.discovered_evidence),
        evidence_details=evidence_details,
        briefing_completed=briefing_completed,
        language=state.language,
        save_revision=state.save_revision,
        available_witnesses=available_witnesses,
        verdict_attempts_remaining=attempts_remaining,
        case_solved=case_solved,
    )
