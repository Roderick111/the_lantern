"""Witness interrogation orchestration — setup, prompts, streaming, and post-LLM."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from src.api.dependencies import UserLLMConfig
from src.api.helpers import (
    SSE_HEADERS,
    detect_secrets_in_response,
    load_case_or_404,
    load_localized_case_or_404,
    load_or_create_state,
    load_slot_state,
    save_slot_state,
    state_delta,
)
from src.api.llm_client import get_client
from src.api.schemas import (
    InterrogateRequest,
    InterrogateResponse,
    PresentEvidenceRequest,
)
from src.api.sse_format import sse_json_event, sse_text_event
from src.api.stream_runner import reliable_sse_stream, streaming_response
from src.case_store.loader import build_evidence_index, get_witness
from src.context.spell_llm import (
    SAFE_INVESTIGATION_SPELLS,
    calculate_spell_success,
    detect_spell_with_fuzzy,
)
from src.context.witness import build_witness_prompt, build_witness_system_prompt
from src.state.player_state import PlayerState
from src.telemetry.logger import log_event
from src.utils.trust import (
    TRUST_DELTA_STRIP_RE,
    TRUST_DELTA_TAG_PARTIAL_RE,
    detect_evidence_in_message,
    extract_trust_delta,
    natural_warming,
    strip_trust_tag,
)

logger = logging.getLogger(__name__)


def build_witness_case_context(case_data: dict[str, Any]) -> dict[str, Any]:
    """Extract basic case context for witness prompts."""
    from src.case_store.loader import get_case_section, get_case_setting, get_crime_scene_label

    case_inner = get_case_section(case_data)
    victim_info = case_inner.get("victim", {})

    return {
        "victim_name": victim_info.get("name", ""),
        "crime_type": case_inner.get("crime_type", ""),
        "location": get_crime_scene_label(case_data),
        "setting": get_case_setting(case_data),
    }


def lookup_evidence_full(
    evidence_id: str,
    case_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Look up full evidence data (including strength, points_to) from case data."""
    return build_evidence_index(case_data).get(evidence_id)


def lookup_evidence(
    witness_id: str,
    evidence_id: str,
    case_data: dict[str, Any],
) -> dict[str, Any]:
    """Look up evidence details and witness reaction from case data."""
    ev = lookup_evidence_full(evidence_id, case_data)
    if ev:
        reactions = ev.get("witness_reactions", {})
        return {
            "name": ev.get("name", evidence_id),
            "description": ev.get("description", ""),
            "witness_reaction": reactions.get(witness_id, ""),
        }
    return {"name": evidence_id, "description": "", "witness_reaction": ""}


def calculate_pressure(
    witness_id: str,
    witness_state: Any,
    case_data: dict[str, Any],
) -> tuple[int, list[dict[str, Any]]]:
    """Calculate evidence pressure against a witness from evidence shown."""
    pressure = 0
    details = []

    for ev_id in witness_state.evidence_shown:
        ev = lookup_evidence_full(ev_id, case_data)
        if not ev:
            continue

        strength = ev.get("strength", 0)
        points_to = ev.get("points_to", [])
        implicates_me = witness_id in points_to

        if implicates_me:
            pressure += strength
        else:
            pressure += int(strength * 0.2)

        details.append(
            {
                "name": ev.get("name", ev_id),
                "implicates_me": implicates_me,
            }
        )

    return pressure, details


@dataclass
class WitnessPrep:
    """Pre-LLM preparation result for witness interactions."""

    prompt: str
    system_prompt: str
    stored_question: str
    evidence_id: str | None = None
    mnemonic_delving_redirect: bool = False


def prepare_interrogation(
    body: InterrogateRequest,
    case_data: dict[str, Any],
    witness: dict[str, Any],
    state: PlayerState,
    witness_state: Any,
) -> WitnessPrep:
    """Shared pre-LLM logic for interrogation."""
    witness_id = witness.get("id", body.witness_id)

    evidence_id = detect_evidence_in_message(
        body.question,
        state.discovered_evidence,
        case_data,
    )
    evidence_info: dict[str, Any] | None = None
    stored_question = body.question
    player_input = body.question

    if evidence_id:
        evidence_info = lookup_evidence(witness_id, evidence_id, case_data)
        witness_state.mark_evidence_shown(evidence_id)
        stored_question = f"[Evidence presented: {evidence_info['name']}]"
        player_input = f"I'd like to show you this evidence: {evidence_info['name']}"

    spell_id: str | None = None
    spell_outcome: str | None = None

    if not evidence_id:
        spell_id, _target = detect_spell_with_fuzzy(body.question)

        if spell_id == "mnemonic_delving":
            return WitnessPrep(
                prompt="",
                system_prompt="",
                stored_question="",
                mnemonic_delving_redirect=True,
            )

        if spell_id and spell_id in SAFE_INVESTIGATION_SPELLS:
            spell_key = spell_id.lower()
            attempts = witness_state.spell_attempts.get(spell_key, 0)
            spell_success = calculate_spell_success(
                spell_id=spell_key,
                player_input=body.question,
                attempts_in_location=attempts,
                location_id=f"witness_{body.witness_id}",
            )
            spell_outcome = "SUCCESS" if spell_success else "FAILURE"
            witness_state.spell_attempts[spell_key] = attempts + 1
            logger.info(
                "Spell on Witness: %s | %s | Attempt #%d | %s",
                spell_id,
                body.witness_id,
                attempts + 1,
                spell_outcome,
            )

    pressure, ev_details = calculate_pressure(witness_id, witness_state, case_data)
    case_context = build_witness_case_context(case_data)

    prompt = build_witness_prompt(
        witness=witness,
        trust=witness_state.trust,
        conversation_history=witness_state.get_history_as_dicts(),
        player_input=player_input,
        spell_id=spell_id,
        spell_outcome=spell_outcome,
        case_context=case_context,
        evidence_presented=evidence_info,
        pressure=pressure,
        evidence_shown_details=ev_details,
    )
    system_prompt = build_witness_system_prompt(
        witness.get("name", "Unknown"), language=state.language
    )

    return WitnessPrep(
        prompt=prompt,
        system_prompt=system_prompt,
        stored_question=stored_question,
        evidence_id=evidence_id,
    )


