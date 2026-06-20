"""Tests for evidence trigger matching utilities."""

import pytest

from src.utils.evidence import (
    check_already_discovered,
    extract_evidence_from_response,
    extract_flags_from_response,
    find_not_present_response,
    matches_trigger,
)


class TestMatchesTrigger:
    """Tests for matches_trigger function."""

    def test_exact_match(self) -> None:
        """Exact trigger match."""
        triggers = ["under desk", "check drawers"]
        assert matches_trigger("under desk", triggers) is True

    def test_substring_match(self) -> None:
        """Trigger as substring of input."""
        triggers = ["under desk"]
        assert matches_trigger("I look under desk carefully", triggers) is True

    def test_case_insensitive(self) -> None:
        """Case insensitive matching."""
        triggers = ["under desk"]
        assert matches_trigger("I look UNDER DESK", triggers) is True
        assert matches_trigger("Under Desk please", triggers) is True

    def test_no_match(self) -> None:
        """No trigger match."""
        triggers = ["under desk", "check drawers"]
        assert matches_trigger("look at window", triggers) is False

    def test_partial_word_match(self) -> None:
        """Trigger matches partial word."""
        triggers = ["desk"]
        assert matches_trigger("I search the desk area", triggers) is True

    def test_multiple_triggers(self) -> None:
        """Any trigger matches."""
        triggers = ["under desk", "beneath desk", "search desk", "check drawers"]
        assert matches_trigger("check drawers now", triggers) is True

    def test_phrase_trigger(self) -> None:
        """Multi-word phrase trigger."""
        triggers = ["echo reading"]
        assert matches_trigger("I cast echo reading on the focus", triggers) is True

    def test_empty_triggers(self) -> None:
        """Empty triggers list."""
        assert matches_trigger("anything", []) is False

    def test_empty_input(self) -> None:
        """Empty player input."""
        triggers = ["desk"]
        assert matches_trigger("", triggers) is False



class TestFindNotPresentResponse:
    """Tests for find_not_present_response function."""

    @pytest.fixture
    def not_present_items(self) -> list[dict]:
        """Sample not_present items."""
        return [
            {
                "triggers": ["secret passage", "hidden door"],
                "response": "The walls are solid stone. No hidden passages here.",
            },
            {
                "triggers": ["blood", "blood stains"],
                "response": "There's no blood visible.",
            },
        ]

    def test_find_not_present_response(self, not_present_items: list[dict]) -> None:
        """Find not_present response."""
        result = find_not_present_response(
            "is there a secret passage?",
            not_present_items,
        )

        assert result == "The walls are solid stone. No hidden passages here."

    def test_no_not_present_match(self, not_present_items: list[dict]) -> None:
        """No not_present match."""
        result = find_not_present_response(
            "examine the desk",
            not_present_items,
        )

        assert result is None


class TestExtractEvidenceFromResponse:
    """Tests for extract_evidence_from_response function."""

    def test_extract_single_tag(self) -> None:
        """Extract single evidence tag."""
        response = "You find a note. [EVIDENCE: hidden_note]"
        result = extract_evidence_from_response(response)

        assert result == ["hidden_note"]

    def test_extract_multiple_tags(self) -> None:
        """Extract multiple evidence tags."""
        response = """You discover [EVIDENCE: note1] and also [EVIDENCE: note2]."""
        result = extract_evidence_from_response(response)

        assert result == ["note1", "note2"]

    def test_case_insensitive_tag(self) -> None:
        """Case insensitive tag extraction."""
        response = "Found it! [evidence: hidden_note]"
        result = extract_evidence_from_response(response)

        assert result == ["hidden_note"]

    def test_no_tags(self) -> None:
        """No evidence tags in response."""
        response = "You search but find nothing of interest."
        result = extract_evidence_from_response(response)

        assert result == []

    def test_tag_with_spaces(self) -> None:
        """Tag with extra spaces."""
        response = "[EVIDENCE:   spaced_id   ] was found."
        result = extract_evidence_from_response(response)

        assert result == ["spaced_id"]

    def test_tag_with_underscores(self) -> None:
        """Tag with underscores in ID."""
        response = "[EVIDENCE: focus_last_spell_signature]"
        result = extract_evidence_from_response(response)

        assert result == ["focus_last_spell_signature"]


class TestCheckAlreadyDiscovered:
    """Tests for check_already_discovered function."""

    @pytest.fixture
    def sample_evidence(self) -> list[dict]:
        """Sample hidden evidence."""
        return [
            {
                "id": "hidden_note",
                "triggers": ["under desk", "search desk"],
            },
            {
                "id": "focus_signature",
                "triggers": ["examine focus"],
            },
        ]

    def test_asking_about_discovered(self, sample_evidence: list[dict]) -> None:
        """Player asking about discovered evidence."""
        # "search desk" is the trigger
        result = check_already_discovered(
            "I want to search desk again",
            sample_evidence,
            discovered_ids=["hidden_note"],
        )

        assert result is True

    def test_asking_about_undiscovered(self, sample_evidence: list[dict]) -> None:
        """Player asking about undiscovered evidence."""
        result = check_already_discovered(
            "examine the focus",
            sample_evidence,
            discovered_ids=[],
        )

        assert result is False

    def test_unrelated_input(self, sample_evidence: list[dict]) -> None:
        """Unrelated player input."""
        result = check_already_discovered(
            "look at the ceiling",
            sample_evidence,
            discovered_ids=["hidden_note"],
        )

        assert result is False


class TestExtractFlagsFromResponse:
    """Tests for extract_flags_from_response function."""

    def test_extract_single_flag(self) -> None:
        """Extract single flag tag."""
        response = "You intrude on her thoughts. [FLAG: relationship_damaged]"
        result = extract_flags_from_response(response)

        assert result == ["relationship_damaged"]

    def test_extract_multiple_flags(self) -> None:
        """Extract multiple flag tags."""
        response = """The mental shields slam back! [FLAG: mental_strain]
        She recoils in horror. [FLAG: relationship_damaged]"""
        result = extract_flags_from_response(response)

        assert result == ["mental_strain", "relationship_damaged"]

    def test_case_insensitive_flag(self) -> None:
        """Case insensitive flag extraction."""
        response = "Trust broken. [flag: relationship_damaged]"
        result = extract_flags_from_response(response)

        assert result == ["relationship_damaged"]

    def test_no_flags(self) -> None:
        """No flag tags in response."""
        response = "You search but find nothing of interest."
        result = extract_flags_from_response(response)

        assert result == []

    def test_flag_with_spaces(self) -> None:
        """Flag with space before name (trailing spaces not supported)."""
        response = "[FLAG:   mental_strain] was triggered."
        result = extract_flags_from_response(response)

        assert result == ["mental_strain"]

    def test_mixed_evidence_and_flags(self) -> None:
        """Response with both evidence and flag tags."""
        response = """You discover a memory. [EVIDENCE: secret_memory]
        But she felt the intrusion! [FLAG: relationship_damaged]"""

        flags = extract_flags_from_response(response)
        evidence = extract_evidence_from_response(response)

        assert flags == ["relationship_damaged"]
        assert evidence == ["secret_memory"]

    def test_underscore_in_flag_name(self) -> None:
        """Flag with underscores in name."""
        response = "[FLAG: severe_relationship_damage]"
        result = extract_flags_from_response(response)

        assert result == ["severe_relationship_damage"]
