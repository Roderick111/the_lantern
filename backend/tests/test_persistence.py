"""Tests for state persistence module."""

import pytest

from src.state.persistence import delete_state, load_state, save_state
from src.state.player_state import PlayerState, VerdictAttempt, VerdictState, WitnessState


@pytest.fixture
def sample_state() -> PlayerState:
    """Create sample player state."""
    return PlayerState(
        case_id="case_001",
        current_location="library",
        discovered_evidence=["hidden_note"],
        visited_locations=["library"],
    )


class TestSaveState:
    """Tests for save_state function."""

    def test_save_returns_true(self, sample_state: PlayerState) -> None:
        """Save returns True on success."""
        result = save_state(sample_state, "player_1")
        assert result is True

    def test_save_data_is_loadable(self, sample_state: PlayerState) -> None:
        """Saved data can be loaded back."""
        save_state(sample_state, "player_1")
        loaded = load_state("case_001", "player_1")

        assert loaded is not None
        assert loaded.case_id == "case_001"
        assert loaded.current_location == "library"
        assert "hidden_note" in loaded.discovered_evidence

    def test_save_overwrites_existing(self, sample_state: PlayerState) -> None:
        """Save overwrites existing save."""
        save_state(sample_state, "player_1")

        # Modify state
        sample_state.add_evidence("focus_signature")
        save_state(sample_state, "player_1")

        # Load and verify
        loaded = load_state("case_001", "player_1")
        assert loaded is not None
        assert "focus_signature" in loaded.discovered_evidence


class TestLoadState:
    """Tests for load_state function."""

    def test_load_returns_player_state(self, sample_state: PlayerState) -> None:
        """Load returns PlayerState instance."""
        save_state(sample_state, "player_1")

        loaded = load_state("case_001", "player_1")

        assert loaded is not None
        assert isinstance(loaded, PlayerState)

    def test_load_preserves_data(self, sample_state: PlayerState) -> None:
        """Load preserves all state data."""
        save_state(sample_state, "player_1")

        loaded = load_state("case_001", "player_1")

        assert loaded is not None
        assert loaded.case_id == sample_state.case_id
        assert loaded.current_location == sample_state.current_location
        assert loaded.discovered_evidence == sample_state.discovered_evidence
        assert loaded.visited_locations == sample_state.visited_locations

    def test_load_nonexistent_returns_none(self) -> None:
        """Load returns None for missing file."""
        loaded = load_state("case_001", "player_999")

        assert loaded is None

    def test_roundtrip_preserves_state(self, sample_state: PlayerState) -> None:
        """Save/load roundtrip preserves state."""
        # Add more data
        sample_state.add_evidence("focus_signature")
        sample_state.visit_location("corridor")

        save_state(sample_state, "player_1")
        loaded = load_state("case_001", "player_1")

        assert loaded is not None
        assert loaded.discovered_evidence == ["hidden_note", "focus_signature"]
        assert loaded.current_location == "corridor"
        assert "corridor" in loaded.visited_locations


class TestDeleteState:
    """Tests for delete_state function."""

    def test_delete_removes_save(self, sample_state: PlayerState) -> None:
        """Delete removes save entry."""
        save_state(sample_state, "player_1")
        assert load_state("case_001", "player_1") is not None

        result = delete_state("case_001", "player_1")

        assert result is True
        assert load_state("case_001", "player_1") is None

    def test_delete_nonexistent_returns_false(self) -> None:
        """Delete returns False for missing file."""
        result = delete_state("case_001", "player_999")

        assert result is False


