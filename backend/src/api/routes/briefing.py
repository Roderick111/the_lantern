"""Briefing endpoints: case assignment, teaching questions, Graves Q&A."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from src.api.dependencies import UserLLMConfig, get_authenticated_player_id, get_user_llm_config
from src.api.errors import llm_http_exception
from src.api.helpers import (
    load_case_or_404,
    load_localized_case_or_404,
    load_or_create_state,
    load_slot_state,
    save_slot_state,
)
from src.api.llm_client import LLMClientError
from src.api.rate_limit import LLM_RATE, limiter
from src.api.schemas import (
    BriefingCompleteRequest,
    BriefingCompleteResponse,
    BriefingContent,
    BriefingQuestionRequest,
    BriefingQuestionResponse,
    CaseDossier,
    TeachingChoice,
    TeachingQuestion,
)
from src.context.briefing import ask_graves_question
from src.state.idempotency import IdempotencyGuard
from src.telemetry.logger import log_event

logger = logging.getLogger(__name__)
router = APIRouter()


def _load_briefing_content(
    case_id: str,
    player_id: str | None = None,
    slot: str = "autosave",
) -> dict[str, Any]:
    """Load briefing content from case YAML."""
    state = load_slot_state(case_id, player_id, slot) if player_id else None
    case_data = load_localized_case_or_404(
        case_id,
        getattr(state, "language", "en") if state else "en",
    )
    case_section = case_data.get("case", case_data)
    briefing: dict[str, Any] | None = case_section.get("briefing")

    if not briefing:
        raise HTTPException(status_code=404, detail=f"No briefing section in case: {case_id}")

    return briefing


@router.get("/briefing/{case_id}", response_model=BriefingContent)
async def get_briefing(
    case_id: str,
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = "autosave",
) -> BriefingContent:
    """Load briefing content for a case."""
    briefing = _load_briefing_content(case_id, player_id, slot)

    dossier_data = briefing.get("dossier", {})
    dossier = CaseDossier(
        title=dossier_data.get("title", "CLASSIFIED"),
        victim=dossier_data.get("victim", "Unknown"),
        location=dossier_data.get("location", "Unknown"),
        time=dossier_data.get("time", "Unknown"),
        status=dossier_data.get("status", "Unknown"),
        synopsis=dossier_data.get("synopsis", ""),
    )

    questions_data = briefing.get("teaching_questions", [])
    if not questions_data and "teaching_question" in briefing:
        questions_data = [briefing["teaching_question"]]

    teaching_questions = []
    for q_data in questions_data:
        choices_data = q_data.get("choices", [])
        choices = [
            TeachingChoice(
                id=c.get("id", ""),
                text=c.get("text", ""),
                response=c.get("response", ""),
            )
            for c in choices_data
        ]
        teaching_questions.append(
            TeachingQuestion(
                prompt=q_data.get("prompt", ""),
                choices=choices,
                concept_summary=q_data.get("concept_summary", ""),
            )
        )

    state = load_slot_state(case_id, player_id, slot)
    briefing_completed = False
    if state and state.briefing_state:
        briefing_completed = state.briefing_state.briefing_completed

    return BriefingContent(
        case_id=case_id,
        dossier=dossier,
        teaching_questions=teaching_questions,
        rationality_concept=briefing.get("rationality_concept", ""),
        concept_description=briefing.get("concept_description", ""),
        transition=briefing.get("transition", ""),
        briefing_completed=briefing_completed,
    )


@router.post("/briefing/{case_id}/question", response_model=BriefingQuestionResponse)
@limiter.limit(LLM_RATE)
async def ask_briefing_question(
    request: Request,
    case_id: str,
    body: BriefingQuestionRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
) -> BriefingQuestionResponse:
    """Ask Graves a question during briefing."""
    player_id = player_id
    briefing = _load_briefing_content(case_id, player_id, body.slot)

    state = load_slot_state(case_id, player_id, body.slot)
    case_data = load_localized_case_or_404(
        case_id,
        getattr(state, "language", "en") if state else "en",
    )
    case_section = case_data.get("case", case_data)
    briefing_context = case_section.get("briefing_context", {})

    if state is None:
        state = load_or_create_state(case_id, player_id, case_data, slot=body.slot)

    briefing_state = state.get_briefing_state()

    dossier = briefing.get("dossier", {})
    teaching_questions = briefing.get("teaching_questions", [])
    first_question = teaching_questions[0] if teaching_questions else {}

    case_assignment = f"""VICTIM: {dossier.get("victim", "Unknown")}
LOCATION: {dossier.get("location", "Unknown")}
TIME: {dossier.get("time", "Unknown")}
STATUS: {dossier.get("status", "Unknown")}
SYNOPSIS: {dossier.get("synopsis", "")}"""

    try:
        answer = await ask_graves_question(
            question=body.question,
            case_assignment=case_assignment,
            teaching_moment=first_question.get("prompt", ""),
            rationality_concept=first_question.get("concept_summary", ""),
            concept_description=first_question.get("concept_summary", ""),
            conversation_history=briefing_state.conversation_history,
            briefing_context=briefing_context,
            api_key=llm_config.api_key,
            model=llm_config.model,
            language=state.language,
        )
    except LLMClientError as e:
        raise llm_http_exception(e) from e

    briefing_state.add_question(body.question, answer)
    save_slot_state(state, player_id, body.slot)

    await log_event(
        "briefing_question",
        player_id,
        case_id,
        {
            "question": body.question[:100],
        },
    )

    return BriefingQuestionResponse(
        answer=answer,
        updated_state=state.model_dump(mode="json"),
    )


@router.post("/briefing/{case_id}/complete", response_model=BriefingCompleteResponse)
async def complete_briefing(
    case_id: str,
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = Query(default="autosave", pattern=r"^[a-zA-Z0-9_]+$"),
    body: BriefingCompleteRequest | None = Body(default=None),
) -> BriefingCompleteResponse:
    """Mark briefing as completed.

    Accepts optional JSON body (slot + request_id). Query-only callers still work.
    """
    effective_slot = body.slot if body is not None else slot
    request_id = body.request_id if body is not None else None

    guard = IdempotencyGuard(player_id, "briefing_complete", request_id)
    early = guard.begin()
    if early is not None:
        return BriefingCompleteResponse.model_validate(early)

    case_data = load_case_or_404(case_id)
    state = load_or_create_state(case_id, player_id, case_data, slot=effective_slot)

    state.mark_briefing_complete()
    await asyncio.to_thread(save_slot_state, state, player_id, effective_slot)

    await log_event("briefing_complete", player_id, case_id, {})

    result = BriefingCompleteResponse(
        success=True,
        updated_state=state.model_dump(mode="json"),
    )
    guard.complete(result)
    return result
