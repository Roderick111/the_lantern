"""Tests for Phase 5.5 YAML schema enhancements.

Tests:
- New Pydantic models (Victim, EvidenceEnhanced, WitnessEnhanced, TimelineEntry, SolutionEnhanced)
- Validator Phase 5.5 checks (victim.name, wants/fears, strength, timeline)
- LLM prompt formatters for new fields
- Backward compatibility with existing case_001.yaml
"""

import pytest

from src.case_store.loader import (
    load_case,
    validate_case,
)
from src.context.mentor import (
    format_common_mistakes,
    format_fallacies_to_catch,
    format_timeline,
)
from src.context.narrator import (
    format_hidden_evidence,
    format_victim_context,
)
from src.context.matthew_llm import (
    format_evidence_by_strength,
    format_victim_for_matthew,
)
from src.context.witness import format_wants_fears
from src.state.player_state import (
    EvidenceEnhanced,
    SolutionEnhanced,
    TimelineEntry,
    Victim,
    WitnessEnhanced,
)

# ============================================================================
# Pydantic Model Tests
# ============================================================================


class TestVictimModel:
    """Tests for Victim Pydantic model."""

    def test_victim_with_all_fields(self) -> None:
        """Victim model accepts all fields."""
        victim = Victim(
            name="Marcus Webb",
            age="Fourth-year Candlewick",
            humanization="Known for helping first-years with homework.",
            memorable_trait="Always carried a lucky quill.",
            time_of_death="10:30 PM",
            cause_of_death="Freezing curse",
        )
        assert victim.name == "Marcus Webb"
        assert victim.age == "Fourth-year Candlewick"
        assert victim.memorable_trait == "Always carried a lucky quill."

    def test_victim_with_defaults(self) -> None:
        """Victim model provides defaults for optional fields."""
        victim = Victim(name="Test Victim")
        assert victim.name == "Test Victim"
        assert victim.age == ""
        assert victim.humanization == ""

    def test_victim_empty_name_allowed(self) -> None:
        """Victim can have empty name (backward compat)."""
        victim = Victim()
        assert victim.name == ""


class TestEvidenceEnhancedModel:
    """Tests for EvidenceEnhanced Pydantic model."""

    def test_evidence_enhanced_with_all_fields(self) -> None:
        """EvidenceEnhanced model accepts all fields."""
        evidence = EvidenceEnhanced(
            id="frost_pattern",
            name="Unnatural Frost Pattern",
            type="magical",
            significance="Proves freezing curse used at scene.",
            strength=90,
            points_to=["cassian"],
            contradicts=["elena_theory"],
        )
        assert evidence.id == "frost_pattern"
        assert evidence.strength == 90
        assert evidence.type == "magical"
        assert "cassian" in evidence.points_to

    def test_evidence_enhanced_defaults(self) -> None:
        """EvidenceEnhanced provides sensible defaults."""
        evidence = EvidenceEnhanced(id="test_evidence")
        assert evidence.strength == 50  # Default moderate
        assert evidence.type == "unknown"
        assert evidence.points_to == []
        assert evidence.significance == ""

    def test_evidence_strength_validation(self) -> None:
        """EvidenceEnhanced strength must be 0-100."""
        with pytest.raises(ValueError):
            EvidenceEnhanced(id="test", strength=150)

        with pytest.raises(ValueError):
            EvidenceEnhanced(id="test", strength=-10)


class TestWitnessEnhancedModel:
    """Tests for WitnessEnhanced Pydantic model."""

    def test_witness_enhanced_with_depth(self) -> None:
        """WitnessEnhanced accepts psychological depth fields."""
        witness = WitnessEnhanced(
            id="elena",
            name="Elena Marsh",
            personality="Intelligent, rule-following, anxious under pressure.",
            wants="To help find the truth and clear her name.",
            fears="Being blamed unfairly despite her innocence.",
            moral_complexity="She knows something but fears revealing it will make things worse.",
        )
        assert witness.wants != ""
        assert witness.fears != ""
        assert "truth" in witness.wants.lower()

    def test_witness_enhanced_defaults(self) -> None:
        """WitnessEnhanced provides empty defaults for depth fields."""
        witness = WitnessEnhanced(id="test", name="Test")
        assert witness.wants == ""
        assert witness.fears == ""
        assert witness.moral_complexity == ""


class TestTimelineEntryModel:
    """Tests for TimelineEntry Pydantic model."""

    def test_timeline_entry_full(self) -> None:
        """TimelineEntry accepts all fields."""
        entry = TimelineEntry(
            time="10:05 PM",
            event="Elena leaves library",
            witnesses=["crankshaw"],
            evidence=["hallway_log"],
        )
        assert entry.time == "10:05 PM"
        assert "crankshaw" in entry.witnesses

    def test_timeline_entry_defaults(self) -> None:
        """TimelineEntry defaults witnesses/evidence to empty lists."""
        entry = TimelineEntry(time="10:00 PM", event="Something happened")
        assert entry.witnesses == []
        assert entry.evidence == []


