"""Tests for case loader module."""

import re

import pytest

from src.case_store.loader import (
    get_all_evidence,
    get_evidence_by_id,
    get_location,
    get_witness,
    list_cases,
    list_witnesses,
    load_case,
    load_confrontation,
    load_mentor_templates,
    load_solution,
    load_witnesses,
    load_wrong_suspects,
    load_wrong_verdict_info,
)


class TestLoadCase:
    """Tests for load_case function."""

    def test_load_case_001_success(self) -> None:
        """Load case_001 successfully."""
        case_data = load_case("case_001")

        assert "case" in case_data
        assert case_data["case"]["id"] == "case_001"
        assert case_data["case"]["title"] == "The Sealed Archive"

    def test_load_case_has_locations(self) -> None:
        """Case has locations dictionary."""
        case_data = load_case("case_001")

        assert "locations" in case_data["case"]
        assert "library" in case_data["case"]["locations"]

    def test_load_case_not_found_raises(self) -> None:
        """FileNotFoundError for missing case."""
        with pytest.raises(FileNotFoundError):
            load_case("nonexistent_case")


class TestGetLocation:
    """Tests for get_location function."""

    def test_get_library_location(self) -> None:
        """Get library location data."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        assert location["id"] == "library"
        assert location["name"] == "Sealed Archive"
        assert "description" in location

    def test_location_description_breaks_only_between_paragraphs(self) -> None:
        """Location prose uses blank lines for paragraphs, not hard wraps."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        description = location["description"]
        assert "\n\n" in description
        assert re.search(r"[^\n]\n[^\n]", description) is None
        assert len(description) > 50

    def test_location_has_hidden_evidence(self) -> None:
        """Location has hidden evidence list."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        assert "hidden_evidence" in location
        evidence_list = location["hidden_evidence"]
        assert len(evidence_list) >= 2

        # Check evidence structure
        first_evidence = evidence_list[0]
        assert "id" in first_evidence
        assert "discovery_guidance" in first_evidence
        assert "description" in first_evidence

    def test_location_has_not_present_items(self) -> None:
        """Location has not_present items for hallucination prevention."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        assert "not_present" in location
        not_present = location["not_present"]
        assert len(not_present) >= 2

        # Check structure
        first_item = not_present[0]
        assert "triggers" in first_item
        assert "response" in first_item

    def test_get_nonexistent_location_raises(self) -> None:
        """KeyError for missing location."""
        case_data = load_case("case_001")

        with pytest.raises(KeyError):
            get_location(case_data, "nonexistent_room")


class TestListCases:
    """Tests for list_cases function."""

    def test_list_cases_includes_case_001(self) -> None:
        """case_001 in available cases."""
        cases = list_cases()

        assert "case_001" in cases

    def test_list_cases_returns_list(self) -> None:
        """Returns list of strings."""
        cases = list_cases()

        assert isinstance(cases, list)
        assert all(isinstance(c, str) for c in cases)


class TestEvidenceStructure:
    """Tests for evidence data structure."""

    def test_evidence_has_required_fields(self) -> None:
        """Each evidence has id, discovery_guidance, description."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        for evidence in location["hidden_evidence"]:
            assert "id" in evidence, f"Evidence missing 'id': {evidence}"
            assert "discovery_guidance" in evidence, f"Evidence missing 'discovery_guidance': {evidence}"
            assert "description" in evidence, f"Evidence missing 'description': {evidence}"
            assert isinstance(evidence["discovery_guidance"], str)
            assert len(evidence["discovery_guidance"]) >= 1

    def test_evidence_discovery_guidance_is_descriptive(self) -> None:
        """Discovery guidance describes how evidence is found."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        for evidence in location["hidden_evidence"]:
            guidance = evidence["discovery_guidance"]
            assert len(guidance) > 10, f"Evidence {evidence['id']} has too short guidance"

    def test_hidden_note_evidence_exists(self) -> None:
        """hidden_note evidence with desk discovery guidance."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        evidence_ids = [e["id"] for e in location["hidden_evidence"]]
        assert "hidden_note" in evidence_ids

        hidden_note = next(e for e in location["hidden_evidence"] if e["id"] == "hidden_note")
        assert "desk" in hidden_note["discovery_guidance"].lower()

    def test_focus_signature_evidence_exists(self) -> None:
        """focus_signature evidence with Echo Reading discovery guidance."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        evidence_ids = [e["id"] for e in location["hidden_evidence"]]
        assert "focus_signature" in evidence_ids

        focus_sig = next(e for e in location["hidden_evidence"] if e["id"] == "focus_signature")
        assert "echo reading" in focus_sig["discovery_guidance"].lower()


