"""Investigation endpoints: explore locations, perform rites, discover evidence."""

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from src.api.dependencies import UserLLMConfig, get_authenticated_player_id, get_user_llm_config
from src.api.errors import llm_http_exception, llm_stream_error_payload, redact_secrets
from src.api.helpers import (
    SSE_HEADERS,
    check_spell_already_discovered,
    save_conversation_and_return,
    save_slot_state,
    state_delta,
    stream_with_keepalive,
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
)
from src.api.schemas import InvestigateRequest, InvestigateResponse
from src.api.sse_format import sse_json_event, sse_text_event
from src.context.spell_llm import detect_spell_with_fuzzy
from src.telemetry.logger import log_event
from src.utils.evidence import check_already_discovered, find_not_present_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/investigate/stream")
@limiter.limit(LLM_RATE)
async def investigate_stream(
    request: Request,
    body: InvestigateRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
):
    """Stream narrator response via SSE."""
    t_start = time.monotonic()
    ctx = await asyncio.to_thread(setup_investigation, body, player_id)
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
            yield sse_json_event(
                {
                    "done": True,
                    "new_evidence": [],
                    "evidence_names": {},
                    "location_changed": new_loc_id,
                    "updated_state": state_delta(ctx.state),
                }
            )

        return StreamingResponse(
            location_change_generator(),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

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

    async def event_generator():
        full_response = ""
        t0 = time.monotonic()
        try:
            llm_stream = client.get_response_stream(
                prompt,
                system=system_prompt,
                api_key=llm_config.api_key,
                model=llm_config.model,
            )
            async for chunk in stream_with_keepalive(llm_stream):
                if chunk.startswith(":"):
                    yield chunk
                    continue
                full_response += chunk
                yield sse_text_event(chunk)
        except Exception as e:
            await log_event(
                "llm_error",
                player_id,
                body.case_id,
                {
                    "endpoint": "investigate_stream",
                    "error": redact_secrets(str(e)),
                    "model": llm_config.model,
                },
            )
            logger.error("LLM stream error in investigate: %s", e)
            yield sse_json_event(llm_stream_error_payload(e))
            return

        try:
            llm_elapsed_ms = int((time.monotonic() - t0) * 1000)

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
        except Exception:
            logger.error("Post-LLM processing failed in investigate", exc_info=True)
            yield sse_json_event(
                {"error": "Progress may not be saved. Try again.", "code": "persist_failed"}
            )
            return

        yield sse_json_event(
            {
                "done": True,
                "new_evidence": new_evidence,
                "evidence_names": evidence_names,
                "updated_state": state_delta(ctx.state),
                "meta": {
                    "model": llm_config.model,
                    "latency_ms": llm_elapsed_ms,
                    "is_spell": is_spell,
                    "spell_id": spell_id,
                },
            }
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
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

    narrator_hint: str | None = None
    if has_nav_intent and not is_spell:
        narrator_hint = (
            "The player seems to be trying to leave this location or go somewhere. "
            "Do NOT narrate travel or describe arriving at a different place. "
            "Briefly acknowledge their intent in character — perhaps the path is "
            "unclear, or suggest they decide where to go. Stay in the current location. "
            "Keep it to 1-2 sentences."
        )

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

    try:
        client = get_client()
        narrator_response = await client.get_response(
            prompt,
            system=system_prompt,
            api_key=llm_config.api_key,
            model=llm_config.model,
        )
    except ClaudeClientError as e:
        raise llm_http_exception(e) from e

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
