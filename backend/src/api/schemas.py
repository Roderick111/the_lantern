"""Pydantic request/response models for all API endpoints."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

SaveSlotName = Literal["autosave", "slot_1", "slot_2", "slot_3"]

# Opaque ASCII request id for durable clients (Telegram gateway). Optional.
RequestId = Annotated[
    str | None,
    Field(
        max_length=128,
        pattern=r"^[\x21-\x7E]{1,128}$",
        description="Opaque ASCII idempotency key (max 128). Omit for legacy clients.",
    ),
]

# ============================================
# Investigation models
# ============================================


class InvestigateRequest(BaseModel):
    """Request for investigate endpoint."""

    player_input: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Player's action/input (max 1000 chars, ~250 tokens)",
    )
    case_id: str = Field(
        default="case_001",
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Case identifier",
    )
    location_id: str | None = Field(
        default=None,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Current location (optional, defaults to saved state or first location)",
    )
    slot: SaveSlotName = Field(
        default="autosave",
        description="Save slot to load/save state from",
    )
    request_id: RequestId = None


class StateDeltaResponse(BaseModel):
    """Lightweight player-state slice returned in SSE done payloads."""

    case_id: str
    current_location: str
    discovered_evidence: list[str] = Field(default_factory=list)
    visited_locations: list[str] = Field(default_factory=list)
    save_revision: int = 0


class InvestigateResponse(BaseModel):
    """Response from investigate endpoint."""

    narrator_response: str = Field(..., description="LLM narrator response")
    new_evidence: list[str] = Field(
        default_factory=list, description="Newly discovered evidence IDs"
    )
    evidence_names: dict[str, str] = Field(
        default_factory=dict, description="Evidence ID → display name map"
    )
    already_discovered: bool = Field(default=False, description="Was this already found?")
    location_changed: str | None = Field(
        default=None, description="New location ID if player moved via natural language"
    )
    updated_state: StateDeltaResponse | None = None


# ============================================
# Save/Load models
# ============================================


class SaveRequest(BaseModel):
    """Request for save endpoint."""

    state: dict[str, Any] = Field(..., description="Player state to save")
    slot: SaveSlotName = Field(
        default="autosave",
        description="Save slot to save state to",
    )


class SaveResponse(BaseModel):
    """Response from save endpoint."""

    success: bool
    message: str
    slot: str | None = None


class UpdateSettingsRequest(BaseModel):
    """Request to update player settings."""

    case_id: str = Field(
        default="case_001",
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Case identifier",
    )
    narrator_verbosity: str | None = Field(
        default=None,
        description="Narrator style: concise | storyteller | atmospheric",
    )
    language: str | None = Field(
        default=None,
        description="Game language: en | ru | fr | es | de | pt | zh | ja | ko",
    )
    slot: str = Field(
        default="autosave",
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Save slot to load/save state from",
    )
    request_id: RequestId = None


class UpdateSettingsResponse(BaseModel):
    """Response from update settings endpoint."""

    success: bool
    message: str


class StateResponse(BaseModel):
    """Response containing player state."""

    case_id: str
    current_location: str
    discovered_evidence: list[str]
    visited_locations: list[str]
    conversation_history: list[dict[str, Any]] = []
    narrator_verbosity: str | None = None
    language: str | None = None


class ResetResponse(BaseModel):
    """Response for case reset endpoint."""

    success: bool
    message: str


class SaveSlotMetadata(BaseModel):
    """Metadata for a single save slot."""

    slot: str = Field(..., description="Slot identifier (slot_1, slot_2, slot_3, autosave)")
    case_id: str = Field(..., description="Case identifier (e.g., case_001)")
    timestamp: str | None = Field(None, description="Last save timestamp (ISO format)")
    location: str = Field(default="unknown", description="Current location in save")
    evidence_count: int = Field(default=0, description="Number of discovered evidence")
    witnesses_interrogated: int = Field(default=0, description="Number of witnesses interrogated")
    progress_percent: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    version: str = Field(default="1.0.0", description="Save file version")


class SaveSlotsListResponse(BaseModel):
    """Response listing all save slots."""

    case_id: str
    saves: list[SaveSlotMetadata] = Field(default_factory=list)


class SaveSlotResponse(BaseModel):
    """Response from save/delete slot operations."""

    success: bool
    slot: str
    message: str | None = None


# ============================================
# Evidence models
# ============================================


class EvidenceDetailItem(BaseModel):
    """Evidence item with full metadata."""

    id: str
    name: str
    location_found: str
    description: str
    type: str


class EvidenceResponse(BaseModel):
    """Response from evidence endpoint."""

    case_id: str
    discovered_evidence: list[str]


class EvidenceDetailResponse(BaseModel):
    """Response with full evidence details."""

    case_id: str
    evidence: list[EvidenceDetailItem]


# ============================================
# Witness/Interrogation models
# ============================================


class InterrogateRequest(BaseModel):
    """Request for interrogate endpoint."""

    witness_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Witness identifier",
    )
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Player's question (max 1000 chars, ~250 tokens)",
    )
    case_id: str = Field(
        default="case_001",
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Case identifier",
    )
    slot: str = Field(
        default="autosave",
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Save slot to load/save state from",
    )
    request_id: RequestId = None


class InterrogateResponse(BaseModel):
    """Response from interrogate endpoint."""

    response: str = Field(..., description="Witness response")
    trust: int = Field(..., description="Current trust level (0-100)")
    trust_delta: int = Field(default=0, description="Change in trust from this question")
    secrets_revealed: list[str] = Field(
        default_factory=list, description="Secrets revealed in this response"
    )
    secret_texts: dict[str, str] = Field(
        default_factory=dict, description="Secret ID to full text description mapping"
    )
    updated_state: StateDeltaResponse | None = None


class PresentEvidenceRequest(BaseModel):
    """Request for present-evidence endpoint."""

    witness_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Witness identifier",
    )
    evidence_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Evidence to present",
    )
    case_id: str = Field(
        default="case_001",
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Case identifier",
    )
    slot: str = Field(
        default="autosave",
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Save slot to load/save state from",
    )
    request_id: RequestId = None


class PresentEvidenceResponse(BaseModel):
    """Response from present-evidence endpoint."""

    response: str = Field(..., description="Witness response")
    trust: int = Field(..., description="Current trust level (0-100)")
    trust_delta: int = Field(default=0, description="Change in trust from this action")
    secrets_revealed: list[str] = Field(
        default_factory=list, description="Secrets revealed in this response"
    )
    secret_texts: dict[str, str] = Field(
        default_factory=dict, description="Secret ID to full text description mapping"
    )
    updated_state: StateDeltaResponse | None = None


class WitnessInfo(BaseModel):
    """Public witness information."""

    id: str
    name: str
    trust: int = Field(default=50, description="Current trust level")
    secrets_revealed: list[str] = Field(default_factory=list)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    personality: str | None = None


# ============================================
# Verdict models
# ============================================


class SubmitVerdictRequest(BaseModel):
    """Request for submit-verdict endpoint."""

    case_id: str = Field(
        default="case_001",
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Case identifier",
    )
    slot: str = Field(
        default="autosave",
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Save slot to load/save state from",
    )
    accused_suspect_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Suspect ID being accused",
    )
    reasoning: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Player's reasoning for accusation (max 2000 chars, ~500 tokens)",
    )
    evidence_cited: list[str] = Field(default_factory=list, description="Evidence IDs player cites")
    request_id: RequestId = None


class FallacyDetail(BaseModel):
    """Detailed fallacy information."""

    name: str
    description: str
    example: str = ""


class MentorFeedback(BaseModel):
    """Mentor feedback for verdict."""

    analysis: str
    fallacies_detected: list[FallacyDetail]
    score: int
    quality: str
    critique: str
    praise: str
    hint: str | None = None


class ConfrontationDialogue(BaseModel):
    """Confrontation dialogue after verdict."""

    dialogue: list[dict[str, str]]
    aftermath: str


class SubmitVerdictResponse(BaseModel):
    """Response from submit-verdict endpoint."""

    correct: bool
    attempts_remaining: int
    case_solved: bool
    mentor_feedback: MentorFeedback
    confrontation: ConfrontationDialogue | None = None
    reveal: str | None = None
    wrong_suspect_response: str | None = None
    updated_state: dict[str, Any] | None = None


# ============================================
# Briefing models
# ============================================


class TeachingChoice(BaseModel):
    """Single choice for teaching question."""

    id: str
    text: str
    response: str


class TeachingQuestion(BaseModel):
    """Teaching question with multiple choice answers."""

    prompt: str
    choices: list[TeachingChoice]
    concept_summary: str


class CaseDossier(BaseModel):
    """Structured case details for the briefing dossier."""

    title: str = "CLASSIFIED"
    victim: str
    location: str
    time: str
    status: str
    synopsis: str


class BriefingContent(BaseModel):
    """Briefing content from YAML."""

    case_id: str
    dossier: CaseDossier
    teaching_questions: list[TeachingQuestion]
    rationality_concept: str
    concept_description: str
    transition: str = ""
    briefing_completed: bool = False


class BriefingQuestionRequest(BaseModel):
    """Request for briefing question endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Player's question for Graves (max 1000 chars, ~250 tokens)",
    )
    slot: str = Field(
        default="autosave",
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Save slot to load/save state from",
    )