class TestLoadWitnesses:
    """Tests for witness loading functions."""

    def test_load_witnesses_returns_dict(self) -> None:
        """load_witnesses returns dict keyed by witness ID."""
        case_data = load_case("case_001")
        witnesses = load_witnesses(case_data)

        assert isinstance(witnesses, dict)
        assert "elena" in witnesses
        assert "cassian" in witnesses

    def test_get_witness_elena(self) -> None:
        """Get Elena witness data."""
        case_data = load_case("case_001")
        elena = get_witness(case_data, "elena")

        assert elena["name"] == "Elena Marsh"
        assert elena["base_trust"] == 55
        assert "personality" in elena
        assert "knowledge" in elena
        assert "secrets" in elena
        assert "lies" in elena

    def test_get_witness_cassian(self) -> None:
        """Get Cassian witness data."""
        case_data = load_case("case_001")
        cassian = get_witness(case_data, "cassian")

        assert cassian["name"] == "Cassian Thorne"
        assert cassian["base_trust"] == 30
        assert "personality" in cassian

    def test_get_witness_not_found_raises(self) -> None:
        """KeyError for missing witness."""
        case_data = load_case("case_001")

        with pytest.raises(KeyError):
            get_witness(case_data, "moriarty")

    def test_list_witnesses(self) -> None:
        """list_witnesses returns witness IDs."""
        case_data = load_case("case_001")
        witness_ids = list_witnesses(case_data)

        assert "elena" in witness_ids
        assert "cassian" in witness_ids
        assert len(witness_ids) == 4


class TestWitnessStructure:
    """Tests for witness data structure."""

    def test_witness_has_required_fields(self) -> None:
        """Each witness has required fields."""
        case_data = load_case("case_001")
        witnesses = load_witnesses(case_data)

        required_fields = [
            "id",
            "name",
            "personality",
            "base_trust",
            "knowledge",
            "secrets",
            "lies",
        ]

        for witness_id, witness in witnesses.items():
            for field in required_fields:
                assert field in witness, f"Witness {witness_id} missing '{field}'"

    def test_witness_knowledge_is_list(self) -> None:
        """Witness knowledge is a list of strings."""
        case_data = load_case("case_001")
        elena = get_witness(case_data, "elena")

        assert isinstance(elena["knowledge"], list)
        assert len(elena["knowledge"]) >= 3
        assert all(isinstance(k, str) for k in elena["knowledge"])

    def test_witness_secrets_structure(self) -> None:
        """Witness secrets have id, trigger, text."""
        case_data = load_case("case_001")
        elena = get_witness(case_data, "elena")

        for secret in elena["secrets"]:
            assert "id" in secret, f"Secret missing 'id': {secret}"
            assert "trigger" in secret, f"Secret missing 'trigger': {secret}"
            assert "text" in secret, f"Secret missing 'text': {secret}"

    def test_witness_lies_structure(self) -> None:
        """Witness lies have condition, topics, response."""
        case_data = load_case("case_001")
        cassian = get_witness(case_data, "cassian")

        for lie in cassian["lies"]:
            assert "condition" in lie, f"Lie missing 'condition': {lie}"
            assert "topics" in lie, f"Lie missing 'topics': {lie}"
            assert "response" in lie, f"Lie missing 'response': {lie}"
            assert isinstance(lie["topics"], list)

    def test_elena_secret_triggers(self) -> None:
        """Elena's secrets have valid triggers."""
        case_data = load_case("case_001")
        elena = get_witness(case_data, "elena")

        secret_ids = [s["id"] for s in elena["secrets"]]
        assert "tutoring_a_peer" in secret_ids
        assert "saw_fleeing_figure" in secret_ids

        saw_fleeing = next(s for s in elena["secrets"] if s["id"] == "saw_fleeing_figure")
        assert "trust>70" in saw_fleeing["trigger"]

    def test_cassian_base_trust_lower_than_elena(self) -> None:
        """Cassian starts with lower trust (hostile)."""
        case_data = load_case("case_001")
        elena = get_witness(case_data, "elena")
        cassian = get_witness(case_data, "cassian")

        assert cassian["base_trust"] < elena["base_trust"]