def prepare_evidence_presentation(
    body: PresentEvidenceRequest,
    case_data: dict[str, Any],
    witness: dict[str, Any],
    witness_state: Any,
    state: PlayerState | None = None,
) -> WitnessPrep:
    """Shared pre-LLM logic for explicit evidence presentation."""
    witness_id = witness.get("id", "")
    evidence_info = lookup_evidence(witness_id, body.evidence_id, case_data)
    witness_state.mark_evidence_shown(body.evidence_id)

    pressure, ev_details = calculate_pressure(witness_id, witness_state, case_data)
    case_context = build_witness_case_context(case_data)

    prompt = build_witness_prompt(
        witness=witness,
        trust=witness_state.trust,
        conversation_history=witness_state.get_history_as_dicts(),
        player_input=f"I'd like to show you this evidence: {evidence_info['name']}",
        case_context=case_context,
        evidence_presented=evidence_info,
        pressure=pressure,
        evidence_shown_details=ev_details,
    )
    lang = state.language if state else "en"
    system_prompt = build_witness_system_prompt(witness.get("name", "Unknown"), language=lang)

    return WitnessPrep(
        prompt=prompt,
        system_prompt=system_prompt,
        stored_question=f"[Evidence presented: {evidence_info['name']}]",
        evidence_id=body.evidence_id,
    )


async def finalize_witness_response(
    full_response: str,
    witness: dict[str, Any],
    witness_state: Any,
    state: PlayerState,
    player_id: str,
    case_id: str,
    witness_id: str,
    slot: str,
    prep: WitnessPrep,
    use_natural_warming: bool = True,
) -> tuple[int, str, list[str], dict[str, str]]:
    """Shared post-LLM processing for all witness interactions."""
    trust_delta = extract_trust_delta(full_response)
    if trust_delta is None:
        trust_delta = natural_warming() if use_natural_warming else 0
    witness_state.adjust_trust(trust_delta)

    clean_response = strip_trust_tag(full_response)
    secrets_revealed, secret_texts = detect_secrets_in_response(
        clean_response,
        witness,
        witness_state,
    )

    witness_state.add_conversation(
        question=prep.stored_question,
        response=clean_response,
        trust_delta=trust_delta,
    )
    state.update_witness_state(witness_state)
    await asyncio.to_thread(save_slot_state, state, player_id, slot)

    event_type = "evidence_presented" if prep.evidence_id else "witness_questioned"
    try:
        await log_event(
            event_type,
            player_id,
            case_id,
            {
                "witness_id": witness_id,
                **(
                    {"evidence_id": prep.evidence_id}
                    if prep.evidence_id
                    else {"question": prep.stored_question[:100]}
                ),
            },
        )
    except Exception:
        logger.warning("interaction telemetry failed after state save", exc_info=True)
    if secrets_revealed:
        try:
            await log_event(
                "secret_revealed",
                player_id,
                case_id,
                {"witness_id": witness_id, "secrets": secrets_revealed},
            )
        except Exception:
            logger.warning("secret telemetry failed after state save", exc_info=True)

    return trust_delta, clean_response, secrets_revealed, secret_texts


