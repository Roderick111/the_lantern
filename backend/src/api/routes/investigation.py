"""Investigation endpoints: explore locations, perform rites, discover evidence."""

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.dependencies import UserLLMConfig, get_authenticated_player_id, get_user_llm_config
from src.api.errors import llm_http_exception
from src.api.helpers import (
    check_spell_already_discovered,
    save_conversation_and_return,
    save_slot_state,
    state_delta,
)
from src.api.llm_client import LLMClientError as ClaudeClientError
from src.api.llm_client import get_client
from src.api.rate_limit import LLM_RATE, limiter
from src.api.routes.investigation_logic import (
    build_investigation_prompt,
    build_narrator_hints,
    detect_location_command,
    process_investigation_response,
    resolve_spell_mechanics,
    setup_investigation,
    validate_narrator_control_response,
)
from src.api.schemas import InvestigateRequest, InvestigateResponse
from src.api.sse_format import sse_json_event, sse_text_event
from src.api.stream_runner import reliable_sse_stream, replay_cached_stream, streaming_response
from src.context.spell_llm import detect_spell_with_fuzzy
from src.state.idempotency import IdempotencyGuard
from src.utils.evidence import check_already_discovered, find_not_present_response

logger = logging.getLogger(__name__)
router = APIRouter()
NARRATOR_MAX_TOKENS = 600
NARRATOR_TEMPERATURE = 0.7


@router.post("/investigate/stream")
@limiter.limit(LLM_RATE)
async def investigate_stream(
    request: Request,
    body: InvestigateRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
):
    """Stream narrator response via SSE."""
    guard = IdempotencyGuard(player_id, "investigate_stream", body.request_id)
    early = guard.begin()
    if early is not None:
        if early.get("__stream__"):
            return replay_cached_stream(early)
        return replay_cached_stream(
            {"text": early.get("narrator_response", ""), "done_payload": early}
        )
    t_start = time.monotonic()
    try:
        ctx = await asyncio.to_thread(setup_investigation, body, player_id)
    except Exception:
        guard.fail_before_mutation()
        raise
    logger.debug("TIMING setup: %.0fms", (time.monotonic() - t_start) * 1000)

    t1 = time.monotonic()
    new_loc_id, new_loc_name, has_nav_intent = detect_location_command(
        body.player_input,
        ctx.locations,
        ctx.state.current_location,
    )
    if new_loc_id:
        ctx.state.visit_location(new_loc_id)
        await asyncio.to_thread(save_slot_state, ctx.state, player_id, body.slot)
        narrative = f"You make your way to the {new_loc_name}..."

        async def location_change_generator():
            yield sse_text_event(narrative)
            done_payload = {
                "done": True,
                "new_evidence": [],
                "evidence_names": {},
                "location_changed": new_loc_id,
                "updated_state": state_delta(ctx.state),
                **({"request_id": body.request_id} if body.request_id else {}),
            }
            if body.request_id:
                guard.complete_stream(narrative, done_payload)
            yield sse_json_event(done_payload)

        return streaming_response(location_change_generator())

    spell_id, target = detect_spell_with_fuzzy(body.player_input)
    is_spell = spell_id is not None
    logger.debug("TIMING location+spell detect: %.0fms", (time.monotonic() - t1) * 1000)

    t2 = time.monotonic()
    narrator_hint = build_narrator_hints(body, ctx, has_nav_intent, is_spell, spell_id)
    spell_outcome, witness_context = resolve_spell_mechanics(body, ctx, spell_id, target)

    prompt, system_prompt = build_investigation_prompt(
        body,
        ctx,
        is_spell,
        spell_id,
        target,
        spell_outcome,
        witness_context,
        narrator_hint=narrator_hint,
    )
    logger.debug("TIMING prompt build: %.0fms", (time.monotonic() - t2) * 1000)
    client = get_client()
    llm_trace: list[dict] = []

    async def finalize(full_response: str) -> dict:
        llm_elapsed_ms = int((time.monotonic() - t0) * 1000)

        control_resolution = await validate_narrator_control_response(
            full_response,
            is_spell=is_spell,
            prompt=prompt,
            model=llm_config.model,
            player_id=player_id,
            case_id=body.case_id,
            slot=body.slot,
            assistance_mode=ctx.state.assistance_mode,
            pre_action_discovered_ids=list(ctx.discovered_ids),
        )
        full_response = control_resolution.response

        new_evidence, evidence_names = await process_investigation_response(
            full_response,
            body,
            ctx,
            is_spell,
            spell_id,
            target,
            player_id,
        )

        ctx.state.add_conversation_message(
            "player",
            body.player_input,
            location_id=ctx.target_location_id,
        )
        ctx.state.add_conversation_message(
            "narrator",
            full_response,
            location_id=ctx.target_location_id,
        )
        ctx.state.add_narrator_conversation(
            body.player_input,
            full_response,
            location_id=ctx.target_location_id,
        )
        await asyncio.to_thread(save_slot_state, ctx.state, player_id, body.slot)
        return {
            "done": True,
            "new_evidence": new_evidence,
            "evidence_names": evidence_names,
            "updated_state": state_delta(ctx.state),
            "meta": {
                "model": llm_config.model,
                "latency_ms": llm_elapsed_ms,
                "is_spell": is_spell,
                "spell_id": spell_id,
                "llm_trace": llm_trace,
            },
        }

    t0 = time.monotonic()

    async def persist_completion(text: str, done_payload: dict) -> None:
        guard.complete_stream(text, done_payload)

    async def on_failure(_exc: Exception, _partial: bool) -> None:
        guard.fail_before_mutation()

    return streaming_response(
        reliable_sse_stream(
            client.get_response_stream(
                prompt,
                system=system_prompt,
                api_key=llm_config.api_key,
                model=llm_config.model,
                max_tokens=NARRATOR_MAX_TOKENS,
                temperature=NARRATOR_TEMPERATURE,
                trace=llm_trace,
                disable_reasoning=True,
                endpoint="investigate_stream",
                request_id=body.request_id,
            ),
            request=request,
            endpoint="investigate_stream",
            request_id=body.request_id,
            finalize=finalize,
            persist_completion=persist_completion if body.request_id else None,
            on_failure=on_failure if body.request_id else None,
        )
    )


