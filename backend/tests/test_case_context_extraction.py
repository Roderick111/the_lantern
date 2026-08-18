"""Test case context extraction for witness prompts.

Verifies that witness context (victim, crime type, location) is correctly
extracted from both case_001 and case_002 YAML files.
"""

from pathlib import Path

import yaml


def load_case(case_id: str) -> dict:
    """Load case YAML file."""
    case_path = Path(__file__).parent.parent / "src" / "case_store" / f"{case_id}.yaml"
    with open(case_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["case"]


def extract_case_context(case_data: dict) -> dict:
    """Extract case context (same logic as routes.py)."""
    victim_info = case_data.get("victim", {})

    # Get simplified crime type from cause_of_death
    cause_of_death = victim_info.get("cause_of_death", "")
    crime_type = cause_of_death.split()[0] if cause_of_death else "Victim found"

    # Get first location as crime scene (where investigation starts)
    locations = case_data.get("locations", {})
    crime_scene_loc = next(iter(locations.values()), {}) if locations else {}

    return {
        "victim_name": victim_info.get("name", ""),
        "crime_type": crime_type,
        "location": crime_scene_loc.get("name", "Unknown location"),
    }


class TestCaseContextExtraction:
    """Test case context extraction for all cases."""

    def test_case_001_context_extraction(self):
        """Verify case_001 context is correctly extracted."""
        case_data = load_case("case_001")
        context = extract_case_context(case_data)

        assert context["victim_name"] == "Professor Aldric Vane"
        assert context["crime_type"] == "Layered"
        # Case 001 uses a plain-language crime-scene name.
        assert context["location"] == "Sealed Archive"

    def test_case_002_context_extraction(self):
        """Verify case_002 context is correctly extracted."""
        case_data = load_case("case_002")
        context = extract_case_context(case_data)

        assert context["victim_name"] == "Helena Blackwood"
        assert context["crime_type"] == "Crushed"
        assert "Library" in context["location"]

    def test_context_has_required_fields(self):
        """Both cases provide all required context fields."""
        for case_id in ["case_001", "case_002"]:
            case_data = load_case(case_id)
            context = extract_case_context(case_data)

            # All fields must be present and non-empty
            assert context["victim_name"], f"{case_id}: Missing victim_name"
            assert context["crime_type"], f"{case_id}: Missing crime_type"
            assert context["location"], f"{case_id}: Missing location"

            # No "Unknown" fallbacks should be needed
            assert context["location"] != "Unknown location", (
                f"{case_id}: Location fallback triggered"
            )

    def test_context_formatting(self):
        """Context should be witness-friendly (not technical)."""
        for case_id in ["case_001", "case_002"]:
            case_data = load_case(case_id)
            context = extract_case_context(case_data)

            # Crime type should be simple (first word)
            assert len(context["crime_type"].split()) == 1, f"{case_id}: Crime type too verbose"

            # Victim name should be person's name (not ID)
            assert context["victim_name"], f"{case_id}: Victim name empty"
            assert not context["victim_name"].startswith("case_"), (
                f"{case_id}: Victim name is case ID"
            )
