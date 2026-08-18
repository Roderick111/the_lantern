from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from src.api.routes import InvestigateRequest, investigate


def _make_request() -> Request:
    """Create a minimal Starlette Request for rate-limiter compatibility."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/investigate",
        "headers": [],
        "query_string": b"",
    }
    return Request(scope)

TEST_CASE_ID = "test_case_init"
TEST_PLAYER_ID = "test_player_init"


@pytest.fixture
def mock_case_file(tmp_path):
    """Create a temporary case file without 'great_hall'."""
    case_data = {
        "id": TEST_CASE_ID,
        "title": "Test Case",
        "difficulty": 1,
        "victim": {"id": "victim", "name": "Victim"},
        "locations": [
            {"id": "entry_hall", "name": "Entry Hall", "description": "The entry hall."},
            {"id": "kitchen", "name": "Kitchen", "description": "The kitchen."},
        ],
        "witnesses": [],
        "evidence": [],
        "timeline": [],
        "solution": {"whodunit": "nobody", "howdunit": "nothing", "whydunit": "none"},
        "post_verdict": {"success": "Win", "failure": "Lose"},
    }
    return case_data


@pytest.mark.asyncio
async def test_initialization_flow_without_greathall(mock_case_file):
    """Test that a new game initializes with the first location when no default exists."""

    with (
        patch("src.api.helpers.load_case", return_value=mock_case_file),
        patch("src.api.helpers.list_locations", return_value=mock_case_file["locations"]),
        patch(
            "src.api.helpers.get_location",
            side_effect=lambda case, loc_id: next(
                (loc for loc in mock_case_file["locations"] if loc["id"] == loc_id), None
            ),
        ),
        patch("src.api.helpers.load_player_state", return_value=None),
        patch("src.api.routes.investigation_logic.load_slot_state", return_value=None),
        patch("src.api.helpers.save_player_state") as mock_save,
        patch(
            "src.api.routes.investigation_logic.build_narrator_or_spell_prompt",
            return_value=("Prompt", "System", None),
        ),
        patch("src.api.routes.investigation_logic.build_narrator_prompt", return_value="Prompt"),
        patch("src.api.routes.investigation_logic.build_system_prompt", return_value="System"),
        patch("src.api.routes.investigation.get_client") as mock_client,
        patch("src.api.routes.investigation_logic.list_locations", return_value=mock_case_file["locations"]),
        patch("src.api.routes.investigation.detect_spell_with_fuzzy", return_value=(None, None)),
        patch("src.api.routes.investigation_logic.check_already_discovered", return_value=False),
        patch("src.api.helpers.extract_evidence_from_response", return_value=[]),
        patch("src.api.helpers.extract_flags_from_response", return_value=([], [])),
    ):
        mock_client_instance = MagicMock()
        mock_client_instance.get_response = AsyncMock(return_value="Narrator response")
        mock_client.return_value = mock_client_instance

        req = InvestigateRequest(
            player_input="start game",
            case_id=TEST_CASE_ID,
            player_id=TEST_PLAYER_ID,
            location_id=None,
        )

        try:
            await investigate(
                request=_make_request(),
                body=req,
                llm_config=MagicMock(api_key=None, model=None),
            )
        except Exception as e:
            pytest.fail(f"Investigate failed with error: {e}")

        assert mock_save.called, "save_player_state should be called"

        # save_player_state(case_id, player_id, state, slot)
        saved_state = mock_save.call_args[0][2]
        print(f"Initialized location: {saved_state.current_location}")
        assert saved_state.current_location == "entry_hall"
        assert saved_state.current_location != "great_hall"


@pytest.mark.asyncio
async def test_initialization_flow_with_explicit_location(mock_case_file):
    """Test that explicit location request is honored."""

    with (
        patch("src.api.helpers.load_case", return_value=mock_case_file),
        patch("src.api.helpers.list_locations", return_value=mock_case_file["locations"]),
        patch(
            "src.api.helpers.get_location",
            side_effect=lambda case, loc_id: next(
                (loc for loc in mock_case_file["locations"] if loc["id"] == loc_id), None
            ),
        ),
        patch("src.api.helpers.load_player_state", return_value=None),
        patch("src.api.routes.investigation_logic.load_slot_state", return_value=None),
        patch("src.api.helpers.save_player_state") as mock_save,
        patch(
            "src.api.routes.investigation_logic.build_narrator_or_spell_prompt",
            return_value=("Prompt", "System", None),
        ),
        patch("src.api.routes.investigation_logic.build_narrator_prompt", return_value="Prompt"),
        patch("src.api.routes.investigation_logic.build_system_prompt", return_value="System"),
        patch("src.api.routes.investigation.get_client") as mock_client,
        patch("src.api.routes.investigation_logic.list_locations", return_value=mock_case_file["locations"]),
        patch("src.api.routes.investigation.detect_spell_with_fuzzy", return_value=(None, None)),
        patch("src.api.routes.investigation_logic.check_already_discovered", return_value=False),
        patch("src.api.helpers.extract_evidence_from_response", return_value=[]),
        patch("src.api.helpers.extract_flags_from_response", return_value=([], [])),
    ):
        mock_client.return_value.get_response = AsyncMock(return_value="Response")

        req = InvestigateRequest(
            player_input="go to kitchen",
            case_id=TEST_CASE_ID,
            player_id=TEST_PLAYER_ID,
            location_id="kitchen",
        )

        try:
            await investigate(
                request=_make_request(),
                body=req,
                llm_config=MagicMock(api_key=None, model=None),
            )
        except Exception as e:
            pytest.fail(f"Investigate failed with error: {e}")

        assert mock_save.called, "save_player_state should be called"
        # save_player_state(case_id, player_id, state, slot)
        saved_state = mock_save.call_args[0][2]
        assert saved_state.current_location == "kitchen"