class TestMultipleSaves:
    """Tests for saving/loading multiple states."""

    def test_no_saves_returns_none(self) -> None:
        """Load returns None when nothing saved."""
        assert load_state("case_001", "player_1") is None

    def test_multiple_cases_independent(self) -> None:
        """Saves for different cases are independent."""
        state1 = PlayerState(case_id="case_001", current_location="library")
        state2 = PlayerState(case_id="case_002", current_location="dormitory")

        save_state(state1, "player_1")
        save_state(state2, "player_1")

        loaded1 = load_state("case_001", "player_1")
        loaded2 = load_state("case_002", "player_1")

        assert loaded1 is not None
        assert loaded2 is not None
        assert loaded1.current_location == "library"
        assert loaded2.current_location == "dormitory"

    def test_multiple_players_independent(self) -> None:
        """Saves for different players are independent."""
        state1 = PlayerState(case_id="case_001", current_location="library")
        state2 = PlayerState(case_id="case_001", current_location="corridor")

        save_state(state1, "player_1")
        save_state(state2, "player_2")

        loaded1 = load_state("case_001", "player_1")
        loaded2 = load_state("case_001", "player_2")

        assert loaded1 is not None
        assert loaded2 is not None
        assert loaded1.current_location == "library"
        assert loaded2.current_location == "corridor"


class TestWitnessStatePersistence:
    """Tests for witness state persistence."""

    def test_save_load_witness_state(self) -> None:
        """Witness state persists through save/load."""
        state = PlayerState(case_id="case_001", current_location="library")

        # Create witness state
        witness_state = state.get_witness_state("elena", base_trust=50)
        witness_state.adjust_trust(10)
        witness_state.add_conversation("Where were you?", "In the library.")
        witness_state.reveal_secret("saw_cassian")

        save_state(state, "player_1")
        loaded = load_state("case_001", "player_1")

        assert loaded is not None
        assert "elena" in loaded.witness_states
        ws = loaded.witness_states["elena"]
        assert ws.trust == 60
        assert len(ws.conversation_history) == 1
        assert ws.conversation_history[0].question == "Where were you?"
        assert "saw_cassian" in ws.secrets_revealed

    def test_multiple_witness_states(self) -> None:
        """Multiple witness states persist."""
        state = PlayerState(case_id="case_001", current_location="library")

        # Create states for two witnesses
        elena = state.get_witness_state("elena", base_trust=50)
        elena.adjust_trust(5)

        cassian = state.get_witness_state("cassian", base_trust=20)
        cassian.adjust_trust(-5)

        save_state(state, "player_1")
        loaded = load_state("case_001", "player_1")

        assert loaded is not None
        assert loaded.witness_states["elena"].trust == 55
        assert loaded.witness_states["cassian"].trust == 15


class TestWitnessStateModel:
    """Tests for WitnessState model methods."""

    def test_adjust_trust_clamps_to_range(self) -> None:
        """Trust clamped to 0-100."""
        ws = WitnessState(witness_id="test", trust=50)

        ws.adjust_trust(100)
        assert ws.trust == 100

        ws.adjust_trust(-200)
        assert ws.trust == 0

    def test_reveal_secret_deduplicates(self) -> None:
        """Secrets deduplicated."""
        ws = WitnessState(witness_id="test", trust=50)

        ws.reveal_secret("secret1")
        ws.reveal_secret("secret1")
        ws.reveal_secret("secret2")

        assert ws.secrets_revealed == ["secret1", "secret2"]

    def test_get_history_as_dicts(self) -> None:
        """History converted to dicts for prompts."""
        ws = WitnessState(witness_id="test", trust=50)
        ws.add_conversation("Q1", "R1")
        ws.add_conversation("Q2", "R2")

        history = ws.get_history_as_dicts()

        assert len(history) == 2
        assert history[0] == {"question": "Q1", "response": "R1"}
        assert history[1] == {"question": "Q2", "response": "R2"}


# Phase 3: Verdict state tests


class TestVerdictAttemptModel:
    """Tests for VerdictAttempt model."""

    def test_create_verdict_attempt(self) -> None:
        """Create VerdictAttempt with all fields."""
        attempt = VerdictAttempt(
            accused_suspect_id="elena",
            reasoning="She was there.",
            evidence_cited=["hidden_note"],
            correct=False,
            score=45,
            fallacies_detected=["correlation_not_causation"],
        )

        assert attempt.accused_suspect_id == "elena"
        assert attempt.reasoning == "She was there."
        assert attempt.evidence_cited == ["hidden_note"]
        assert attempt.correct is False
        assert attempt.score == 45
        assert attempt.fallacies_detected == ["correlation_not_causation"]

    def test_verdict_attempt_has_timestamp(self) -> None:
        """VerdictAttempt has auto-generated timestamp."""
        attempt = VerdictAttempt(
            accused_suspect_id="cassian",
            reasoning="Test",
            correct=True,
            score=90,
        )

        assert attempt.timestamp is not None


