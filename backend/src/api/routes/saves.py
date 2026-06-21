"""Save/load/delete game state endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.api.dependencies import get_authenticated_player_id
from src.api.helpers import invalidate_state_cache, load_slot_state, save_slot_state
from src.api.rate_limit import SAVE_LOAD_RATE, limiter
from src.api.schemas import (
    ChangeLocationRequest,
    ChangeLocationResponse,
    LocationInfo,
    ResetResponse,
    SaveRequest,
    SaveResponse,
    SaveSlotMetadata,
    SaveSlotResponse,
    SaveSlotsListResponse,
    StateResponse,
    UpdateSettingsRequest,
    UpdateSettingsResponse,
)
from src.case_store.loader import get_first_location_id, get_location, list_locations, load_case
from src.state.exceptions import StaleStateError
from src.state.persistence import (
    delete_player_save,
    list_player_saves,
    load_player_state,
    migrate_old_save,
)
from src.state.player_state import PlayerState
from src.telemetry.logger import log_event

logger = logging.getLogger(__name__)
router = APIRouter()


def _merge_client_save_fields(state: PlayerState, request_state: dict) -> None:
    """Apply only client-allowed fields — server-owned subgraphs stay intact."""
    if "current_location" in request_state:
        state.current_location = request_state["current_location"]
    if "discovered_evidence" in request_state:
        state.discovered_evidence = list(request_state["discovered_evidence"])
    if "visited_locations" in request_state:
        state.visited_locations = list(request_state["visited_locations"])
    if "narrator_verbosity" in request_state:
        verbosity = request_state["narrator_verbosity"]
        if verbosity in ("concise", "storyteller", "atmospheric"):
            state.narrator_verbosity = verbosity
    if "language" in request_state:
        state.language = request_state["language"]


def _new_state_from_client(case_id: str, request_state: dict) -> PlayerState:
    """Create a fresh PlayerState from the client slice — no arbitrary field injection."""
    try:
        case_data = load_case(case_id)
        first_location = get_first_location_id(case_data)
    except (FileNotFoundError, ValueError):
        first_location = request_state.get("current_location", "library")

    state = PlayerState(
        case_id=case_id,
        current_location=request_state.get("current_location", first_location),
    )
    _merge_client_save_fields(state, request_state)
    return state


def _build_save_state(
    case_id: str,
    player_id: str,
    slot: str,
    request_state: dict,
) -> PlayerState:
    """Build authoritative save state — server-owned subgraphs preserved on autosave."""
    if slot != "autosave":
        autosave = load_player_state(case_id, player_id, "autosave")
        if autosave:
            return autosave
        return _new_state_from_client(case_id, request_state)

    existing = load_slot_state(case_id, player_id, slot)
    if existing:
        _merge_client_save_fields(existing, request_state)
        return existing
    return _new_state_from_client(case_id, request_state)


@router.post("/save", response_model=SaveResponse)
@limiter.limit(SAVE_LOAD_RATE)
async def save_game(
    request: Request,
    body: SaveRequest,
    player_id: str = Depends(get_authenticated_player_id),
) -> SaveResponse:
    """Save player game state to specific slot."""
    player_id = player_id
    slot = body.slot
    try:
        case_id = body.state.get("case_id", "case_001")
        state = _build_save_state(case_id, player_id, slot, body.state)
        save_slot_state(state, player_id, slot)

        if slot != "autosave":
            await log_event("save_game", player_id, case_id, {"slot": slot})

        return SaveResponse(success=True, message=f"Saved to {slot}", slot=slot)
    except StaleStateError:
        return SaveResponse(
            success=False,
            message="Save conflict — reload and try again.",
            slot=slot,
        )
    except ValueError as e:
        return SaveResponse(success=False, message=str(e), slot=slot)
    except Exception as e:
        return SaveResponse(success=False, message=f"Failed to save: {e}", slot=slot)


@router.post("/settings/update", response_model=UpdateSettingsResponse)
async def update_settings(
    request: UpdateSettingsRequest,
    player_id: str = Depends(get_authenticated_player_id),
) -> UpdateSettingsResponse:
    """Update player settings (narrator verbosity, etc.)."""
    player_id = player_id
    try:
        state = load_slot_state(request.case_id, player_id, request.slot)
        if not state:
            state = PlayerState(case_id=request.case_id)

        if request.narrator_verbosity:
            valid_options = ["concise", "storyteller", "atmospheric"]
            if request.narrator_verbosity not in valid_options:
                return UpdateSettingsResponse(
                    success=False,
                    message=f"Invalid verbosity. Must be one of: {', '.join(valid_options)}",
                )
            state.narrator_verbosity = request.narrator_verbosity

        if request.language:
            from src.config.language import SUPPORTED_LANGUAGES

            if request.language not in SUPPORTED_LANGUAGES:
                return UpdateSettingsResponse(
                    success=False,
                    message=f"Invalid language. Must be one of: {', '.join(SUPPORTED_LANGUAGES)}",
                )
            state.language = request.language

        save_slot_state(state, player_id, request.slot)
        return UpdateSettingsResponse(success=True, message="Settings updated successfully")
    except Exception as e:
        return UpdateSettingsResponse(success=False, message=f"Failed to update settings: {e}")


@router.get("/load/{case_id}", response_model=StateResponse)
@limiter.limit(SAVE_LOAD_RATE)
async def load_game(
    request: Request,
    case_id: str,
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = Query(default="autosave", description="Save slot"),
    location_id: str | None = Query(default=None, description="Current location context"),
) -> StateResponse:
    """Load player game state from specific slot."""
    try:
        state = load_player_state(case_id, player_id, slot)

        if state is None:
            raise HTTPException(
                status_code=404,
                detail=f"No save found for case {case_id} in slot {slot}",
            )

        # When loading from a named slot, copy to autosave so gameplay
        # continues seamlessly (all actions autosave to "autosave" slot)
        if slot != "autosave":
            save_slot_state(state, player_id, "autosave")
        else:
            invalidate_state_cache(case_id, player_id, "autosave")

        if slot != "autosave":
            await log_event("load_game", player_id, case_id, {"slot": slot})

        target_loc = location_id or state.current_location

        return StateResponse(
            case_id=state.case_id,
            current_location=state.current_location,
            discovered_evidence=state.discovered_evidence,
            visited_locations=state.visited_locations,
            conversation_history=state.location_chat_history.get(target_loc, []),
            narrator_verbosity=state.narrator_verbosity,
            language=state.language,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/state/{case_id}")
async def delete_game(
    case_id: str,
    player_id: str = Depends(get_authenticated_player_id),
) -> dict[str, bool]:
    """Delete player game state."""
    result = delete_player_save(case_id, player_id, "autosave")
    invalidate_state_cache(case_id, player_id, "autosave")
    return {"deleted": result}


@router.post("/case/{case_id}/reset", response_model=ResetResponse)
async def reset_case(
    case_id: str,
    player_id: str = Depends(get_authenticated_player_id),
) -> ResetResponse:
    """Reset case progress (delete saved state)."""
    deleted = delete_player_save(case_id, player_id, "autosave")
    invalidate_state_cache(case_id, player_id, "autosave")

    if deleted:
        return ResetResponse(
            success=True,
            message=f"Case {case_id} reset successfully.",
        )
    return ResetResponse(
        success=False,
        message=f"No active progress found for case {case_id}.",
    )


@router.get("/case/{case_id}/saves/list", response_model=SaveSlotsListResponse)
async def list_saves_endpoint(
    case_id: str,
    player_id: str = Depends(get_authenticated_player_id),
) -> SaveSlotsListResponse:
    """List all save slots with metadata for a player."""
    migrate_old_save(case_id, player_id)
    saves_data = list_player_saves(case_id, player_id)

    saves = [
        SaveSlotMetadata(
            slot=s["slot"],
            case_id=s.get("case_id", case_id),
            timestamp=s.get("timestamp"),
            location=s.get("location", "unknown"),
            evidence_count=s.get("evidence_count", 0),
            witnesses_interrogated=s.get("witnesses_interrogated", 0),
            progress_percent=s.get("progress_percent", 0),
            version=s.get("version", "1.0.0"),
        )
        for s in saves_data
    ]

    return SaveSlotsListResponse(case_id=case_id, saves=saves)


@router.delete("/case/{case_id}/saves/{slot}", response_model=SaveSlotResponse)
async def delete_save_slot_endpoint(
    case_id: str,
    slot: str,
    player_id: str = Depends(get_authenticated_player_id),
) -> SaveSlotResponse:
    """Delete a specific save slot."""
    valid_slots = {"slot_1", "slot_2", "slot_3", "autosave"}
    if slot not in valid_slots:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid slot: {slot}. Must be one of: {', '.join(valid_slots)}",
        )

    success = delete_player_save(case_id, player_id, slot)
    invalidate_state_cache(case_id, player_id, slot)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Save slot '{slot}' not found for case {case_id}",
        )

    return SaveSlotResponse(success=True, slot=slot, message=f"Deleted save slot {slot}")


@router.get("/case/{case_id}/locations", response_model=list[LocationInfo])
async def get_locations(case_id: str) -> list[LocationInfo]:
    """Get all locations for LocationSelector."""
    try:
        case_data = load_case(case_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    locations = list_locations(case_data)
    return [LocationInfo(**loc) for loc in locations]


@router.post("/case/{case_id}/change-location", response_model=ChangeLocationResponse)
async def change_location(
    case_id: str,
    request: ChangeLocationRequest,
    player_id: str = Depends(get_authenticated_player_id),
) -> ChangeLocationResponse:
    """Change player location."""
    player_id = player_id
    try:
        case_data = load_case(case_id)
        location = get_location(case_data, request.location_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Location not found: {request.location_id}")

    state = load_slot_state(case_id, player_id, request.slot)
    if state is None:
        state = PlayerState(case_id=case_id, current_location=request.location_id)

    state.visit_location(request.location_id)
    save_slot_state(state, player_id, request.slot)

    await log_event(
        "location_changed",
        player_id,
        case_id,
        {
            "location_id": request.location_id,
            "location_name": location.get("name", "Unknown"),
        },
    )

    return ChangeLocationResponse(
        success=True,
        location={
            "id": location.get("id", request.location_id),
            "name": location.get("name", "Unknown Location"),
            "description": location.get("description", ""),
            "surface_elements": location.get("surface_elements", []),
            "witnesses_present": location.get("witnesses_present", []),
        },
        updated_state=state.model_dump(mode="json"),
    )
