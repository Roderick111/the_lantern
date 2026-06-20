"""Tests for Phase 5.4 case discovery system.

Tests:
- Case validation (validate_case)
- Case discovery (discover_cases, list_cases_with_metadata)
- GET /api/cases endpoint
- Error handling for malformed/invalid YAML
"""

from pathlib import Path

import pytest
import yaml

from src.case_store.loader import (
    discover_cases,
    list_cases_with_metadata,
    validate_case,
)
from src.state.player_state import CaseMetadata

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def valid_case_dict() -> dict:
    """Minimal valid case structure."""
    return {
        "case": {
            "id": "test_case",
            "title": "Test Case Title",
            "difficulty": "beginner",
            "description": "A test case description.",
            "locations": {
                "test_location": {
                    "id": "test_location",
                    "name": "Test Location",
                    "description": "A test location.",
                    "hidden_evidence": [
                        {
                            "id": "test_evidence",
                            "name": "Test Evidence",
                            "location_found": "test_location",
                            "type": "physical",
                            "triggers": ["examine test"],
                            "description": "Test evidence description.",
                            "tag": "[EVIDENCE: test_evidence]",
                        }
                    ],
                }
            },
            "witnesses": [
                {
                    "id": "test_witness",
                    "name": "Test Witness",
                    "personality": "Test personality.",
                    "base_trust": 50,
                    "knowledge": ["knows something"],
                    "secrets": [],
                    "lies": [],
                }
            ],
            "solution": {
                "culprit": "test_witness",
                "method": "Test method.",
                "motive": "Test motive.",
                "key_evidence": ["test_evidence"],
            },
            "briefing": {
                "case_assignment": "Test case assignment.",
                "teaching_question": {
                    "prompt": "Test question?",
                    "choices": [{"id": "a", "text": "Option A", "response": "Response A."}],
                    "concept_summary": "Test summary.",
                },
                "rationality_concept": "test_concept",
                "concept_description": "Test description.",
            },
        }
    }


@pytest.fixture
def temp_case_dir(tmp_path: Path) -> Path:
    """Create temporary directory for test cases."""
    return tmp_path


# ============================================================================
# Test CaseMetadata Model
# ============================================================================


class TestCaseMetadataModel:
    """Tests for CaseMetadata Pydantic model."""

    def test_create_valid_metadata(self) -> None:
        """Create CaseMetadata with valid data."""
        metadata = CaseMetadata(
            id="case_001",
            title="Test Case",
            difficulty="beginner",
            description="Test description.",
        )
        assert metadata.id == "case_001"
        assert metadata.title == "Test Case"
        assert metadata.difficulty == "beginner"
        assert metadata.description == "Test description."

    def test_metadata_description_optional(self) -> None:
        """Description field is optional (defaults to empty)."""
        metadata = CaseMetadata(
            id="case_001",
            title="Test Case",
            difficulty="beginner",
        )
        assert metadata.description == ""

    def test_metadata_id_pattern_valid(self) -> None:
        """ID pattern allows lowercase alphanumeric and underscores."""
        metadata = CaseMetadata(
            id="case_dragon_egg_001",
            title="Test",
            difficulty="beginner",
        )
        assert metadata.id == "case_dragon_egg_001"

    def test_metadata_id_pattern_invalid_uppercase(self) -> None:
        """ID pattern rejects uppercase letters."""
        with pytest.raises(ValueError):
            CaseMetadata(
                id="Case_001",
                title="Test",
                difficulty="beginner",
            )

    def test_metadata_id_pattern_invalid_hyphen(self) -> None:
        """ID pattern rejects hyphens."""
        with pytest.raises(ValueError):
            CaseMetadata(
                id="case-001",
                title="Test",
                difficulty="beginner",
            )

    def test_metadata_difficulty_valid_values(self) -> None:
        """Difficulty accepts beginner/intermediate/advanced."""
        for difficulty in ["beginner", "intermediate", "advanced"]:
            metadata = CaseMetadata(
                id="test",
                title="Test",
                difficulty=difficulty,
            )
            assert metadata.difficulty == difficulty

    def test_metadata_difficulty_invalid_value(self) -> None:
        """Difficulty rejects invalid values."""
        with pytest.raises(ValueError):
            CaseMetadata(
                id="test",
                title="Test",
                difficulty="expert",  # Invalid
            )


# ============================================================================
# Test validate_case Function
# ============================================================================


