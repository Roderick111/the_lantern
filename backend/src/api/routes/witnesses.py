"""Witness interrogation, evidence presentation, and read-only witness endpoints."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.dependencies import UserLLMConfig, get_authenticated_player_id, get_user_llm_config
from src.api.errors import llm_http_exception
from src.api.helpers import load_case_or_404, load_slot_state, state_delta
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
from src.case_store.loader import get_witness, list_witnesses

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
    _, witness, state, witness_state, prep = await asyncio.to_thread(
        setup_interrogate_stream,
        body,
        player_id,
    )
    if prep.mnemonic_delving_redirect:
        result = await handle_programmatic_mnemonic_delving(
            body=body,
            witness=witness,
            state=state,
            witness_state=witness_state,
            llm_config=llm_config,
            slot=body.slot,
            player_id=player_id,
        )
        return wrap_interrogate_as_sse(result, llm_config.model)

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
    case_data = load_case_or_404(body.case_id)
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
    _, witness, state, witness_state, prep = await asyncio.to_thread(
        setup_present_evidence_stream,
        body,
        player_id,
    )

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
    case_data = load_case_or_404(body.case_id)
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
