"""Evidence listing and detail endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_authenticated_player_id
from src.api.helpers import load_localized_case_or_404, load_slot_state
from src.api.schemas import EvidenceDetailItem, EvidenceDetailResponse, EvidenceResponse
from src.case_store.loader import get_all_evidence, get_evidence_by_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/evidence", response_model=EvidenceResponse)
async def get_evidence(
    case_id: str = "case_001",
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = "autosave",
) -> EvidenceResponse:
    """Get list of discovered evidence."""
    state = await asyncio.to_thread(load_slot_state, case_id, player_id, slot)
    if state is None:
        return EvidenceResponse(case_id=case_id, discovered_evidence=[])

    return EvidenceResponse(
        case_id=state.case_id,
        discovered_evidence=state.discovered_evidence,
    )


@router.get("/evidence/details", response_model=EvidenceDetailResponse)
async def get_evidence_details(
    case_id: str = "case_001",
    location_id: str | None = None,
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = "autosave",
) -> EvidenceDetailResponse:
    """Get detailed evidence info for discovered evidence."""
    state = await asyncio.to_thread(load_slot_state, case_id, player_id, slot)
    case_data = load_localized_case_or_404(
        case_id,
        getattr(state, "language", "en") if state else "en",
    )
    discovered_ids = state.discovered_evidence if state else []

    all_evidence = get_all_evidence(case_data, location_id)
    discovered_evidence = [
        EvidenceDetailItem(
            id=evidence["id"],
            name=evidence["name"],
            location_found=evidence["location_found"],
            description=evidence["description"],
            type=evidence["type"],
        )
        for evidence in all_evidence
        if evidence["id"] in discovered_ids
    ]

    return EvidenceDetailResponse(case_id=case_id, evidence=discovered_evidence)


@router.get("/evidence/{evidence_id}")
async def get_single_evidence(
    evidence_id: str,
    case_id: str = "case_001",
    location_id: str | None = None,
    player_id: str = Depends(get_authenticated_player_id),
    slot: str = "autosave",
) -> EvidenceDetailItem:
    """Get single evidence item with full metadata."""
    state = await asyncio.to_thread(load_slot_state, case_id, player_id, slot)
    case_data = load_localized_case_or_404(
        case_id,
        getattr(state, "language", "en") if state else "en",
    )
    discovered_ids = state.discovered_evidence if state else []

    if evidence_id not in discovered_ids:
        raise HTTPException(status_code=404, detail=f"Evidence not discovered: {evidence_id}")

    evidence = get_evidence_by_id(case_data, location_id, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")

    return EvidenceDetailItem(
        id=evidence["id"],
        name=evidence["name"],
        location_found=evidence["location_found"],
        description=evidence["description"],
        type=evidence["type"],
    )
