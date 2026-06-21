"""Matthew Croft spirit companion endpoints: triggers, auto-comments, direct chat."""

import asyncio
import logging
import random

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.api.dependencies import get_authenticated_player_id
from src.api.helpers import (
    build_case_context,
    get_witness_history_summary,
    load_case_or_404,
    load_or_create_state,
    save_slot_state,
)
from src.api.rate_limit import LLM_RATE, limiter
from src.api.schemas import (
    InnerVoiceCheckRequest,
    InnerVoiceTriggerResponse,
    MatthewAutoCommentRequest,
    MatthewChatRequest,
    MatthewResponseModel,
)
from src.case_store.loader import get_evidence_details_for_ids, get_location
from src.telemetry.logger import log_event

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_evidence_details(
    case_id: str,
    case_data: dict,
    discovered_ids: list[str],
) -> list[dict]:
    """Get full details for discovered evidence via cached index."""
    return get_evidence_details_for_ids(case_id, case_data, discovered_ids)


def _get_location_description(case_data: dict, current_location: str) -> str:
    """Get current location description, with fallback."""
    try:
        location = get_location(case_data, current_location)
        return location.get("description", "")
    except KeyError:
        return "Unknown location"


async def _generate_matthew_with_fallback(
    case_data: dict,
    state,
    companion_state,
    user_message: str | None = None,
) -> tuple[str, str]:
    """Generate Matthew's response via LLM with template fallback."""
    from src.context.matthew_llm import generate_matthew_response, get_matthew_fallback_response

    case_context = build_case_context(case_data)
    evidence_discovered = _get_evidence_details(
        state.case_id, case_data, state.discovered_evidence
    )
    location_desc = _get_location_description(case_data, state.current_location)
    witness_history = get_witness_history_summary(state)

    try:
        return await generate_matthew_response(
            case_context=case_context,
            evidence_discovered=evidence_discovered,
            trust_level=companion_state.trust_level,
            conversation_history=companion_state.conversation_history,
            mode=None,
            user_message=user_message,
            location_description=location_desc,
            witness_history=witness_history,
            language=getattr(state, "language", "en"),
        )
    except Exception as e:
        logger.warning(f"Matthew LLM failed, using fallback: {e}")
        mode_used = "helpful" if random.random() < 0.5 else "misleading"
        response_text = get_matthew_fallback_response(mode_used, len(state.discovered_evidence))
        return response_text, mode_used


@router.post(
    "/case/{case_id}/matthew/triggers/check",
    response_model=InnerVoiceTriggerResponse,
    responses={404: {"description": "No eligible triggers available"}},
)
@limiter.limit(LLM_RATE)
async def check_matthew_trigger(
    request: Request,
    case_id: str,
    body: InnerVoiceCheckRequest,
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = "autosave",
) -> InnerVoiceTriggerResponse:
    """Check legacy YAML triggers for Matthew companion (optional)."""
    from src.context.matthew_triggers import load_matthew_triggers, select_matthew_trigger

    case_data = load_case_or_404(case_id)
    state = load_or_create_state(case_id, player_id, case_data, slot=slot)
    companion_state = state.get_matthew_companion_state()

    triggers_by_tier = load_matthew_triggers(case_id)
    if not triggers_by_tier:
        raise HTTPException(status_code=404, detail="No companion triggers configured")

    trigger = select_matthew_trigger(
        triggers_by_tier,
        body.evidence_count,
        companion_state.fired_triggers,
    )

    if not trigger:
        raise HTTPException(status_code=404, detail="No eligible triggers")

    companion_state.fire_trigger(
        trigger_id=trigger["id"],
        text=trigger["text"],
        trigger_type=trigger["type"],
        tier=trigger["tier"],
        evidence_count=body.evidence_count,
    )

    await asyncio.to_thread(save_slot_state, state, player_id, slot)

    return InnerVoiceTriggerResponse(
        id=trigger["id"],
        text=trigger["text"],
        type=trigger["type"],
        tier=trigger["tier"],
        updated_state=state.model_dump(mode="json"),
    )


@router.post(
    "/case/{case_id}/matthew/auto-comment",
    response_model=MatthewResponseModel,
    responses={204: {"description": "Matthew chose not to comment (30% chance)"}},
)
@limiter.limit(LLM_RATE)
async def matthew_auto_comment(
    request: Request,
    case_id: str,
    body: MatthewAutoCommentRequest,
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = "autosave",
) -> MatthewResponseModel | Response:
    """Generate Matthew's automatic comment after evidence discovery."""
    from src.context.matthew_llm import check_matthew_should_comment

    case_data = load_case_or_404(case_id)

    should_comment = await check_matthew_should_comment(body.is_critical)
    if not should_comment:
        return Response(status_code=204)

    state = load_or_create_state(case_id, player_id, case_data, slot=slot)
    companion_state = state.get_matthew_companion_state()

    response_text, mode_used = await _generate_matthew_with_fallback(
        case_data,
        state,
        companion_state,
    )

    companion_state.add_matthew_comment(None, response_text)
    state.add_conversation_message("matthew", response_text)
    await asyncio.to_thread(save_slot_state, state, player_id, slot)

    await log_event(
        "matthew_triggered",
        player_id,
        case_id,
        {
            "mode": mode_used,
        },
    )

    return MatthewResponseModel(
        text=response_text,
        mode=f"auto_{mode_used}",
        trust_level=companion_state.get_trust_percentage(),
        updated_state=state.model_dump(mode="json"),
    )


@router.post("/case/{case_id}/matthew/chat", response_model=MatthewResponseModel)
@limiter.limit(LLM_RATE)
async def matthew_direct_chat(
    request: Request,
    case_id: str,
    body: MatthewChatRequest,
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = "autosave",
) -> MatthewResponseModel:
    """Handle direct conversation with Matthew."""
    case_data = load_case_or_404(case_id)
    state = load_or_create_state(case_id, player_id, case_data, slot=slot)
    companion_state = state.get_matthew_companion_state()

    response_text, mode_used = await _generate_matthew_with_fallback(
        case_data,
        state,
        companion_state,
        user_message=body.message,
    )

    companion_state.add_matthew_comment(body.message, response_text)
    state.add_conversation_message("player", body.message)
    state.add_conversation_message("matthew", response_text)
    await asyncio.to_thread(save_slot_state, state, player_id, slot)

    return MatthewResponseModel(
        text=response_text,
        mode=f"direct_chat_{mode_used}",
        trust_level=companion_state.get_trust_percentage(),
        updated_state=state.model_dump(mode="json"),
    )