class TestValidateCase:
    """Tests for validate_case function."""

    def test_validate_valid_case(self, valid_case_dict: dict) -> None:
        """Valid case passes validation."""
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is True
        assert errors == []

    def test_validate_missing_case_id(self, valid_case_dict: dict) -> None:
        """Missing case.id fails validation."""
        del valid_case_dict["case"]["id"]
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("case.id" in e for e in errors)

    def test_validate_mismatched_case_id(self, valid_case_dict: dict) -> None:
        """case.id not matching filename fails validation."""
        valid_case_dict["case"]["id"] = "wrong_id"
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("does not match filename" in e for e in errors)

    def test_validate_missing_title(self, valid_case_dict: dict) -> None:
        """Missing case.title fails validation."""
        del valid_case_dict["case"]["title"]
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("case.title" in e for e in errors)

    def test_validate_missing_difficulty(self, valid_case_dict: dict) -> None:
        """Missing case.difficulty fails validation."""
        del valid_case_dict["case"]["difficulty"]
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("case.difficulty" in e for e in errors)

    def test_validate_invalid_difficulty(self, valid_case_dict: dict) -> None:
        """Invalid case.difficulty value fails validation."""
        valid_case_dict["case"]["difficulty"] = "expert"
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("Invalid case.difficulty" in e for e in errors)

    def test_validate_no_locations(self, valid_case_dict: dict) -> None:
        """Empty locations fails validation."""
        valid_case_dict["case"]["locations"] = {}
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("at least 1 location" in e for e in errors)

    def test_validate_no_witnesses(self, valid_case_dict: dict) -> None:
        """Empty witnesses fails validation."""
        valid_case_dict["case"]["witnesses"] = []
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("at least 1 witness" in e for e in errors)

    def test_validate_no_evidence(self, valid_case_dict: dict) -> None:
        """No evidence items fails validation."""
        valid_case_dict["case"]["locations"]["test_location"]["hidden_evidence"] = []
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("at least 1 evidence item" in e for e in errors)

    def test_validate_missing_solution_culprit(self, valid_case_dict: dict) -> None:
        """Missing solution.culprit fails validation."""
        del valid_case_dict["case"]["solution"]["culprit"]
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("solution.culprit" in e for e in errors)

    def test_validate_culprit_not_witness(self, valid_case_dict: dict) -> None:
        """solution.culprit not matching witness ID fails validation."""
        valid_case_dict["case"]["solution"]["culprit"] = "unknown_person"
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("does not match any witness ID" in e for e in errors)

    def test_validate_missing_briefing_case_assignment(self, valid_case_dict: dict) -> None:
        """Missing briefing.dossier (or legacy case_assignment) fails validation."""
        if "dossier" in valid_case_dict["case"]["briefing"]:
            del valid_case_dict["case"]["briefing"]["dossier"]
        if "case_assignment" in valid_case_dict["case"]["briefing"]:
            del valid_case_dict["case"]["briefing"]["case_assignment"]
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("dossier" in e or "case_assignment" in e for e in errors)

    def test_validate_missing_briefing_teaching_question(self, valid_case_dict: dict) -> None:
        """Missing briefing.teaching_questions (or legacy teaching_question) fails validation."""
        if "teaching_questions" in valid_case_dict["case"]["briefing"]:
            del valid_case_dict["case"]["briefing"]["teaching_questions"]
        if "teaching_question" in valid_case_dict["case"]["briefing"]:
            del valid_case_dict["case"]["briefing"]["teaching_question"]
        is_valid, errors, warnings = validate_case(valid_case_dict, "test_case")
        assert is_valid is False
        assert any("teaching_question" in e for e in errors)

    def test_validate_accumulates_multiple_errors(self) -> None:
        """Validation accumulates all errors, doesn't stop at first."""
        bad_case = {
            "case": {
                # Missing: id, title, difficulty
                "locations": {},
                "witnesses": [],
                "solution": {},
                "briefing": {},
            }
        }
        is_valid, errors, warnings = validate_case(bad_case, "test_case")
        assert is_valid is False
        # Should have multiple errors
        assert len(errors) >= 5


# ============================================================================
# Test discover_cases Function
# ============================================================================


