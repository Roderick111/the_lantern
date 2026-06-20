"""Witness interrogation, evidence presentation, and Mnemonic Delving endpoints."""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.api.dependencies import UserLLMConfig, get_authenticated_player_id, get_user_llm_config
from src.api.helpers import (
    SSE_HEADERS,
    detect_secrets_in_response,
    load_case_or_404,
    load_or_create_state,
    load_slot_state,
    save_slot_state,
    stream_with_keepalive,
)
from src.api.llm_client import LLMClientError as ClaudeClientError
from src.api.llm_client import get_client
from src.api.rate_limit import LLM_RATE, limiter
from src.api.routes.mnemonic_delving import handle_programmatic_mnemonic_delving
from src.api.schemas import (
    InterrogateRequest,
    InterrogateResponse,
    PresentEvidenceRequest,
    PresentEvidenceResponse,
    WitnessInfo,
)
from src.case_store.loader import get_witness, list_witnesses
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
router = APIRouter()


# ── Shared helpers ────────────────────────────────────────────────────────────


def _build_witness_case_context(case_data: dict[str, Any]) -> dict[str, Any]:
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


def _build_evidence_index(case_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build evidence ID → evidence dict index from case data."""
    case_inner = case_data.get("case", case_data)
    index: dict[str, dict[str, Any]] = {}
    for location in case_inner.get("locations", {}).values():
        for ev in location.get("hidden_evidence", []):
            eid = ev.get("id")
            if eid:
                index[eid] = ev
    for ev in case_inner.get("additional_evidence", []):
        eid = ev.get("id")
        if eid:
            index[eid] = ev
    return index


def _lookup_evidence_full(
    evidence_id: str,
    case_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Look up full evidence data (including strength, points_to) from case data."""
    return _build_evidence_index(case_data).get(evidence_id)


def _lookup_evidence(
    witness_id: str,
    evidence_id: str,
    case_data: dict[str, Any],
) -> dict[str, Any]:
    """Look up evidence details and witness reaction from case data."""
    ev = _lookup_evidence_full(evidence_id, case_data)
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
    """Calculate evidence pressure against a witness from evidence shown.

    Evidence that directly implicates the witness (via points_to) contributes
    full strength. Other evidence contributes 20% (atmosphere/indirect).
    """
    pressure = 0
    details = []

    for ev_id in witness_state.evidence_shown:
        ev = _lookup_evidence_full(ev_id, case_data)
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


# ── Shared pre/post-LLM logic ────────────────────────────────────────────────


@dataclass
class WitnessPrep:
    """Pre-LLM preparation result for witness interactions."""

    prompt: str
    system_prompt: str
    stored_question: str
    evidence_id: str | None = None
    mnemonic_delving_redirect: bool = False


def _prepare_interrogation(
    body: InterrogateRequest,
    case_data: dict[str, Any],
    witness: dict[str, Any],
    state: PlayerState,
    witness_state: Any,
) -> WitnessPrep:
    """Shared pre-LLM logic for interrogation.

    Handles: evidence detection in player text, spell detection,
    pressure calculation, prompt building.
    """
    witness_id = witness.get("id", body.witness_id)

    # Detect evidence reference in player's question
    evidence_id = detect_evidence_in_message(
        body.question,
        state.discovered_evidence,
        case_data,
    )
    evidence_info: dict[str, Any] | None = None
    stored_question = body.question
    player_input = body.question

    if evidence_id:
        evidence_info = _lookup_evidence(witness_id, evidence_id, case_data)
        witness_state.mark_evidence_shown(evidence_id)
        stored_question = f"[Evidence presented: {evidence_info['name']}]"
        player_input = f"I'd like to show you this evidence: {evidence_info['name']}"

    # Spell detection (only when no evidence presented)
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
    case_context = _build_witness_case_context(case_data)

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


def _prepare_evidence_presentation(
    body: PresentEvidenceRequest,
    case_data: dict[str, Any],
    witness: dict[str, Any],
    witness_state: Any,
    state: PlayerState | None = None,
) -> WitnessPrep:
    """Shared pre-LLM logic for explicit evidence presentation."""
    witness_id = witness.get("id", "")
    evidence_info = _lookup_evidence(witness_id, body.evidence_id, case_data)
    witness_state.mark_evidence_shown(body.evidence_id)

    pressure, ev_details = calculate_pressure(witness_id, witness_state, case_data)
    case_context = _build_witness_case_context(case_data)

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


async def _finalize_witness_response(
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
) -> tuple[int, str, list[str], list[str]]:
    """Shared post-LLM processing for all witness interactions.

    Returns: (trust_delta, clean_response, secrets_revealed, secret_texts)
    """
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
    if secrets_revealed:
        await log_event(
            "secret_revealed",
            player_id,
            case_id,
            {"witness_id": witness_id, "secrets": secrets_revealed},
        )

    return trust_delta, clean_response, secrets_revealed, secret_texts


def _load_witness_context(
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


def _stream_witness_llm(
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
) -> StreamingResponse:
    """Stream LLM response for any witness interaction."""
    client = get_client()

    async def event_generator():
        full_response = ""
        display_buffer = ""  # Buffer to catch trust tags before they're sent
        t0 = time.monotonic()
        try:
            llm_stream = client.get_response_stream(
                prep.prompt,
                system=prep.system_prompt,
                api_key=llm_config.api_key,
                model=llm_config.model,
            )
            async for chunk in stream_with_keepalive(llm_stream):
                if chunk.startswith(":"):
                    yield chunk  # keepalive comment
                    continue
                full_response += chunk
                display_buffer += chunk

                # Check if buffer contains a partial trust tag forming
                if TRUST_DELTA_TAG_PARTIAL_RE.search(display_buffer):
                    continue  # Hold back — tag may still be forming

                # Strip any complete trust tags from buffer
                clean = TRUST_DELTA_STRIP_RE.sub("", display_buffer)
                display_buffer = ""
                if clean:
                    yield f"data: {json.dumps({'text': clean})}\n\n"

            # Flush remaining buffer (strip any trust tag remnants)
            if display_buffer:
                clean = TRUST_DELTA_STRIP_RE.sub("", display_buffer)
                if clean:
                    yield f"data: {json.dumps({'text': clean})}\n\n"
        except Exception as e:
            await log_event(
                "llm_error",
                player_id,
                case_id,
                {"endpoint": endpoint_name, "error": str(e)[:200], "model": llm_config.model},
            )
            logger.error("LLM stream error in %s: %s", endpoint_name, e)
            yield f"data: {json.dumps({'error': 'An error occurred while processing your request.'})}\n\n"
            return

        try:
            llm_elapsed_ms = int((time.monotonic() - t0) * 1000)

            trust_delta, _, secrets_revealed, _ = await _finalize_witness_response(
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
        except Exception as e:
            logger.error("Post-LLM processing failed in %s", endpoint_name, exc_info=True)
            yield f"data: {json.dumps({'error': 'persist_failed', 'message': str(e)[:200]})}\n\n"
            return

        yield f"data: {json.dumps({'done': True, 'trust': witness_state.trust, 'trust_delta': trust_delta, 'secrets_revealed': secrets_revealed, 'updated_state': state.model_dump(mode='json'), 'meta': {'model': llm_config.model, 'latency_ms': llm_elapsed_ms}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# ── Interrogation endpoints ──────────────────────────────────────────────────


@router.post("/interrogate/stream")
@limiter.limit(LLM_RATE)
async def interrogate_witness_stream(
    request: Request,
    body: InterrogateRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
):
    """Stream witness interrogation response via SSE."""
    # player_id from dep, removed from body
    case_data = load_case_or_404(body.case_id)
    witness, state, witness_state = _load_witness_context(body, case_data, player_id)

    prep = _prepare_interrogation(body, case_data, witness, state, witness_state)
    if prep.mnemonic_delving_redirect:
        # Mnemonic Delving has its own non-streaming handler; wrap as single SSE event
        result = await handle_programmatic_mnemonic_delving(
            body=body,
            witness=witness,
            state=state,
            witness_state=witness_state,
            llm_config=llm_config,
            slot=body.slot,
            player_id=player_id,
        )
        return _wrap_interrogate_as_sse(result, llm_config.model)

    return _stream_witness_llm(
        prep,
        witness,
        witness_state,
        state,
        player_id,
        body.case_id,
        body.witness_id,
        body.slot,
        llm_config,
        "interrogate_stream",
    )


@router.post("/interrogate", response_model=InterrogateResponse)
@limiter.limit(LLM_RATE)
async def interrogate_witness(
    request: Request,
    body: InterrogateRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
) -> InterrogateResponse:
    """Interrogate a witness (non-streaming, used by tests)."""
    # player_id from dep, removed from body
    case_data = load_case_or_404(body.case_id)
    witness, state, witness_state = _load_witness_context(body, case_data, player_id)

    prep = _prepare_interrogation(body, case_data, witness, state, witness_state)
    if prep.mnemonic_delving_redirect:
        return await handle_programmatic_mnemonic_delving(
            body=body,
            witness=witness,
            state=state,
            witness_state=witness_state,
            llm_config=llm_config,
            slot=body.slot,
            player_id=player_id,
        )

    try:
        client = get_client()
        response = await client.get_response(
            prep.prompt,
            system=prep.system_prompt,
            api_key=llm_config.api_key,
            model=llm_config.model,
        )
    except ClaudeClientError:
        raise HTTPException(status_code=503, detail="LLM service temporarily unavailable")

    trust_delta, clean_response, secrets_revealed, secret_texts = await _finalize_witness_response(
        response,
        witness,
        witness_state,
        state,
        player_id,
        body.case_id,
        body.witness_id,
        body.slot,
        prep,
    )

    return InterrogateResponse(
        response=clean_response,
        trust=witness_state.trust,
        trust_delta=trust_delta,
        secrets_revealed=secrets_revealed,
        secret_texts=secret_texts,
        updated_state=state.model_dump(mode="json"),
    )


# ── Evidence presentation endpoints ──────────────────────────────────────────


@router.post("/present-evidence/stream")
@limiter.limit(LLM_RATE)
async def present_evidence_stream(
    request: Request,
    body: PresentEvidenceRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
):
    """Stream evidence presentation response via SSE."""
    # player_id from dep, removed from body
    case_data = load_case_or_404(body.case_id)
    witness, state, witness_state = _load_witness_context(body, case_data, player_id)

    if body.evidence_id not in state.discovered_evidence:
        raise HTTPException(status_code=400, detail=f"Evidence not discovered: {body.evidence_id}")

    prep = _prepare_evidence_presentation(body, case_data, witness, witness_state, state=state)

    return _stream_witness_llm(
        prep,
        witness,
        witness_state,
        state,
        player_id,
        body.case_id,
        body.witness_id,
        body.slot,
        llm_config,
        "present_evidence_stream",
        use_natural_warming=False,
    )


@router.post("/present-evidence", response_model=PresentEvidenceResponse)
@limiter.limit(LLM_RATE)
async def present_evidence(
    request: Request,
    body: PresentEvidenceRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
) -> PresentEvidenceResponse:
    """Present evidence to a witness (non-streaming, used by tests)."""
    # player_id from dep, removed from body
    case_data = load_case_or_404(body.case_id)
    witness, state, witness_state = _load_witness_context(body, case_data, player_id)

    if body.evidence_id not in state.discovered_evidence:
        raise HTTPException(status_code=400, detail=f"Evidence not discovered: {body.evidence_id}")

    prep = _prepare_evidence_presentation(body, case_data, witness, witness_state, state=state)

    try:
        client = get_client()
        response = await client.get_response(
            prep.prompt,
            system=prep.system_prompt,
            api_key=llm_config.api_key,
            model=llm_config.model,
        )
    except ClaudeClientError:
        raise HTTPException(status_code=503, detail="LLM service temporarily unavailable")

    trust_delta, clean_response, secrets_revealed, secret_texts = await _finalize_witness_response(
        response,
        witness,
        witness_state,
        state,
        player_id,
        body.case_id,
        body.witness_id,
        body.slot,
        prep,
        use_natural_warming=False,
    )

    return PresentEvidenceResponse(
        response=clean_response,
        trust=witness_state.trust,
        trust_delta=trust_delta,
        secrets_revealed=secrets_revealed,
        secret_texts=secret_texts,
        updated_state=state.model_dump(mode="json"),
    )


# ── Utility ──────────────────────────────────────────────────────────────────


def _wrap_interrogate_as_sse(
    result: InterrogateResponse,
    model: str | None,
) -> StreamingResponse:
    """Wrap a non-streaming InterrogateResponse as an SSE stream."""

    async def gen():
        yield f"data: {json.dumps({'text': result.response})}\n\n"
        yield f"data: {json.dumps({'done': True, 'trust': result.trust, 'trust_delta': result.trust_delta, 'secrets_revealed': result.secrets_revealed, 'updated_state': result.updated_state, 'meta': {'model': model}})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# ── Read-only endpoints ──────────────────────────────────────────────────────


@router.get("/witnesses", response_model=list[WitnessInfo])
async def get_witnesses(
    case_id: str = "case_001",
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = "autosave",
) -> list[WitnessInfo]:
    """List available witnesses with current trust levels."""
    case_data = load_case_or_404(case_id)
    witness_ids = list_witnesses(case_data)
    state = load_slot_state(case_id, player_id, slot)

    witnesses: list[WitnessInfo] = []
    for witness_id in witness_ids:
        witness = get_witness(case_data, witness_id)

        if state and witness_id in state.witness_states:
            ws = state.witness_states[witness_id]
            trust = ws.trust
            secrets_revealed = ws.secrets_revealed
        else:
            trust = witness.get("base_trust", 50)
            secrets_revealed = []

        witnesses.append(
            WitnessInfo(
                id=witness_id,
                name=witness.get("name", "Unknown"),
                trust=trust,
                secrets_revealed=secrets_revealed,
            )
        )

    return witnesses


@router.get("/witness/{witness_id}", response_model=WitnessInfo)
async def get_witness_info(
    witness_id: str,
    case_id: str = "case_001",
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = "autosave",
) -> WitnessInfo:
    """Get single witness info with current trust level."""
    case_data = load_case_or_404(case_id)
    try:
        witness = get_witness(case_data, witness_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Witness not found: {witness_id}")

    state = load_slot_state(case_id, player_id, slot)

    if state and witness_id in state.witness_states:
        ws = state.witness_states[witness_id]
        trust = ws.trust
        secrets_revealed = ws.secrets_revealed
        conversation_history = [item.model_dump() for item in ws.conversation_history]
    else:
        trust = witness.get("base_trust", 50)
        secrets_revealed = []
        conversation_history = []

    return WitnessInfo(
        id=witness_id,
        name=witness.get("name", "Unknown"),
        trust=trust,
        secrets_revealed=secrets_revealed,
        conversation_history=conversation_history,
        personality=witness.get("description") or witness.get("personality"),
    )
