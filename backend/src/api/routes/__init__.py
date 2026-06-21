"""API route modules.

All sub-routers are collected into a single `router` for main.py.
"""

from fastapi import APIRouter

from .briefing import router as briefing_router
from .cases import router as cases_router
from .evidence import router as evidence_router
from .investigation import router as investigation_router
from .llm_config import router as llm_config_router
from .matthew import router as matthew_router
from .saves import router as saves_router
from .session import router as session_router
from .telemetry import router as telemetry_router
from .verdict import router as verdict_router
from .witnesses import router as witnesses_router

router = APIRouter(prefix="/api", tags=["game"])

router.include_router(session_router)
router.include_router(investigation_router)
router.include_router(witnesses_router)
router.include_router(verdict_router)
router.include_router(briefing_router)
router.include_router(matthew_router)
router.include_router(saves_router)
router.include_router(cases_router)
router.include_router(evidence_router)
router.include_router(llm_config_router)
router.include_router(telemetry_router)

# Re-export for backward compatibility with tests
from src.api.schemas import (  # noqa: E402, F401
    InvestigateRequest,
    InvestigateResponse,
    SubmitVerdictRequest,
    SubmitVerdictResponse,
)

# Re-export helper functions for backward compatibility with tests
from src.context.narrator import (  # noqa: E402, F401
    build_narrator_or_spell_prompt,
    build_narrator_prompt,
)

from .investigation import investigate  # noqa: E402, F401
from .verdict import submit_verdict  # noqa: E402, F401
