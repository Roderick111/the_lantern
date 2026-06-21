"""Verdict submission and mentor feedback endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.dependencies import UserLLMConfig, get_authenticated_player_id, get_user_llm_config
from src.api.helpers import load_case_or_404, load_or_create_state, save_slot_state
from src.api.rate_limit import LLM_RATE, limiter
from src.api.schemas import (
    ConfrontationDialogue,
    MentorFeedback,
    SubmitVerdictRequest,
    SubmitVerdictResponse,
)
from src.case_store.loader import (
    load_confrontation,
    load_mentor_templates,
    load_solution,
    load_wrong_verdict_info,
)
from src.context.mentor import (
    build_graves_feedback_llm,
    build_mentor_feedback,
    get_wrong_suspect_response,
)
from src.state.exceptions import StaleStateError
from src.state.player_state import VerdictState
from src.telemetry.logger import log_event
from src.verdict.evaluator import check_verdict
from src.verdict.llm_evaluator import evaluate_reasoning_llm

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/submit-verdict", response_model=SubmitVerdictResponse)
@limiter.limit(LLM_RATE)
async def submit_verdict(
    request: Request,
    body: SubmitVerdictRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
) -> SubmitVerdictResponse:
    """Submit verdict and get Graves mentor feedback."""
    # player_id injected via auth dep; body no longer carries it
    case_data = load_case_or_404(body.case_id)
    state = load_or_create_state(body.case_id, player_id, case_data, slot=body.slot)

    solution = load_solution(case_data)
    mentor_templates = load_mentor_templates(case_data)

    if not solution:
        raise HTTPException(status_code=500, detail="Case solution not configured")

    if state.verdict_state is None:
        state.verdict_state = VerdictState(case_id=body.case_id)

    verdict_state = state.verdict_state



    if verdict_state.attempts_remaining <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"No attempts remaining. You've used all {10 - verdict_state.attempts_remaining} attempts. Use 'Reset Case' to start over.",
        )

    correct = check_verdict(body.accused_suspect_id, solution)

    # Get case context for evaluator
    case_section = case_data.get("case", case_data)
    briefing_context = case_section.get("briefing_context", {})

    # LLM-based reasoning evaluation (replaces rule-based scoring)
    evaluator_result = await evaluate_reasoning_llm(
        correct=correct,
        reasoning=body.reasoning,
        accused_id=body.accused_suspect_id,
        evidence_cited=body.evidence_cited,
        discovered_evidence=list(state.discovered_evidence),
        solution=solution,
        case_context=briefing_context,
        api_key=llm_config.api_key,
        model=llm_config.model,
    )

    score = evaluator_result["score"]
    fallacies = evaluator_result.get("fallacies", [])

    verdict_state.add_attempt(
        body.accused_suspect_id,
        body.reasoning,
        body.evidence_cited,
        correct,
        score,
        fallacies,
    )

    build_mentor_feedback(
        correct=correct,
        score=score,
        fallacies=fallacies,
        reasoning=body.reasoning,
        accused_id=body.accused_suspect_id,
        solution=solution,
        feedback_templates=mentor_templates,
        attempts_remaining=verdict_state.attempts_remaining,
    )

    graves_text = await build_graves_feedback_llm(
        correct=correct,
        score=score,
        fallacies=fallacies,
        reasoning=body.reasoning,
        accused_id=body.accused_suspect_id,
        solution=solution,
        attempts_remaining=verdict_state.attempts_remaining,
        evidence_cited=body.evidence_cited,
        feedback_templates=mentor_templates,
        case_id=body.case_id,
        api_key=llm_config.api_key,
        model=llm_config.model,
        evaluator_result=evaluator_result,
        language=state.language,
    )

    mentor_feedback = MentorFeedback(
        analysis=graves_text,
        fallacies_detected=[],
        score=score,
        quality=evaluator_result["quality"],
        critique="",
        praise="",
        hint=None,
    )

    confrontation_response: ConfrontationDialogue | None = None
    if correct or verdict_state.attempts_remaining == 0:
        confrontation_data = load_confrontation(case_data, body.accused_suspect_id, correct)
        if confrontation_data:
            confrontation_response = ConfrontationDialogue(
                dialogue=confrontation_data["dialogue"],
                aftermath=confrontation_data["aftermath"],
            )

    wrong_suspect_response: str | None = None
    if not correct:
        wrong_suspect_response = get_wrong_suspect_response(
            body.accused_suspect_id,
            mentor_templates,
            verdict_state.attempts_remaining,
        )

    reveal: str | None = None
    if not correct and verdict_state.attempts_remaining == 0:
        culprit = solution.get("culprit", "unknown")
        method = solution.get("method", "")
        reveal = f"The actual culprit was {culprit}. {method}"

        wrong_info = load_wrong_verdict_info(case_data, body.accused_suspect_id)
        if wrong_info and wrong_info.get("reveal"):
            reveal = wrong_info["reveal"]

    try:
        save_slot_state(state, player_id, body.slot)
    except StaleStateError as exc:
        raise HTTPException(
            status_code=409,
            detail="Save conflict — reload your game and try again.",
        ) from exc

    await log_event(
        "verdict_submitted",
        player_id,
        body.case_id,
        {
            "accused": body.accused_suspect_id,
            "correct": correct,
            "score": score,
            "attempts_remaining": verdict_state.attempts_remaining,
        },
    )

    return SubmitVerdictResponse(
        correct=correct,
        attempts_remaining=verdict_state.attempts_remaining,
        case_solved=verdict_state.case_solved,
        mentor_feedback=mentor_feedback,
        confrontation=confrontation_response,
        reveal=reveal,
        wrong_suspect_response=wrong_suspect_response,
        updated_state=state.model_dump(mode="json"),
    )
