"""Player state models.

Tracks investigation progress:
- Discovered evidence
- Visited locations
- Conversation history
- Witness interrogation states
- Submitted verdict
- Case metadata for discovery
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


# ============================================================================
# Phase 5.4: Case Discovery Models
# ============================================================================


class CaseMetadata(BaseModel):
    """Lightweight metadata for case discovery and landing page display.

    Used by GET /api/cases to list available cases without loading full case data.
    """

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9_]+$",
        description="Case identifier (lowercase, underscores only)",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Display title",
    )
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        ...,
        description="Case difficulty level",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="1-2 sentence case description for landing page",
    )


# ============================================================================
# Phase 5.5: Enhanced YAML Schema Models
# ============================================================================


class Victim(BaseModel):
    """Victim metadata for humanization and emotional stakes.

    Used by narrator LLM (crime scene descriptions) and Graves LLM (briefing/feedback).
    All fields optional except name for backward compatibility.
    """

    name: str = Field(
        default="",
        max_length=100,
        description="Victim's name",
    )
    age: str = Field(
        default="",
        max_length=100,
        description="Age or year (e.g., 'Fourth-year Candlewick')",
    )
    humanization: str = Field(
        default="",
        max_length=1000,
        description="2-3 sentence emotional hook connecting player to victim",
    )
    memorable_trait: str = Field(
        default="",
        max_length=200,
        description="One defining characteristic players remember",
    )
    time_of_death: str = Field(
        default="",
        max_length=100,
        description="Approximate time of death",
    )
    cause_of_death: str = Field(
        default="",
        max_length=200,
        description="How victim died (for crime scene context)",
    )


class EvidenceEnhanced(BaseModel):
    """Enhanced evidence metadata with strategic significance.

    Extends base evidence with fields for Graves feedback quality and Matthew commentary.
    """

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9_]+$",
        description="Evidence identifier",
    )
    name: str = Field(
        default="",
        max_length=100,
        description="Display name",
    )
    type: Literal["physical", "magical", "testimonial", "documentary", "unknown"] = Field(
        default="unknown",
        description="Evidence type category",
    )
    significance: str = Field(
        default="",
        max_length=500,
        description="Why this evidence matters (1-2 sentences)",
    )
    strength: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Evidence quality rating (100=irrefutable, 50=moderate, 20=weak)",
    )
    points_to: list[str] = Field(
        default_factory=list,
        description="Suspect IDs this evidence implicates",
    )
    contradicts: list[str] = Field(
        default_factory=list,
        description="Theories or suspect IDs this evidence disproves",
    )


class WitnessEnhanced(BaseModel):
    """Enhanced witness metadata with psychological depth.

    Used by witness LLM (personality context) and Graves LLM (feedback on witness handling).
    """

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9_]+$",
        description="Witness identifier",
    )
    name: str = Field(
        default="",
        max_length=100,
        description="Display name",
    )
    personality: str = Field(
        default="",
        max_length=1000,
        description="Personality description",
    )
    wants: str = Field(
        default="",
        max_length=500,
        description="What witness is trying to achieve (drives behavior)",
    )
    fears: str = Field(
        default="",
        max_length=500,
        description="What stops witness from helping (inhibits honesty)",
    )
    moral_complexity: str = Field(
        default="",
        max_length=1000,
        description="Internal conflict, why witness is torn (multiline)",
    )


class TimelineEntry(BaseModel):
    """Single event in case timeline.

    Used by narrator LLM (timeline references) and Graves LLM (alibi evaluation).
    """

    time: str = Field(
        ...,
        max_length=50,
        description="Time of event (e.g., '10:05 PM')",
    )
    event: str = Field(
        ...,
        max_length=500,
        description="What happened",
    )
    witnesses: list[str] = Field(
        default_factory=list,
        description="Witness IDs present at this time",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence IDs related to this event",
    )


class SolutionEnhanced(BaseModel):
    """Enhanced solution metadata for educational feedback.

    Used by Graves LLM for verdict evaluation and teaching moments.
    """

    culprit: str = Field(
        ...,
        pattern=r"^[a-z0-9_]+$",
        description="Culprit witness ID",
    )
    method: str = Field(
        default="",
        max_length=500,
        description="How the crime was committed",
    )
    motive: str = Field(
        default="",
        max_length=500,
        description="Why the culprit committed the crime",
    )
    key_evidence: list[str] = Field(
        default_factory=list,
        description="Evidence IDs that prove guilt",
    )
    deductions_required: list[str] = Field(
        default_factory=list,
        description="Logical steps player must take to reach correct conclusion",
    )
    correct_reasoning_requires: list[str] = Field(
        default_factory=list,
        description="Key insights player must understand",
    )
    common_mistakes: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {error, reason, why_wrong} objects",
    )
    fallacies_to_catch: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {fallacy, example} objects",
    )


class ConversationItem(BaseModel):
    """Single conversation exchange with witness."""

    question: str
    response: str
    timestamp: datetime = Field(default_factory=_utc_now)
    trust_delta: int = 0


class VerdictAttempt(BaseModel):
    """Single verdict attempt."""

    accused_suspect_id: str
    reasoning: str
    evidence_cited: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=_utc_now)
    correct: bool
    score: int
    fallacies_detected: list[str] = Field(default_factory=list)


class VerdictState(BaseModel):
    """Verdict submission state."""

    model_config = ConfigDict(extra="ignore")

    case_id: str
    attempts: list[VerdictAttempt] = Field(default_factory=list)
    attempts_remaining: int = 10
    case_solved: bool = False
    final_verdict: VerdictAttempt | None = None

    def add_attempt(
        self,
        accused_id: str,
        reasoning: str,
        evidence_cited: list[str],
        correct: bool,
        score: int,
        fallacies: list[str],
    ) -> None:
        """Add verdict attempt.

        Args:
            accused_id: Who player accused
            reasoning: Player's reasoning text
            evidence_cited: Evidence IDs player selected
            correct: Whether verdict was correct
            score: Reasoning quality score
            fallacies: Fallacies detected in reasoning
        """
        attempt = VerdictAttempt(
            accused_suspect_id=accused_id,
            reasoning=reasoning,
            evidence_cited=evidence_cited,
            correct=correct,
            score=score,
            fallacies_detected=fallacies,
        )
        self.attempts.append(attempt)
        self.attempts_remaining -= 1

        if correct:
            self.case_solved = True
            self.final_verdict = attempt

    def get_attempt_count(self) -> int:
        """Get number of attempts made."""
        return len(self.attempts)


class WitnessState(BaseModel):
    """State tracking for a specific witness interrogation."""

    model_config = ConfigDict(extra="ignore")

    witness_id: str
    trust: int
    conversation_history: list[ConversationItem] = Field(default_factory=list)
    secrets_revealed: list[str] = Field(default_factory=list)
    awaiting_spell_confirmation: str | None = (
        None  # Spell awaiting confirmation (e.g., "mnemonic_delving")
    )
    # Phase 4.8: Mnemonic Delving consequence tracking
    mnemonic_delving_detected: bool = False  # Track if Mnemonic Delving was detected
    spell_attempts: dict[str, int] = Field(default_factory=dict)  # Track spell attempts by spell_id

    # Phase 5.5+: Track evidence shown to this witness (for one-time bonus)
    evidence_shown: list[str] = Field(default_factory=list)

    _MAX_CONVERSATION_HISTORY = 50

    def add_conversation(
        self,
        question: str,
        response: str,
        trust_delta: int = 0,
    ) -> None:
        """Add conversation exchange to history (capped at 50 entries)."""
        self.conversation_history.append(
            ConversationItem(
                question=question,
                response=response,
                trust_delta=trust_delta,
            )
        )
        if len(self.conversation_history) > self._MAX_CONVERSATION_HISTORY:
            self.conversation_history = self.conversation_history[
                -self._MAX_CONVERSATION_HISTORY :
            ]

    def reveal_secret(self, secret_id: str) -> None:
        """Mark secret as revealed (deduplicated)."""
        if secret_id not in self.secrets_revealed:
            self.secrets_revealed.append(secret_id)

    def adjust_trust(self, delta: int) -> None:
        """Adjust trust level (clamped 0-100)."""
        self.trust = max(0, min(100, self.trust + delta))

    def mark_evidence_shown(self, evidence_id: str) -> bool:
        """Mark evidence as shown to this witness.

        Args:
            evidence_id: Evidence ID being shown

        Returns:
            True if this is first time showing, False if already shown
        """
        if evidence_id not in self.evidence_shown:
            self.evidence_shown.append(evidence_id)
            return True
        return False

    def get_history_as_dicts(self) -> list[dict[str, Any]]:
        """Get conversation history as list of dicts for prompt building."""
        return [
            {"question": item.question, "response": item.response}
            for item in self.conversation_history
        ]


class BriefingState(BaseModel):
    """State for intro briefing with Inspector Graves."""

    model_config = ConfigDict(extra="ignore")

    case_id: str
    briefing_completed: bool = False
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    completed_at: datetime | None = None

    _MAX_CONVERSATION_HISTORY = 30

    def add_question(self, question: str, answer: str) -> None:
        """Add Q&A exchange to conversation history.

        Args:
            question: Player's question
            answer: Graves's response
        """
        self.conversation_history.append({"question": question, "answer": answer})
        if len(self.conversation_history) > self._MAX_CONVERSATION_HISTORY:
            self.conversation_history = self.conversation_history[
                -self._MAX_CONVERSATION_HISTORY :
            ]

    def mark_complete(self) -> None:
        """Mark briefing as completed."""
        self.briefing_completed = True
        self.completed_at = _utc_now()


class MatthewTriggerRecord(BaseModel):
    """Single Matthew spirit companion trigger event.

    Records when a trigger fired with context for debugging/analytics.
    """

    trigger_id: str
    text: str
    type: str  # "helpful" | "misleading" | "self_aware" | "dark_humor" | "emotional"
    tier: int  # 1 | 2 | 3
    timestamp: datetime = Field(default_factory=_utc_now)
    evidence_count_at_fire: int


class MatthewCompanionState(BaseModel):
    """State for Matthew's spirit companion system."""

    model_config = ConfigDict(extra="ignore")

    case_id: str
    fired_triggers: list[str] = Field(default_factory=list)  # LEGACY for YAML triggers
    trigger_history: list[MatthewTriggerRecord] = Field(default_factory=list)
    total_interruptions: int = 0  # Renamed semantically but kept for compat
    last_interruption_at: datetime | None = None

    # Phase 4.1: Trust system and LLM mode
    trust_level: float = Field(default=0.0, ge=0.0, le=1.0)  # 0.0-1.0
    cases_completed: int = Field(default=0, ge=0)  # Track across saves
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    total_comments: int = 0  # LLM-based comment count
    last_comment_at: datetime | None = None

    _MAX_CONVERSATION_HISTORY = 50

    def get_trust_percentage(self) -> int:
        """Return trust as 0-100 integer for display.

        Returns:
            Trust level as percentage (0-100)
        """
        return int(self.trust_level * 100)

    def calculate_trust_from_cases(self) -> float:
        """Calculate trust level from completed cases.

        10% per completed case (0% -> 100% over 10 cases).

        Returns:
            Trust level as 0.0-1.0 float
        """
        return min(1.0, self.cases_completed * 0.1)

    def increment_trust(self, amount: float = 0.1) -> None:
        """Increase trust level (call on case completion).

        Args:
            amount: Amount to increase trust by (default 0.1 = 10%)
        """
        self.trust_level = min(1.0, self.trust_level + amount)

    def mark_case_complete(self) -> None:
        """Mark a case as completed and update trust.

        Called when player solves a case correctly.
        """
        self.cases_completed += 1
        self.trust_level = self.calculate_trust_from_cases()

    def add_matthew_comment(self, user_msg: str | None, matthew_response: str) -> None:
        """Add Matthew conversation exchange to history.

        Args:
            user_msg: Player's message (None if auto-comment)
            matthew_response: Matthew's response text
        """
        self.conversation_history.append(
            {
                "user": user_msg or "[auto-comment]",
                "matthew": matthew_response,
                "timestamp": _utc_now().isoformat(),
            }
        )
        if len(self.conversation_history) > self._MAX_CONVERSATION_HISTORY:
            self.conversation_history = self.conversation_history[
                -self._MAX_CONVERSATION_HISTORY :
            ]
        self.total_comments += 1
        self.last_comment_at = _utc_now()

    def fire_trigger(
        self,
        trigger_id: str,
        text: str,
        trigger_type: str,
        tier: int,
        evidence_count: int,
    ) -> None:
        """Record a fired trigger.

        Args:
            trigger_id: Unique trigger ID
            text: Matthew's message text
            trigger_type: Type of trigger (helpful/misleading/etc.)
            tier: Trigger tier (1/2/3)
            evidence_count: Evidence count when fired
        """
        self.fired_triggers.append(trigger_id)
        self.trigger_history.append(
            MatthewTriggerRecord(
                trigger_id=trigger_id,
                text=text,
                type=trigger_type,
                tier=tier,
                evidence_count_at_fire=evidence_count,
            )
        )
        self.total_interruptions += 1
        self.last_interruption_at = _utc_now()