class TestSolutionEnhancedModel:
    """Tests for SolutionEnhanced Pydantic model."""

    def test_solution_enhanced_full(self) -> None:
        """SolutionEnhanced accepts all teaching fields."""
        solution = SolutionEnhanced(
            culprit="cassian",
            method="Freezing curse",
            motive="Revenge for perceived slight",
            key_evidence=["frost_pattern", "focus_signature"],
            deductions_required=[
                "Connect frost pattern to freezing curse",
                "Identify focus signature as Cassian's",
            ],
            correct_reasoning_requires=[
                "Understanding that Elena's alibi is solid",
            ],
            common_mistakes=[
                {
                    "error": "Accusing Elena",
                    "reason": "She was in the library",
                    "why_wrong": "Presence does not equal guilt",
                },
            ],
            fallacies_to_catch=[
                {"fallacy": "Confirmation bias", "example": "Ignoring exonerating evidence"},
            ],
        )
        assert solution.culprit == "cassian"
        assert len(solution.deductions_required) == 2
        assert len(solution.common_mistakes) == 1


# ============================================================================
# Loader Function Tests
# ============================================================================


# ============================================================================
# Validator Tests
# ============================================================================


class TestValidateCase:
    """Tests for validate_case with Phase 5.5 checks."""

    def test_validate_case_returns_three_tuple(self) -> None:
        """validate_case now returns (is_valid, errors, warnings)."""
        case_data = load_case("case_001")
        result = validate_case(case_data, "case_001")

        assert len(result) == 3
        is_valid, errors, warnings = result
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
        assert isinstance(warnings, list)

    def test_validate_case_backward_compatible(self) -> None:
        """case_001 without new fields still passes validation."""
        case_data = load_case("case_001")
        is_valid, errors, warnings = validate_case(case_data, "case_001")

        assert is_valid is True, f"Expected valid, got errors: {errors}"

    def test_validate_victim_name_required_if_present(self) -> None:
        """Victim section requires name if present."""
        mock_case = {
            "case": {
                "id": "test_case",
                "title": "Test",
                "difficulty": "beginner",
                "locations": {"room": {"hidden_evidence": [{"id": "e1"}]}},
                "witnesses": [{"id": "w1"}],
                "solution": {"culprit": "w1"},
                "briefing": {
                    "case_assignment": "Test",
                    "teaching_question": "Test?",
                },
                "victim": {"humanization": "No name given"},  # Missing name!
            }
        }
        is_valid, errors, warnings = validate_case(mock_case, "test_case")

        assert is_valid is False
        assert any("victim.name" in e for e in errors)

    def test_validate_wants_fears_consistency(self) -> None:
        """Wants without fears (or vice versa) is an error."""
        mock_case = {
            "case": {
                "id": "test_case",
                "title": "Test",
                "difficulty": "beginner",
                "locations": {"room": {"hidden_evidence": [{"id": "e1"}]}},
                "witnesses": [
                    {"id": "w1", "wants": "something", "fears": ""},  # Wants but no fears
                ],
                "solution": {"culprit": "w1"},
                "briefing": {
                    "case_assignment": "Test",
                    "teaching_question": "Test?",
                },
            }
        }
        is_valid, errors, warnings = validate_case(mock_case, "test_case")

        assert is_valid is False
        assert any("wants specified but fears missing" in e for e in errors)

    def test_validate_evidence_strength_range(self) -> None:
        """Evidence strength must be 0-100 if present."""
        mock_case = {
            "case": {
                "id": "test_case",
                "title": "Test",
                "difficulty": "beginner",
                "locations": {
                    "room": {
                        "hidden_evidence": [{"id": "e1", "strength": 150}]  # Invalid!
                    }
                },
                "witnesses": [{"id": "w1"}],
                "solution": {"culprit": "w1"},
                "briefing": {
                    "case_assignment": "Test",
                    "teaching_question": "Test?",
                },
            }
        }
        is_valid, errors, warnings = validate_case(mock_case, "test_case")

        assert is_valid is False
        assert any("strength must be integer 0-100" in e for e in errors)

    def test_validate_timeline_requires_time_event(self) -> None:
        """Timeline entries must have time and event."""
        mock_case = {
            "case": {
                "id": "test_case",
                "title": "Test",
                "difficulty": "beginner",
                "locations": {"room": {"hidden_evidence": [{"id": "e1"}]}},
                "witnesses": [{"id": "w1"}],
                "solution": {"culprit": "w1"},
                "briefing": {
                    "case_assignment": "Test",
                    "teaching_question": "Test?",
                },
                "timeline": [
                    {"time": "", "event": "Something"},  # Missing time!
                ],
            }
        }
        is_valid, errors, warnings = validate_case(mock_case, "test_case")

        assert is_valid is False
        assert any("missing required field 'time'" in e for e in errors)