class TestDiscoverCases:
    """Tests for discover_cases function."""

    def test_discover_empty_directory(self, temp_case_dir: Path) -> None:
        """Empty directory returns empty list."""
        cases, errors = discover_cases(temp_case_dir)
        assert cases == []
        assert errors == []

    def test_discover_valid_case(self, temp_case_dir: Path, valid_case_dict: dict) -> None:
        """Single valid case is discovered."""
        # Write valid case file
        case_file = temp_case_dir / "case_test.yaml"
        with open(case_file, "w") as f:
            yaml.dump(valid_case_dict, f)

        # Update case_id to match filename
        valid_case_dict["case"]["id"] = "case_test"
        with open(case_file, "w") as f:
            yaml.dump(valid_case_dict, f)

        cases, errors = discover_cases(temp_case_dir)
        assert len(cases) == 1
        assert cases[0].id == "case_test"
        assert cases[0].title == "Test Case Title"
        assert errors == []

    def test_discover_multiple_cases(self, temp_case_dir: Path, valid_case_dict: dict) -> None:
        """Multiple valid cases are discovered and sorted."""
        # Create case_001
        valid_case_dict["case"]["id"] = "case_001"
        with open(temp_case_dir / "case_001.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        # Create case_002
        valid_case_dict["case"]["id"] = "case_002"
        valid_case_dict["case"]["title"] = "Second Case"
        with open(temp_case_dir / "case_002.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        cases, errors = discover_cases(temp_case_dir)
        assert len(cases) == 2
        # Should be sorted by filename
        assert cases[0].id == "case_001"
        assert cases[1].id == "case_002"
        assert errors == []

    def test_discover_skips_invalid_case(self, temp_case_dir: Path, valid_case_dict: dict) -> None:
        """Invalid case is skipped with error, valid case still loads."""
        # Create valid case
        valid_case_dict["case"]["id"] = "case_001"
        with open(temp_case_dir / "case_001.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        # Create invalid case (missing title)
        invalid_case = {"case": {"id": "case_002"}}
        with open(temp_case_dir / "case_002.yaml", "w") as f:
            yaml.dump(invalid_case, f)

        cases, errors = discover_cases(temp_case_dir)
        assert len(cases) == 1
        assert cases[0].id == "case_001"
        assert len(errors) == 1
        assert "case_002" in errors[0]

    def test_discover_skips_malformed_yaml(
        self, temp_case_dir: Path, valid_case_dict: dict
    ) -> None:
        """Malformed YAML is skipped with error."""
        # Create valid case
        valid_case_dict["case"]["id"] = "case_001"
        with open(temp_case_dir / "case_001.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        # Create malformed YAML
        with open(temp_case_dir / "case_002.yaml", "w") as f:
            f.write("invalid: yaml: content: [")

        cases, errors = discover_cases(temp_case_dir)
        assert len(cases) == 1
        assert cases[0].id == "case_001"
        assert len(errors) == 1
        assert "case_002" in errors[0]
        assert "YAML parse error" in errors[0]

    def test_discover_skips_empty_yaml(self, temp_case_dir: Path, valid_case_dict: dict) -> None:
        """Empty YAML file is skipped with error."""
        # Create valid case
        valid_case_dict["case"]["id"] = "case_001"
        with open(temp_case_dir / "case_001.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        # Create empty file
        with open(temp_case_dir / "case_002.yaml", "w") as f:
            f.write("")

        cases, errors = discover_cases(temp_case_dir)
        assert len(cases) == 1
        assert len(errors) == 1
        assert "Empty YAML file" in errors[0]

    def test_discover_skips_template_file(self, temp_case_dir: Path, valid_case_dict: dict) -> None:
        """case_template.yaml is skipped."""
        # Create valid case
        valid_case_dict["case"]["id"] = "case_001"
        with open(temp_case_dir / "case_001.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        # Create template file (should be skipped)
        with open(temp_case_dir / "case_template.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        cases, errors = discover_cases(temp_case_dir)
        assert len(cases) == 1
        assert cases[0].id == "case_001"

    def test_discover_skips_hidden_files(self, temp_case_dir: Path, valid_case_dict: dict) -> None:
        """Hidden files (starting with .) are skipped."""
        # Create valid case
        valid_case_dict["case"]["id"] = "case_001"
        with open(temp_case_dir / "case_001.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        # Create hidden file (should be skipped)
        with open(temp_case_dir / ".case_hidden.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        cases, errors = discover_cases(temp_case_dir)
        assert len(cases) == 1
        assert cases[0].id == "case_001"

    def test_discover_nonexistent_directory(self) -> None:
        """Nonexistent directory returns empty lists."""
        cases, errors = discover_cases("/nonexistent/directory")
        assert cases == []
        assert errors == []

    def test_discover_extracts_description(
        self, temp_case_dir: Path, valid_case_dict: dict
    ) -> None:
        """Description is extracted from case metadata."""
        valid_case_dict["case"]["id"] = "case_001"
        valid_case_dict["case"]["description"] = "A thrilling mystery!"
        with open(temp_case_dir / "case_001.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        cases, errors = discover_cases(temp_case_dir)
        assert len(cases) == 1
        assert cases[0].description == "A thrilling mystery!"


# ============================================================================
# Test list_cases_with_metadata Function
# ============================================================================


class TestListCasesWithMetadata:
    """Tests for list_cases_with_metadata convenience function."""

    def test_list_cases_discovers_case_001(self) -> None:
        """list_cases_with_metadata discovers case_001.yaml from actual case_store."""
        cases, errors = list_cases_with_metadata()

        # Should discover at least case_001
        case_ids = [c.id for c in cases]
        assert "case_001" in case_ids

        # case_001 should have correct metadata
        case_001 = next(c for c in cases if c.id == "case_001")
        assert case_001.title == "The Sealed Stacks"
        assert case_001.difficulty == "beginner"
        assert "held in stillness" in case_001.description.lower()


# ============================================================================
# Test GET /api/cases Endpoint
# ============================================================================


class TestGetCasesEndpoint:
    """Tests for GET /api/cases endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from src.api.routes import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_get_cases_returns_list(self, client) -> None:
        """GET /api/cases returns list of cases."""
        response = client.get("/api/cases")
        assert response.status_code == 200

        data = response.json()
        assert "cases" in data
        assert "count" in data
        assert isinstance(data["cases"], list)
        assert isinstance(data["count"], int)

    def test_get_cases_includes_case_001(self, client) -> None:
        """GET /api/cases includes case_001 with metadata."""
        response = client.get("/api/cases")
        assert response.status_code == 200

        data = response.json()
        case_ids = [c["id"] for c in data["cases"]]
        assert "case_001" in case_ids

        case_001 = next(c for c in data["cases"] if c["id"] == "case_001")
        assert case_001["title"] == "The Sealed Stacks"
        assert case_001["difficulty"] == "beginner"
        assert "description" in case_001

    def test_get_cases_count_matches_list_length(self, client) -> None:
        """GET /api/cases count matches cases list length."""
        response = client.get("/api/cases")
        data = response.json()

        assert data["count"] == len(data["cases"])

    def test_get_cases_errors_null_when_no_errors(self, client) -> None:
        """GET /api/cases errors field is null when no validation errors."""
        response = client.get("/api/cases")
        data = response.json()

        # If all cases valid, errors should be null
        # (or list of errors if some cases invalid)
        assert data.get("errors") is None or isinstance(data["errors"], list)


# ============================================================================
# Test Integration: End-to-End Case Discovery
# ============================================================================


class TestCaseDiscoveryIntegration:
    """Integration tests for complete case discovery workflow."""

    def test_new_case_auto_discovered(self, temp_case_dir: Path, valid_case_dict: dict) -> None:
        """New valid case file is automatically discovered."""
        # Initially no cases
        cases, _ = discover_cases(temp_case_dir)
        assert len(cases) == 0

        # Create new case
        valid_case_dict["case"]["id"] = "case_new"
        with open(temp_case_dir / "case_new.yaml", "w") as f:
            yaml.dump(valid_case_dict, f)

        # Re-discover - should find new case
        cases, _ = discover_cases(temp_case_dir)
        assert len(cases) == 1
        assert cases[0].id == "case_new"

    def test_partial_success_three_of_four(
        self, temp_case_dir: Path, valid_case_dict: dict
    ) -> None:
        """3/4 valid cases returns 3 cases, 1 error."""
        # Create 3 valid cases
        for i in range(1, 4):
            valid_case_dict["case"]["id"] = f"case_00{i}"
            valid_case_dict["case"]["title"] = f"Case {i}"
            with open(temp_case_dir / f"case_00{i}.yaml", "w") as f:
                yaml.dump(valid_case_dict, f)

        # Create 1 invalid case
        with open(temp_case_dir / "case_004.yaml", "w") as f:
            yaml.dump({"case": {"id": "case_004"}}, f)

        cases, errors = discover_cases(temp_case_dir)
        assert len(cases) == 3
        assert len(errors) == 1
        assert "case_004" in errors[0]