class BriefingQuestionResponse(BaseModel):
    """Response from briefing question endpoint."""

    answer: str = Field(..., description="Graves's response")
    updated_state: dict[str, Any] | None = None


class BriefingCompleteRequest(BaseModel):
    """Optional body for briefing complete. Query-only calls remain valid."""

    slot: str = Field(
        default="autosave",
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Save slot to load/save state from",
    )
    request_id: RequestId = None


class BriefingCompleteResponse(BaseModel):
    """Response from briefing complete endpoint."""

    success: bool
    updated_state: dict[str, Any] | None = None


# ============================================
# Spirit companion (Matthew) models
# ============================================


class InnerVoiceCheckRequest(BaseModel):
    """Request for inner voice check endpoint."""

    evidence_count: int = Field(..., ge=0, description="Current evidence count")


class InnerVoiceTriggerResponse(BaseModel):
    """Response from inner voice check endpoint (LEGACY YAML system)."""

    id: str = Field(..., description="Trigger ID")
    text: str = Field(..., description="Matthew's message text")
    type: str = Field(..., description="Trigger type (helpful/misleading/etc.)")
    tier: int = Field(..., ge=1, le=3, description="Trigger tier (1/2/3)")
    updated_state: dict[str, Any] | None = None


class MatthewAutoCommentRequest(BaseModel):
    """Request for Matthew auto-comment after evidence discovery."""

    is_critical: bool = Field(default=False, description="Force Matthew to comment?")
    last_evidence_id: str | None = Field(
        default=None,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Evidence just discovered",
    )