class TestVerdictStateModel:
    """Tests for VerdictState model."""

    def test_create_verdict_state(self) -> None:
        """Create VerdictState with defaults."""
        vs = VerdictState(case_id="case_001")

        assert vs.case_id == "case_001"
        assert vs.attempts == []
        assert vs.attempts_remaining == 10
        assert vs.case_solved is False
        assert vs.final_verdict is None

    def test_add_attempt_incorrect(self) -> None:
        """Add incorrect verdict attempt."""
        vs = VerdictState(case_id="case_001")

        vs.add_attempt(
            accused_id="elena",
            reasoning="She was there.",
            evidence_cited=[],
            correct=False,
            score=40,
            fallacies=["confirmation_bias"],
        )

        assert len(vs.attempts) == 1
        assert vs.attempts_remaining == 9
        assert vs.case_solved is False
        assert vs.final_verdict is None

    def test_add_attempt_correct(self) -> None:
        """Add correct verdict attempt."""
        vs = VerdictState(case_id="case_001")

        vs.add_attempt(
            accused_id="cassian",
            reasoning="The focus signature proves it.",
            evidence_cited=["focus_signature", "frost_pattern"],
            correct=True,
            score=90,
            fallacies=[],
        )

        assert len(vs.attempts) == 1
        assert vs.attempts_remaining == 9
        assert vs.case_solved is True
        assert vs.final_verdict is not None
        assert vs.final_verdict.accused_suspect_id == "cassian"

    def test_get_attempt_count(self) -> None:
        """Get attempt count returns correct number."""
        vs = VerdictState(case_id="case_001")

        assert vs.get_attempt_count() == 0

        vs.add_attempt("a", "r", [], False, 50, [])
        assert vs.get_attempt_count() == 1

        vs.add_attempt("b", "r", [], False, 50, [])
        assert vs.get_attempt_count() == 2

    def test_attempts_remaining_decrements(self) -> None:
        """Attempts remaining decrements with each attempt."""
        vs = VerdictState(case_id="case_001")
        assert vs.attempts_remaining == 10

        for i in range(3):
            vs.add_attempt(f"suspect_{i}", "reason", [], False, 50, [])

        assert vs.attempts_remaining == 7


class TestVerdictStatePersistence:
    """Tests for verdict state persistence."""

    def test_save_load_verdict_state(self) -> None:
        """Verdict state persists through save/load."""
        state = PlayerState(case_id="case_001", current_location="library")

        # Create verdict state
        state.verdict_state = VerdictState(case_id="case_001")
        state.verdict_state.add_attempt(
            accused_id="elena",
            reasoning="She was there.",
            evidence_cited=["hidden_note"],
            correct=False,
            score=45,
            fallacies=["confirmation_bias"],
        )

        save_state(state, "player_1")
        loaded = load_state("case_001", "player_1")

        assert loaded is not None
        assert loaded.verdict_state is not None
        assert loaded.verdict_state.attempts_remaining == 9
        assert len(loaded.verdict_state.attempts) == 1
        assert loaded.verdict_state.attempts[0].accused_suspect_id == "elena"

    def test_save_load_solved_case(self) -> None:
        """Solved case persists correctly."""
        state = PlayerState(case_id="case_001", current_location="library")
        state.verdict_state = VerdictState(case_id="case_001")
        state.verdict_state.add_attempt(
            accused_id="cassian",
            reasoning="The evidence proves it.",
            evidence_cited=["frost_pattern"],
            correct=True,
            score=90,
            fallacies=[],
        )

        save_state(state, "player_1")
        loaded = load_state("case_001", "player_1")

        assert loaded is not None
        assert loaded.verdict_state is not None
        assert loaded.verdict_state.case_solved is True
        assert loaded.verdict_state.final_verdict is not None
