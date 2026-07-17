"""Case listing and location info endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.api.helpers import load_localized_case_or_404
from src.api.schemas import CaseListResponse
from src.case_store.loader import get_location

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/cases", response_model=CaseListResponse)
async def list_cases_endpoint(
    language: str = Query(default="en", pattern=r"^[a-zA-Z]{2}$"),
) -> CaseListResponse:
    """List all available cases with metadata."""
    from src.case_store.loader import list_cases_with_metadata

    try:
        cases, errors = list_cases_with_metadata(language)
        return CaseListResponse(
            cases=[case.model_dump() for case in cases],
            count=len(cases),
            errors=errors if errors else None,
        )
    except Exception as e:
        logger.error(f"Case discovery failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load cases")


@router.get("/case/{case_id}/location/{location_id}")
async def get_location_info(
    case_id: str,
    location_id: str,
    language: str = Query(default="en", pattern=r"^[a-zA-Z]{2}$"),
) -> dict[str, Any]:
    """Get location information (for initial load)."""
    try:
        case_data = load_localized_case_or_404(case_id, language)
        location = get_location(case_data, location_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Location not found: {location_id}")

    return {
        "id": location.get("id", location_id),
        "name": location.get("name", "Unknown Location"),
        "description": location.get("description", ""),
        "surface_elements": location.get("surface_elements", []),
        "witnesses_present": location.get("witnesses_present", []),
    }