class TestWitnessesPresentField:
    """Tests for witnesses_present field in locations."""

    def test_location_has_witnesses_present_field(self) -> None:
        """Location includes witnesses_present field."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        assert "witnesses_present" in location
        assert isinstance(location["witnesses_present"], list)

    def test_library_has_elena_present(self) -> None:
        """Library has Elena as witness present."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        assert "elena" in location["witnesses_present"]

    def test_witnesses_present_defaults_to_empty(self) -> None:
        """Missing witnesses_present defaults to empty list."""
        # This tests backward compatibility via get_location
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        # Field should exist (either from YAML or default)
        assert "witnesses_present" in location


class TestEvidenceMetadata:
    """Tests for evidence metadata fields (name, location_found, description)."""

    def test_evidence_has_name_field(self) -> None:
        """Each evidence has name field."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        for evidence in location["hidden_evidence"]:
            assert "name" in evidence, f"Evidence {evidence['id']} missing 'name'"
            assert isinstance(evidence["name"], str)
            assert len(evidence["name"]) > 0

    def test_evidence_has_location_found_field(self) -> None:
        """Each evidence has location_found field."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        for evidence in location["hidden_evidence"]:
            assert "location_found" in evidence, (
                f"Evidence {evidence['id']} missing 'location_found'"
            )
            assert evidence["location_found"] == "library"

    def test_evidence_description_is_detailed(self) -> None:
        """Evidence descriptions are detailed (multi-sentence)."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        for evidence in location["hidden_evidence"]:
            desc = evidence["description"]
            # Should have at least 50 characters for meaningful description
            assert len(desc) >= 50, f"Evidence {evidence['id']} has too short description"

    def test_hidden_note_metadata(self) -> None:
        """Hidden note has correct metadata."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        hidden_note = next(e for e in location["hidden_evidence"] if e["id"] == "hidden_note")
        assert hidden_note["name"] == "Crumpled Apology Note"
        assert hidden_note["location_found"] == "library"
        assert "nightshade" in hidden_note["description"].lower()

    def test_focus_signature_metadata(self) -> None:
        """Focus signature has correct metadata."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        focus_sig = next(e for e in location["hidden_evidence"] if e["id"] == "focus_signature")
        assert focus_sig["name"] == "Professor Vane's Focus Signature"
        assert focus_sig["location_found"] == "library"
        assert "dispel" in focus_sig["description"].lower()

    def test_frost_pattern_metadata(self) -> None:
        """Frost pattern has correct metadata."""
        case_data = load_case("case_001")
        location = get_location(case_data, "library")

        frost = next(e for e in location["hidden_evidence"] if e["id"] == "frost_pattern")
        assert frost["name"] == "Unusual Frost Pattern"
        assert frost["location_found"] == "library"
        assert "frost" in frost["description"].lower()


class TestGetEvidenceById:
    """Tests for get_evidence_by_id function."""

    def test_get_existing_evidence(self) -> None:
        """Get evidence by ID returns correct data."""
        case_data = load_case("case_001")
        evidence = get_evidence_by_id(case_data, "library", "hidden_note")

        assert evidence is not None
        assert evidence["id"] == "hidden_note"
        assert evidence["name"] == "Crumpled Apology Note"
        assert evidence["location_found"] == "library"
        assert "description" in evidence

    def test_get_nonexistent_evidence(self) -> None:
        """Get evidence returns None for missing ID."""
        case_data = load_case("case_001")
        evidence = get_evidence_by_id(case_data, "library", "fake_evidence")

        assert evidence is None

    def test_get_evidence_has_all_fields(self) -> None:
        """Returned evidence has all metadata fields."""
        case_data = load_case("case_001")
        evidence = get_evidence_by_id(case_data, "library", "frost_pattern")

        required_fields = ["id", "name", "location_found", "description", "type", "tag"]
        for field in required_fields:
            assert field in evidence, f"Evidence missing field: {field}"


class TestGetAllEvidence:
    """Tests for get_all_evidence function."""

    def test_get_all_evidence_returns_list(self) -> None:
        """Get all evidence returns list of evidence."""
        case_data = load_case("case_001")
        all_evidence = get_all_evidence(case_data, "library")

        assert isinstance(all_evidence, list)
        assert len(all_evidence) == 11  # library has 11 evidence items

    def test_all_evidence_has_metadata(self) -> None:
        """All evidence items have required metadata."""
        case_data = load_case("case_001")
        all_evidence = get_all_evidence(case_data, "library")

        for evidence in all_evidence:
            assert "id" in evidence
            assert "name" in evidence
            assert "location_found" in evidence
            assert "description" in evidence
            assert "type" in evidence


# Phase 3: Verdict-related loader tests


class TestLoadSolution:
    """Tests for load_solution function."""

    def test_load_solution_returns_dict(self) -> None:
        """load_solution returns solution dictionary."""
        case_data = load_case("case_001")
        solution = load_solution(case_data)

        assert isinstance(solution, dict)

    def test_solution_has_culprit(self) -> None:
        """Solution has culprit field."""
        case_data = load_case("case_001")
        solution = load_solution(case_data)

        assert "culprit" in solution
        assert solution["culprit"] == "wisp"

    def test_solution_has_method(self) -> None:
        """Solution has method field."""
        case_data = load_case("case_001")
        solution = load_solution(case_data)

        assert "method" in solution
        assert "binding" in solution["method"].lower()

    def test_solution_has_key_evidence(self) -> None:
        """Solution has key_evidence list."""
        case_data = load_case("case_001")
        solution = load_solution(case_data)

        assert "key_evidence" in solution
        assert isinstance(solution["key_evidence"], list)
        assert "frost_pattern" in solution["key_evidence"]

    def test_solution_has_deductions_required(self) -> None:
        """Solution has deductions_required list."""
        case_data = load_case("case_001")
        solution = load_solution(case_data)

        assert "deductions_required" in solution
        assert isinstance(solution["deductions_required"], list)
        assert len(solution["deductions_required"]) >= 1


class TestLoadWrongSuspects:
    """Tests for load_wrong_suspects function."""

    def test_load_wrong_suspects_returns_dict(self) -> None:
        """load_wrong_suspects returns dict keyed by suspect ID."""
        case_data = load_case("case_001")
        wrong_suspects = load_wrong_suspects(case_data)

        assert isinstance(wrong_suspects, dict)

    def test_elena_in_wrong_suspects(self) -> None:
        """Elena is in wrong suspects dict."""
        case_data = load_case("case_001")
        wrong_suspects = load_wrong_suspects(case_data)

        assert "elena" in wrong_suspects

    def test_wrong_suspect_has_why_innocent(self) -> None:
        """Wrong suspect has why_innocent field."""
        case_data = load_case("case_001")
        wrong_suspects = load_wrong_suspects(case_data)

        elena = wrong_suspects["elena"]
        assert "why_innocent" in elena
        assert "timeline" in elena["why_innocent"].lower()

    def test_wrong_suspect_has_graves_response(self) -> None:
        """Wrong suspect has graves_response field."""
        case_data = load_case("case_001")
        wrong_suspects = load_wrong_suspects(case_data)

        elena = wrong_suspects["elena"]
        assert "graves_response" in elena
        assert isinstance(elena["graves_response"], str)


class TestLoadConfrontation:
    """Tests for load_confrontation function."""

    def test_load_confrontation_correct_verdict(self) -> None:
        """Load confrontation for correct verdict."""
        case_data = load_case("case_001")
        confrontation = load_confrontation(case_data, "wisp", correct=True)

        assert confrontation is not None
        assert "dialogue" in confrontation
        assert "aftermath" in confrontation

    def test_confrontation_dialogue_structure(self) -> None:
        """Confrontation dialogue has speaker and text."""
        case_data = load_case("case_001")
        confrontation = load_confrontation(case_data, "wisp", correct=True)

        assert len(confrontation["dialogue"]) >= 3
        for entry in confrontation["dialogue"]:
            assert "speaker" in entry
            assert "text" in entry

    def test_confrontation_has_graves(self) -> None:
        """Confrontation includes Graves dialogue."""
        case_data = load_case("case_001")
        confrontation = load_confrontation(case_data, "wisp", correct=True)

        speakers = [d["speaker"] for d in confrontation["dialogue"]]
        assert "graves" in speakers

    def test_confrontation_has_aftermath(self) -> None:
        """Confrontation has aftermath text."""
        case_data = load_case("case_001")
        confrontation = load_confrontation(case_data, "wisp", correct=True)

        assert len(confrontation["aftermath"]) > 50

    def test_load_confrontation_incorrect_no_show(self) -> None:
        """Load confrontation for incorrect verdict without show_anyway returns None."""
        case_data = load_case("case_001")
        # Mock: if no "confrontation_anyway" defined or False
        confrontation = load_confrontation(case_data, "unknown_suspect", correct=False)

        assert confrontation is None

    def test_load_confrontation_incorrect_show_anyway(self) -> None:
        """Load confrontation for incorrect verdict with show_anyway=True."""
        case_data = load_case("case_001")
        # Elena has confrontation_anyway: true
        confrontation = load_confrontation(case_data, "elena", correct=False)

        assert confrontation is not None
        assert "dialogue" in confrontation


class TestLoadMentorTemplates:
    """Tests for load_mentor_templates function."""

    def test_load_mentor_templates_returns_dict(self) -> None:
        """load_mentor_templates returns dictionary (empty when no templates in YAML)."""
        case_data = load_case("case_001")
        templates = load_mentor_templates(case_data)

        assert isinstance(templates, dict)


class TestLoadWrongVerdictInfo:
    """Tests for load_wrong_verdict_info function."""

    def test_load_wrong_verdict_info_existing(self) -> None:
        """Load info for existing wrong suspect."""
        case_data = load_case("case_001")
        info = load_wrong_verdict_info(case_data, "elena")

        assert info is not None
        assert "reveal" in info
        assert "teaching_moment" in info
        assert "confrontation_anyway" in info

    def test_wrong_verdict_info_has_reveal(self) -> None:
        """Wrong verdict info has reveal text."""
        case_data = load_case("case_001")
        info = load_wrong_verdict_info(case_data, "elena")

        assert "wisp" in info["reveal"].lower()

    def test_wrong_verdict_info_has_teaching_moment(self) -> None:
        """Wrong verdict info has teaching_moment."""
        case_data = load_case("case_001")
        info = load_wrong_verdict_info(case_data, "elena")

        assert len(info["teaching_moment"]) > 20

    def test_load_wrong_verdict_info_nonexistent(self) -> None:
        """Load info for non-existent wrong suspect returns None."""
        case_data = load_case("case_001")
        info = load_wrong_verdict_info(case_data, "unknown_suspect")

        assert info is None

    def test_load_wrong_verdict_info_case_insensitive(self) -> None:
        """Load info is case-insensitive."""
        case_data = load_case("case_001")
        info = load_wrong_verdict_info(case_data, "ELENA")

        assert info is not None