class MatthewChatRequest(BaseModel):
    """Request for direct Matthew conversation."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Player's question to Matthew (max 1000 chars, ~250 tokens)",
    )


class MatthewResponseModel(BaseModel):
    """Matthew's response (LLM-powered)."""

    text: str = Field(..., description="Matthew's comment/response")
    mode: str = Field(
        ..., description="Response mode: 'auto', 'direct_chat', 'helpful', 'misleading'"
    )
    trust_level: int = Field(..., ge=0, le=100, description="Current trust level (0-100)")
    updated_state: dict[str, Any] | None = None


# ============================================
# LLM Configuration models
# ============================================


class VerifyKeyRequest(BaseModel):
    """Request to verify a user's API key."""

    provider: str = Field(..., description="Provider name (e.g. openrouter, anthropic)")
    api_key: str = Field(..., description="API key to verify")
    model: str | None = Field(None, description="Model to test with")


class VerifyKeyResponse(BaseModel):
    """Response from API key verification."""

    valid: bool
    error: str | None = None


class ModelInfo(BaseModel):
    """A recommended model option."""

    id: str
    name: str
    provider: str
    free: bool = False


# ============================================
# Case/Location models
# ============================================


class CaseListResponse(BaseModel):
    """Response from GET /api/cases endpoint."""

    cases: list[dict[str, Any]] = Field(default_factory=list, description="List of case metadata")
    count: int = Field(default=0, description="Number of valid cases")
    errors: list[str] | None = Field(default=None, description="Validation errors (if any)")


class LocationInfo(BaseModel):
    """Location metadata for LocationSelector."""

    id: str
    name: str
    type: str = "micro"


class ChangeLocationRequest(BaseModel):
    """Request for change-location endpoint."""

    location_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Target location ID",
    )
    slot: str = Field(
        default="autosave",
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Save slot to load/save state from",
    )
    request_id: RequestId = None


class ChangeLocationResponse(BaseModel):
    """Response from change-location endpoint."""

    success: bool
    location: dict[str, Any]
    updated_state: dict[str, Any] | None = None


# ============================================
# Telegram snapshot (internal gateway)
# ============================================


class TelegramWitnessSnapshot(BaseModel):
    """Canonical witness id + display name for Telegram clients."""

    id: str
    name: str
    description: str = ""


class TelegramEvidenceSnapshot(BaseModel):
    """Player-safe localized evidence text for Telegram casebook/buttons."""

    id: str
    name: str
    description: str = ""
    location_found: str = ""
    type: str = ""
    location_name: str = ""


class TelegramLocationSnapshot(BaseModel):
    """Player-safe localized location text for Telegram navigation."""

    id: str
    name: str
    description: str = ""


class TelegramSnapshotResponse(BaseModel):
    """Compact case snapshot for Telegram gateway. No secrets/solution."""

    case_id: str
    case_title: str = ""
    case_description: str = ""
    current_location: str
    current_location_view: TelegramLocationSnapshot | None = None
    available_locations: list[TelegramLocationSnapshot] = Field(default_factory=list)
    visited_locations: list[str] = Field(default_factory=list)
    discovered_evidence: list[str] = Field(default_factory=list)
    evidence_details: list[TelegramEvidenceSnapshot] = Field(default_factory=list)
    briefing_completed: bool = False
    language: str = "en"
    save_revision: int = 0
    available_witnesses: list[TelegramWitnessSnapshot] = Field(default_factory=list)
    verdict_attempts_remaining: int = 10
    case_solved: bool = False


# ============================================
# Telemetry models
# ============================================


class TelemetryEventRequest(BaseModel):
    """Request for telemetry event endpoint."""

    event_type: str = Field(..., max_length=64)
    case_id: str = Field(default="unknown", max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    data: dict[str, Any] = Field(default_factory=dict)


class TelemetryErrorRequest(BaseModel):
    """Request for telemetry error endpoint."""

    error_type: str = Field(..., max_length=64)
    case_id: str = Field(default="unknown", max_length=64)
    message: str = Field(..., max_length=500)
    context: dict[str, Any] = Field(default_factory=dict)


class TelemetryResponse(BaseModel):
    """Response from telemetry endpoints."""

    ok: bool