@router.post("/investigate", response_model=InvestigateResponse)
@limiter.limit(LLM_RATE)
async def investigate(
    request: Request,
    body: InvestigateRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
) -> InvestigateResponse:
    """Process player investigation action (non-streaming, used by tests)."""
    guard = IdempotencyGuard(player_id, "investigate", body.request_id)
    early = guard.begin()
    if early is not None:
        return InvestigateResponse.model_validate(early)

    try:
        result = await _investigate_impl(body, player_id, llm_config)
    except ClaudeClientError as e:
        guard.fail_before_mutation()
        raise llm_http_exception(e) from e
    except HTTPException:
        guard.fail_before_mutation()
        raise

    guard.complete(result)
    return result


async def _investigate_impl(
    body: InvestigateRequest,
    player_id: str,
    llm_config: UserLLMConfig,
) -> InvestigateResponse:
    """Core investigate logic (idempotency-agnostic)."""
    ctx = await asyncio.to_thread(setup_investigation, body, player_id)

    new_loc_id, new_loc_name, has_nav_intent = detect_location_command(
        body.player_input,
        ctx.locations,
        ctx.state.current_location,
    )
    if new_loc_id:
        ctx.state.visit_location(new_loc_id)
        narrative = f"You make your way to the {new_loc_name}..."
        return save_conversation_and_return(
            ctx.state,
            player_id,
            body.player_input,
            narrative,
            new_loc_id,
            [],
            False,
            slot=body.slot,
            location_changed=new_loc_id,
        )

    spell_id, target = detect_spell_with_fuzzy(body.player_input)
    is_spell = spell_id is not None

    if is_spell:
        already_response = check_spell_already_discovered(
            spell_id,
            body.player_input,
            ctx.hidden_evidence,
            ctx.discovered_ids,
        )
        if already_response:
            return save_conversation_and_return(
                ctx.state,
                player_id,
                body.player_input,
                already_response,
                ctx.target_location_id,
                [],
                True,
                slot=body.slot,
            )
    elif check_already_discovered(body.player_input, ctx.hidden_evidence, ctx.discovered_ids):
        return save_conversation_and_return(
            ctx.state,
            player_id,
            body.player_input,
            "You've already examined this thoroughly. Nothing new to find here.",
            ctx.target_location_id,
            [],
            True,
            slot=body.slot,
        )

    not_present_response = find_not_present_response(body.player_input, ctx.not_present)
    if not_present_response:
        return save_conversation_and_return(
            ctx.state,
            player_id,
            body.player_input,
            not_present_response,
            ctx.target_location_id,
            [],
            False,
            slot=body.slot,
        )

    narrator_hint = build_narrator_hints(body, ctx, has_nav_intent, is_spell, spell_id)

    spell_outcome, witness_context = resolve_spell_mechanics(body, ctx, spell_id, target)

    prompt, system_prompt = build_investigation_prompt(
        body,
        ctx,
        is_spell,
        spell_id,
        target,
        spell_outcome,
        witness_context,
        narrator_hint=narrator_hint,
    )

    client = get_client()
    narrator_response = await client.get_response(
        prompt,
        system=system_prompt,
        api_key=llm_config.api_key,
        model=llm_config.model,
        max_tokens=NARRATOR_MAX_TOKENS,
        temperature=NARRATOR_TEMPERATURE,
        disable_reasoning=True,
    )

    control_resolution = await validate_narrator_control_response(
        narrator_response,
        is_spell=is_spell,
        prompt=prompt,
        model=llm_config.model,
        player_id=player_id,
        case_id=body.case_id,
        slot=body.slot,
        assistance_mode=ctx.state.assistance_mode,
        pre_action_discovered_ids=list(ctx.discovered_ids),
    )
    narrator_response = control_resolution.response

    new_evidence, evidence_names = await process_investigation_response(
        narrator_response,
        body,
        ctx,
        is_spell,
        spell_id,
        target,
        player_id,
    )

    return save_conversation_and_return(
        ctx.state,
        player_id,
        body.player_input,
        narrator_response,
        ctx.target_location_id,
        new_evidence,
        False,
        slot=body.slot,
        evidence_names=evidence_names,
    )