# ============================================================================
# LLM Formatter Tests
# ============================================================================


class TestNarratorFormatters:
    """Tests for narrator.py Phase 5.5 formatters."""

    def test_format_victim_context_with_humanization(self) -> None:
        """format_victim_context includes humanization and cause."""
        victim = {
            "name": "Marcus Webb",
            "humanization": "A brilliant student who helped others.",
            "cause_of_death": "Freezing curse",
        }
        result = format_victim_context(victim)

        assert "Marcus Webb" in result
        assert "brilliant student" in result
        assert "Freezing curse" in result

    def test_format_victim_context_empty_if_no_humanization(self) -> None:
        """format_victim_context returns empty if no humanization."""
        victim = {"name": "Test"}
        result = format_victim_context(victim)

        assert result == ""

    def test_format_hidden_evidence_with_significance(self) -> None:
        """format_hidden_evidence includes significance when present."""
        evidence = [
            {
                "id": "frost_pattern",
                "triggers": ["frost", "ice"],
                "description": "Unusual frost on desk",
                "significance": "Proves freezing curse used",
            }
        ]
        result = format_hidden_evidence(evidence, [])

        assert "frost_pattern" in result
        assert "Strategic significance" in result
        assert "Proves freezing curse" in result


class TestWitnessFormatters:
    """Tests for witness.py Phase 5.5 formatters."""

    def test_format_wants_fears_all_fields(self) -> None:
        """format_wants_fears includes all psychological depth."""
        result = format_wants_fears(
            wants="To clear her name",
            fears="Being blamed unfairly",
            moral_complexity="She knows something but fears revealing it.",
        )

        assert "You want" in result
        assert "clear her name" in result
        assert "You fear" in result
        assert "Internal conflict" in result

    def test_format_wants_fears_empty_if_none(self) -> None:
        """format_wants_fears returns empty if no depth fields."""
        result = format_wants_fears("", "", "")
        assert result == ""


class TestMentorFormatters:
    """Tests for mentor.py Phase 5.5 formatters."""

    def test_format_common_mistakes(self) -> None:
        """format_common_mistakes formats mistake list."""
        mistakes = [
            {
                "error": "Accusing Elena",
                "reason": "She was present",
                "why_wrong": "Presence is not guilt",
            }
        ]
        result = format_common_mistakes(mistakes)

        assert "Accusing Elena" in result
        assert "Why players make this" in result
        assert "Why it's wrong" in result

    def test_format_fallacies_to_catch(self) -> None:
        """format_fallacies_to_catch formats fallacy list."""
        fallacies = [
            {"fallacy": "Confirmation bias", "example": "Ignoring alibi"},
        ]
        result = format_fallacies_to_catch(fallacies)

        assert "Confirmation bias" in result
        assert "Ignoring alibi" in result

    def test_format_timeline(self) -> None:
        """format_timeline formats timeline entries."""
        timeline = [
            {"time": "10:00 PM", "event": "Victim enters", "witnesses": ["crankshaw"]},
        ]
        result = format_timeline(timeline)

        assert "10:00 PM" in result
        assert "Victim enters" in result
        assert "crankshaw" in result


class TestMatthewFormatters:
    """Tests for matthew_llm.py Phase 5.5 formatters."""

    def test_format_evidence_by_strength_categorizes(self) -> None:
        """format_evidence_by_strength categorizes by strength."""
        evidence = [
            {"id": "strong_ev", "name": "Strong Evidence", "strength": 90},
            {"id": "weak_ev", "name": "Weak Evidence", "strength": 30},
        ]
        result = format_evidence_by_strength(evidence)

        assert "STRONG EVIDENCE" in result
        assert "CRITICAL" in result
        assert "WEAK/CIRCUMSTANTIAL" in result

    def test_format_victim_for_matthew_emotional(self) -> None:
        """format_victim_for_matthew includes emotional hook."""
        victim = {
            "name": "Marcus Webb",
            "humanization": "A kind student who helped others.",
        }
        result = format_victim_for_matthew(victim)

        assert "Marcus Webb" in result
        assert "Marcus" in result  # Victim humanization in Matthew context
        assert "kind student" in result

    def test_format_victim_for_matthew_empty_if_no_name(self) -> None:
        """format_victim_for_matthew returns empty if no victim name."""
        result = format_victim_for_matthew(None)
        assert result == ""

        result = format_victim_for_matthew({})
        assert result == ""