class PlayerState(BaseModel):
    """Player investigation state."""

    model_config = ConfigDict(extra="ignore")

    state_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str
    current_location: str
    # Phase 5.3: Save file versioning for migration
    version: str = Field(default="1.0.0", description="Save file version for migration")
    save_revision: int = Field(
        default=0,
        ge=0,
        description="Optimistic concurrency revision — incremented on each successful save",
    )
    last_saved: datetime | None = Field(default=None, description="Timestamp of last save")
    discovered_evidence: list[str] = Field(default_factory=list)
    visited_locations: list[str] = Field(default_factory=list)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    witness_states: dict[str, WitnessState] = Field(default_factory=dict)
    narrator_conversation_history: list[ConversationItem] = Field(default_factory=list)
    # Phase 5.6: Location-specific history
    location_chat_history: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    location_narrator_history: dict[str, list[ConversationItem]] = Field(default_factory=dict)
    # Narrator verbosity style: "concise" | "storyteller" | "atmospheric"
    narrator_verbosity: str = Field(default="storyteller", description="Narrator style verbosity")
    assistance_mode: Literal["normal", "easy"] = Field(
        default="normal", description="Narrator assistance: normal | easy"
    )
    # Game language (ISO 639-1): "en", "ru", "fr", "es", "de", "pt", "zh", "ja", "ko"
    language: str = Field(default="en", description="Game response language")

    submitted_verdict: dict[str, str] | None = None
    verdict_state: VerdictState | None = None
    briefing_state: BriefingState | None = None
    matthew_companion_state: MatthewCompanionState | None = Field(
        default=None,
        validation_alias=AliasChoices("matthew_companion_state", "inner_voice_state"),
    )
    # Phase 4.7: Spell attempt tracking per location per spell
    # Example: {"library": {"unveil": 2, "raise_the_lamp": 1}, "dormitory": {"unveil": 1}}
    spell_attempts_by_location: dict[str, dict[str, int]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    def add_evidence(self, evidence_id: str) -> None:
        """Add discovered evidence (deduplicated)."""
        if evidence_id not in self.discovered_evidence:
            self.discovered_evidence.append(evidence_id)
            self.updated_at = _utc_now()

    def visit_location(self, location_id: str) -> None:
        """Track visited location."""
        self.current_location = location_id
        if location_id not in self.visited_locations:
            self.visited_locations.append(location_id)
        self.updated_at = _utc_now()

    def get_witness_state(self, witness_id: str, base_trust: int = 50) -> WitnessState:
        """Get or create witness state.

        Args:
            witness_id: Witness identifier
            base_trust: Initial trust if creating new state

        Returns:
            WitnessState for the witness
        """
        if witness_id not in self.witness_states:
            self.witness_states[witness_id] = WitnessState(
                witness_id=witness_id,
                trust=base_trust,
            )
            self.updated_at = _utc_now()

        return self.witness_states[witness_id]

    def update_witness_state(self, witness_state: WitnessState) -> None:
        """Update witness state in player state.

        Args:
            witness_state: Updated witness state
        """
        self.witness_states[witness_state.witness_id] = witness_state
        self.updated_at = _utc_now()

    def get_briefing_state(self) -> BriefingState:
        """Get or create briefing state.

        Returns:
            BriefingState for the player
        """
        if self.briefing_state is None:
            self.briefing_state = BriefingState(case_id=self.case_id)
            self.updated_at = _utc_now()
        return self.briefing_state

    def mark_briefing_complete(self) -> None:
        """Mark briefing as completed."""
        briefing = self.get_briefing_state()
        briefing.mark_complete()
        self.updated_at = _utc_now()

    def get_matthew_companion_state(self) -> MatthewCompanionState:
        """Get or create Matthew companion state.

        Returns:
            MatthewCompanionState for spirit companion system
        """
        if self.matthew_companion_state is None:
            self.matthew_companion_state = MatthewCompanionState(case_id=self.case_id)
            self.updated_at = _utc_now()
        return self.matthew_companion_state

    def add_conversation_message(
        self,
        msg_type: str,
        text: str,
        timestamp: int | None = None,
        location_id: str | None = None,
    ) -> None:
        """Add message to conversation history (per location).

        Args:
            msg_type: Message type (player/narrator/matthew)
            text: Message text content
            timestamp: Unix timestamp in milliseconds (defaults to now)
            location_id: Current location ID for scoped history
        """
        message = {
            "type": msg_type,
            "text": text,
            "timestamp": timestamp or int(_utc_now().timestamp() * 1000),
        }

        # Add to global history (legacy/backup)
        self.conversation_history.append(message)
        if len(self.conversation_history) > 50:  # Increased limit for global
            self.conversation_history = self.conversation_history[-50:]

        # Add to location-specific history
        current_loc = location_id or self.current_location
        if current_loc:
            if current_loc not in self.location_chat_history:
                self.location_chat_history[current_loc] = []

            self.location_chat_history[current_loc].append(message)
            # Keep last 30 messages per location
            if len(self.location_chat_history[current_loc]) > 30:
                self.location_chat_history[current_loc] = self.location_chat_history[current_loc][
                    -30:
                ]

        self.updated_at = _utc_now()

    def add_narrator_conversation(
        self,
        player_action: str,
        narrator_response: str,
        location_id: str | None = None,
    ) -> None:
        """Add narrator conversation exchange (scoped to location).

        Args:
            player_action: Player's investigation action
            narrator_response: Narrator's response
            location_id: Current location ID
        """
        # Legacy global list update (still useful for some contexts maybe?)
        self.narrator_conversation_history.append(
            ConversationItem(
                question=player_action,
                response=narrator_response,
                trust_delta=0,
            )
        )
        if len(self.narrator_conversation_history) > 5:
            self.narrator_conversation_history = self.narrator_conversation_history[-5:]

        # Location-specific update
        current_loc = location_id or self.current_location
        if current_loc:
            if current_loc not in self.location_narrator_history:
                self.location_narrator_history[current_loc] = []

            self.location_narrator_history[current_loc].append(
                ConversationItem(
                    question=player_action,
                    response=narrator_response,
                    trust_delta=0,
                )
            )
            # Keep only last 5 exchanges per location context
            if len(self.location_narrator_history[current_loc]) > 5:
                self.location_narrator_history[current_loc] = self.location_narrator_history[
                    current_loc
                ][-5:]

        self.updated_at = _utc_now()

    def get_narrator_history_as_dicts(self, location_id: str | None = None) -> list[dict[str, Any]]:
        """Get narrator conversation history as dicts for prompt (scoped to location).

        Args:
            location_id: Location to get history for. If None, falls back to global list
                for backward compatibility.
        """
        if location_id:
            # Phase 5.6: Strict isolation - if location provided, use ONLY that location's history
            # If not found, return empty list (don't leak global history)
            source_list = self.location_narrator_history.get(location_id, [])
        else:
            # Fallback to global only if no location specified (legacy support)
            source_list = self.narrator_conversation_history

        return [{"question": item.question, "response": item.response} for item in source_list]