def load_witness_context(
    body: InterrogateRequest | PresentEvidenceRequest,
    case_data: dict[str, Any],
    player_id: str,
) -> tuple[dict[str, Any], PlayerState, Any]:
    """Load witness, state, witness_state. Raises 404 if witness not found."""
    try:
        witness = get_witness(case_data, body.witness_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Witness not found: {body.witness_id}")

    state = load_or_create_state(body.case_id, player_id, case_data, slot=body.slot)
    base_trust = witness.get("base_trust", 50)
    witness_state = state.get_witness_state(body.witness_id, base_trust)
    return witness, state, witness_state


def setup_interrogate_stream(
    body: InterrogateRequest,
    player_id: str,
) -> tuple[dict[str, Any], dict[str, Any], PlayerState, Any, WitnessPrep]:
    """Sync pre-LLM setup for interrogation stream (run via asyncio.to_thread)."""
    load_case_or_404(body.case_id)
    existing_state = load_slot_state(body.case_id, player_id, body.slot)
    case_data = load_localized_case_or_404(
        body.case_id,
        getattr(existing_state, "language", "en") if existing_state else "en",
    )
    witness, state, witness_state = load_witness_context(body, case_data, player_id)
    prep = prepare_interrogation(body, case_data, witness, state, witness_state)
    return case_data, witness, state, witness_state, prep


def setup_present_evidence_stream(
    body: PresentEvidenceRequest,
    player_id: str,
) -> tuple[dict[str, Any], dict[str, Any], PlayerState, Any, WitnessPrep]:
    """Sync pre-LLM setup for evidence presentation stream (run via asyncio.to_thread)."""
    load_case_or_404(body.case_id)
    existing_state = load_slot_state(body.case_id, player_id, body.slot)
    case_data = load_localized_case_or_404(
        body.case_id,
        getattr(existing_state, "language", "en") if existing_state else "en",
    )
    witness, state, witness_state = load_witness_context(body, case_data, player_id)
    if body.evidence_id not in state.discovered_evidence:
        raise HTTPException(status_code=400, detail=f"Evidence not discovered: {body.evidence_id}")
    prep = prepare_evidence_presentation(body, case_data, witness, witness_state, state=state)
    return case_data, witness, state, witness_state, prep


def stream_witness_llm(
    prep: WitnessPrep,
    witness: dict[str, Any],
    witness_state: Any,
    state: PlayerState,
    player_id: str,
    case_id: str,
    witness_id: str,
    slot: str,
    llm_config: UserLLMConfig,
    endpoint_name: str,
    use_natural_warming: bool = True,
    request: Request | None = None,
    idempotency: Any | None = None,
) -> StreamingResponse:
    """Stream LLM response for any witness interaction."""
    client = get_client()
    llm_trace: list[dict[str, Any]] = []

    display_buffer = ""
    t0 = time.monotonic()

    def render_chunk(chunk: str) -> str | None:
        nonlocal display_buffer
        display_buffer += chunk
        if TRUST_DELTA_TAG_PARTIAL_RE.search(display_buffer):
            return None
        clean = TRUST_DELTA_STRIP_RE.sub("", display_buffer)
        display_buffer = ""
        return clean or None

    def flush_render() -> str | None:
        nonlocal display_buffer
        clean = TRUST_DELTA_STRIP_RE.sub("", display_buffer)
        display_buffer = ""
        return clean or None

    async def finalize(full_response: str) -> dict[str, Any]:
        llm_elapsed_ms = int((time.monotonic() - t0) * 1000)
        trust_delta, _, secrets_revealed, _ = await finalize_witness_response(
            full_response,
            witness,
            witness_state,
            state,
            player_id,
            case_id,
            witness_id,
            slot,
            prep,
            use_natural_warming=use_natural_warming,
        )
        return {
            "done": True,
            "trust": witness_state.trust,
            "trust_delta": trust_delta,
            "secrets_revealed": secrets_revealed,
            "updated_state": state_delta(state),
            "meta": {
                "model": llm_config.model,
                "latency_ms": llm_elapsed_ms,
                "llm_trace": llm_trace,
            },
        }

    async def persist_completion(text: str, done_payload: dict[str, Any]) -> None:
        if idempotency is not None:
            idempotency.complete_stream(text, done_payload)

    async def on_failure(_exc: Exception, _partial: bool) -> None:
        if idempotency is not None:
            idempotency.fail_before_mutation()

    return streaming_response(
        reliable_sse_stream(
            client.get_response_stream(
                prep.prompt,
                system=prep.system_prompt,
                api_key=llm_config.api_key,
                model=llm_config.model,
                trace=llm_trace,
                endpoint=endpoint_name,
                request_id=getattr(idempotency, "request_id", None),
            ),
            request=request,
            endpoint=endpoint_name,
            request_id=getattr(idempotency, "request_id", None),
            finalize=finalize,
            render_chunk=render_chunk,
            flush_render=flush_render,
            persist_completion=persist_completion if idempotency is not None else None,
            on_failure=on_failure if idempotency is not None else None,
        )
    )


def wrap_interrogate_as_sse(
    result: InterrogateResponse,
    model: str | None,
    request_id: str | None = None,
) -> StreamingResponse:
    """Wrap a non-streaming InterrogateResponse as an SSE stream."""

    async def gen():
        yield sse_text_event(result.response)
        yield sse_json_event(
            {
                "done": True,
                "trust": result.trust,
                "trust_delta": result.trust_delta,
                "secrets_revealed": result.secrets_revealed,
                "updated_state": result.updated_state,
                "meta": {"model": model},
                **({"request_id": request_id} if request_id else {}),
            }
        )

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# Backward-compatible aliases for scripts/tests
_build_witness_case_context = build_witness_case_context
_lookup_evidence = lookup_evidence
