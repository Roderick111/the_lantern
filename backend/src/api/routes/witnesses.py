"""Witness interrogation, evidence presentation, and read-only witness endpoints."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.api.dependencies import UserLLMConfig, get_authenticated_player_id, get_user_llm_config
from src.api.errors import llm_http_exception
from src.api.helpers import (
    load_case_or_404,
    load_localized_case_or_404,
    load_slot_state,
    state_delta,
)
from src.api.llm_client import get_client
from src.api.rate_limit import LLM_RATE, limiter
from src.api.routes.mnemonic_delving import handle_programmatic_mnemonic_delving
from src.api.routes.witnesses_logic import (
    finalize_witness_response,
    load_witness_context,
    prepare_evidence_presentation,
    prepare_interrogation,
    setup_interrogate_stream,
    setup_present_evidence_stream,
    stream_witness_llm,
    wrap_interrogate_as_sse,
)
from src.api.schemas import (
    InterrogateRequest,
    InterrogateResponse,
    PresentEvidenceRequest,
    PresentEvidenceResponse,
    WitnessInfo,
)
from src.api.stream_runner import replay_cached_stream
from src.case_store.loader import get_witness, list_witnesses
from src.state.idempotency import IdempotencyGuard

router = APIRouter()


@router.post("/interrogate/stream")
@limiter.limit(LLM_RATE)
async def interrogate_witness_stream(
    request: Request,
    body: InterrogateRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
):
    """Stream witness interrogation response via SSE."""
    guard = IdempotencyGuard(player_id, "interrogate_stream", body.request_id)
    early = guard.begin()
    if early is not None:
        return replay_cached_stream(early)
    try:
        _, witness, state, witness_state, prep = await asyncio.to_thread(
            setup_interrogate_stream,
            body,
            player_id,
        )
    except Exception:
        guard.fail_before_mutation()
        raise
    if prep.mnemonic_delving_redirect:
        try:
            result = await handle_programmatic_mnemonic_delving(
                body=body,
                witness=witness,
                state=state,
                witness_state=witness_state,
                llm_config=llm_config,
                slot=body.slot,
                player_id=player_id,
            )
        except Exception:
            guard.fail_before_mutation()
            raise
        if body.request_id:
            guard.complete_stream(
                result.response,
                {
                    "done": True,
                    "trust": result.trust,
                    "trust_delta": result.trust_delta,
                    "secrets_revealed": result.secrets_revealed,
                    "updated_state": result.updated_state,
                    "meta": {"model": llm_config.model},
                    "request_id": body.request_id,
                },
            )
        return wrap_interrogate_as_sse(result, llm_config.model, body.request_id)

    return stream_witness_llm(
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
        request=request,
        idempotency=guard,
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
    guard = IdempotencyGuard(player_id, "interrogate", body.request_id)
    early = guard.begin()
    if early is not None:
        return InterrogateResponse.model_validate(early)

    try:
        result = await _interrogate_impl(body, player_id, llm_config)
    except HTTPException:
        guard.fail_before_mutation()
        raise

    guard.complete(result)
    return result


async def _interrogate_impl(
    body: InterrogateRequest,
    player_id: str,
    llm_config: UserLLMConfig,
) -> InterrogateResponse:
    load_case_or_404(body.case_id)
    existing_state = load_slot_state(body.case_id, player_id, body.slot)
    case_data = load_localized_case_or_404(
        body.case_id,
        getattr(existing_state, "language", "en") if existing_state else "en",
    )
    witness, state, witness_state = load_witness_context(body, case_data, player_id)

    prep = prepare_interrogation(body, case_data, witness, state, witness_state)
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
    except Exception as e:
        raise llm_http_exception(e) from e

    trust_delta, clean_response, secrets_revealed, secret_texts = await finalize_witness_response(
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
        updated_state=state_delta(state),
    )


@router.post("/present-evidence/stream")
@limiter.limit(LLM_RATE)
async def present_evidence_stream(
    request: Request,
    body: PresentEvidenceRequest,
    player_id: str = Depends(get_authenticated_player_id),
    llm_config: UserLLMConfig = Depends(get_user_llm_config),
):
    """Stream evidence presentation response via SSE."""
    guard = IdempotencyGuard(player_id, "present_evidence_stream", body.request_id)
    early = guard.begin()
    if early is not None:
        return replay_cached_stream(early)
    try:
        _, witness, state, witness_state, prep = await asyncio.to_thread(
            setup_present_evidence_stream,
            body,
            player_id,
        )
    except Exception:
        guard.fail_before_mutation()
        raise

    return stream_witness_llm(
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
        request=request,
        idempotency=guard,
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
    guard = IdempotencyGuard(player_id, "present_evidence", body.request_id)
    early = guard.begin()
    if early is not None:
        return PresentEvidenceResponse.model_validate(early)

    try:
        result = await _present_evidence_impl(body, player_id, llm_config)
    except HTTPException:
        guard.fail_before_mutation()
        raise

    guard.complete(result)
    return result


async def _present_evidence_impl(
    body: PresentEvidenceRequest,
    player_id: str,
    llm_config: UserLLMConfig,
) -> PresentEvidenceResponse:
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

    try:
        client = get_client()
        response = await client.get_response(
            prep.prompt,
            system=prep.system_prompt,
            api_key=llm_config.api_key,
            model=llm_config.model,
        )
    except Exception as e:
        raise llm_http_exception(e) from e

    trust_delta, clean_response, secrets_revealed, secret_texts = await finalize_witness_response(
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
        updated_state=state_delta(state),
    )


@router.get("/witnesses", response_model=list[WitnessInfo])
async def get_witnesses(
    case_id: str = "case_001",
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = "autosave",
    language: str | None = Query(default=None, pattern=r"^[a-zA-Z]{2}$"),
) -> list[WitnessInfo]:
    """List available witnesses with current trust levels."""
    state = load_slot_state(case_id, player_id, slot)
    case_data = load_localized_case_or_404(
        case_id,
        language or (getattr(state, "language", "en") if state else "en"),
    )
    witness_ids = list_witnesses(case_data)
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
    state = load_slot_state(case_id, player_id, slot)
    case_data = load_localized_case_or_404(
        case_id,
        getattr(state, "language", "en") if state else "en",
    )
    try:
        witness = get_witness(case_data, witness_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Witness not found: {witness_id}")

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
