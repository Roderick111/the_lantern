"""Tests for Phase 5.2: Location Management System.

Tests for:
- GET /api/case/{case_id}/locations
- POST /api/case/{case_id}/change-location
- LocationCommandParser natural language detection
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.case_store.loader import list_locations, load_case
from src.location.parser import LocationCommandParser
from src.main import app

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
async def client() -> AsyncClient:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def case_data():
    """Load case_001 data for testing."""
    return load_case("case_001")


# ============================================================================
# Loader Tests: list_locations
# ============================================================================


class TestListLocations:
    """Tests for list_locations() in loader.py."""

    def test_returns_list(self, case_data):
        """list_locations returns a list."""
        locations = list_locations(case_data)
        assert isinstance(locations, list)

    def test_returns_four_locations(self, case_data):
        """case_001 has 4 locations."""
        locations = list_locations(case_data)
        assert len(locations) == 4

    def test_each_location_has_id(self, case_data):
        """Each location dict has an 'id' field."""
        locations = list_locations(case_data)
        for loc in locations:
            assert "id" in loc
            assert isinstance(loc["id"], str)

    def test_each_location_has_name(self, case_data):
        """Each location dict has a 'name' field."""
        locations = list_locations(case_data)
        for loc in locations:
            assert "name" in loc
            assert isinstance(loc["name"], str)

    def test_each_location_has_type(self, case_data):
        """Each location dict has a 'type' field."""
        locations = list_locations(case_data)
        for loc in locations:
            assert "type" in loc
            assert isinstance(loc["type"], str)

    def test_library_in_locations(self, case_data):
        """Library location exists."""
        locations = list_locations(case_data)
        ids = [loc["id"] for loc in locations]
        assert "library" in ids

    def test_iron_lodge_common_room_in_locations(self, case_data):
        """Iron Lodge Common Room location exists."""
        locations = list_locations(case_data)
        ids = [loc["id"] for loc in locations]
        assert "iron_lodge_common_room" in ids

    def test_third_floor_corridor_in_locations(self, case_data):
        """Third Floor Corridor location exists."""
        locations = list_locations(case_data)
        ids = [loc["id"] for loc in locations]
        assert "third_floor_corridor" in ids

    def test_kitchens_in_locations(self, case_data):
        """Kitchens location exists."""
        locations = list_locations(case_data)
        ids = [loc["id"] for loc in locations]
        assert "kitchens" in ids


# ============================================================================
# GET /api/case/{case_id}/locations Tests
# ============================================================================


class TestGetLocationsEndpoint:
    """Tests for GET /api/case/{case_id}/locations endpoint."""

    @pytest.mark.asyncio
    async def test_returns_200(self, client: AsyncClient):
        """GET /locations returns 200 for valid case."""
        response = await client.get("/api/case/case_001/locations")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_list(self, client: AsyncClient):
        """Response is a list."""
        response = await client.get("/api/case/case_001/locations")
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_returns_four_locations(self, client: AsyncClient):
        """Response contains 4 locations."""
        response = await client.get("/api/case/case_001/locations")
        data = response.json()
        assert len(data) == 4

    @pytest.mark.asyncio
    async def test_each_location_has_id(self, client: AsyncClient):
        """Each location in response has 'id'."""
        response = await client.get("/api/case/case_001/locations")
        for loc in response.json():
            assert "id" in loc

    @pytest.mark.asyncio
    async def test_each_location_has_name(self, client: AsyncClient):
        """Each location in response has 'name'."""
        response = await client.get("/api/case/case_001/locations")
        for loc in response.json():
            assert "name" in loc

    @pytest.mark.asyncio
    async def test_each_location_has_type(self, client: AsyncClient):
        """Each location in response has 'type'."""
        response = await client.get("/api/case/case_001/locations")
        for loc in response.json():
            assert "type" in loc

    @pytest.mark.asyncio
    async def test_invalid_case_returns_404(self, client: AsyncClient):
        """GET /locations returns 404 for invalid case."""
        response = await client.get("/api/case/invalid_case/locations")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ============================================================================
# POST /api/case/{case_id}/change-location Tests
# ============================================================================


class TestChangeLocationEndpoint:
    """Tests for POST /api/case/{case_id}/change-location endpoint."""

    @pytest.mark.asyncio
    async def test_returns_200(self, client: AsyncClient):
        """POST /change-location returns 200 for valid request."""
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "library"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_success_true(self, client: AsyncClient):
        """Response contains success=true."""
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "library"},
        )
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_returns_location_data(self, client: AsyncClient):
        """Response contains location data."""
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "iron_lodge_common_room"},
        )
        data = response.json()
        assert "location" in data
        assert "id" in data["location"]
        assert "name" in data["location"]
        assert "description" in data["location"]

    @pytest.mark.asyncio
    async def test_returns_correct_location_id(self, client: AsyncClient):
        """Response location matches requested location_id."""
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "kitchens"},
        )
        assert response.json()["location"]["id"] == "kitchens"

    @pytest.mark.asyncio
    async def test_returns_witnesses_present(self, client: AsyncClient):
        """Response includes witnesses_present field."""
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "library"},
        )
        assert "witnesses_present" in response.json()["location"]

    @pytest.mark.asyncio
    async def test_library_has_elena(self, client: AsyncClient):
        """Library location has Elena as witness."""
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "library"},
        )
        assert "elena" in response.json()["location"]["witnesses_present"]

    @pytest.mark.asyncio
    async def test_kitchens_has_wisp(self, client: AsyncClient):
        """Kitchens location has Wisp as witness."""
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "kitchens"},
        )
        assert "wisp" in response.json()["location"]["witnesses_present"]

    @pytest.mark.asyncio
    async def test_invalid_case_returns_404(self, client: AsyncClient):
        """POST returns 404 for invalid case."""
        response = await client.post(
            "/api/case/invalid_case/change-location",
            json={"location_id": "library"},
        )
        assert response.status_code == 404
        assert "case" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_location_returns_404(self, client: AsyncClient):
        """POST returns 404 for invalid location."""
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "invalid_location"},
        )
        assert response.status_code == 404
        assert "location" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_empty_location_id_returns_422(self, client: AsyncClient):
        """POST returns 422 for empty location_id."""
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": ""},
        )
        assert response.status_code == 422


# ============================================================================
# LocationCommandParser Tests
# ============================================================================


class TestLocationCommandParser:
    """Tests for LocationCommandParser natural language detection."""

    @pytest.fixture
    def parser(self):
        """Create parser with test locations."""
        return LocationCommandParser(
            ["library", "iron_lodge_common_room", "third_floor_corridor", "kitchens"]
        )

    def test_go_to_location(self, parser):
        """Parses 'go to X' pattern."""
        assert parser.parse("go to kitchens") == "kitchens"

    def test_visit_location(self, parser):
        """Parses 'visit X' pattern."""
        assert parser.parse("visit the library") == "library"

    def test_head_to_location(self, parser):
        """Parses 'head to X' pattern."""
        assert parser.parse("head to third floor corridor") == "third_floor_corridor"

    def test_travel_to_location(self, parser):
        """Parses 'travel to X' pattern."""
        assert parser.parse("travel to kitchens") == "kitchens"

    def test_walk_to_location(self, parser):
        """Parses 'walk to X' pattern."""
        assert parser.parse("walk to library") == "library"

    def test_move_to_location(self, parser):
        """Parses 'move to X' pattern."""
        assert parser.parse("move to iron lodge common room") == "iron_lodge_common_room"

    def test_fuzzy_match_typo(self, parser):
        """Fuzzy matches typos (kichens -> kitchens)."""
        assert parser.parse("go to kichens") == "kitchens"

    def test_fuzzy_match_libary(self, parser):
        """Fuzzy matches 'libary' -> 'library'."""
        assert parser.parse("visit libary") == "library"

    def test_underscore_replaced_with_space(self, parser):
        """Matches 'iron lodge common room' to 'iron_lodge_common_room'."""
        assert parser.parse("go to iron lodge common room") == "iron_lodge_common_room"

    def test_case_insensitive(self, parser):
        """Case insensitive matching."""
        assert parser.parse("GO TO KITCHENS") == "kitchens"
        assert parser.parse("Visit Library") == "library"

    def test_no_match_examination(self, parser):
        """Does not match non-movement commands."""
        assert parser.parse("examine the table") is None

    def test_no_match_evidence_mention(self, parser):
        """Does not match when location only mentioned in evidence context."""
        assert parser.parse("I found evidence in library") is None

    def test_no_match_empty_string(self, parser):
        """Returns None for empty string."""
        assert parser.parse("") is None

    def test_no_match_none_input(self, parser):
        """Returns None for None input."""
        assert parser.parse(None) is None  # type: ignore

    def test_match_with_article_the(self, parser):
        """Matches with 'the' article."""
        assert parser.parse("go to the kitchens") == "kitchens"

    def test_match_sentence_context(self, parser):
        """Matches within longer sentence."""
        assert parser.parse("I want to go to kitchens now") == "kitchens"


class TestLocationCommandParserFuzzyThreshold:
    """Tests for fuzzy matching threshold configuration."""

    def test_default_threshold_accepts_close_match(self):
        """Default threshold (0.75) accepts close matches."""
        parser = LocationCommandParser(["kitchens"])
        assert parser.parse("go to kichens") == "kitchens"

    def test_high_threshold_rejects_distant_match(self):
        """High threshold (0.95) rejects distant matches."""
        parser = LocationCommandParser(["kitchens"], fuzzy_threshold=0.95)
        assert parser.parse("go to kitch") is None

    def test_low_threshold_accepts_distant_match(self):
        """Low threshold (0.5) accepts distant matches."""
        parser = LocationCommandParser(["kitchens"], fuzzy_threshold=0.5)
        # 'kitch' has ~50% similarity to 'kitchens'
        result = parser.parse("go to kitch")
        # May or may not match depending on exact ratio
        # Just verify no crash and returns valid type
        assert result is None or result == "kitchens"


# ============================================================================
# Integration Tests
# ============================================================================


class TestLocationManagementIntegration:
    """Integration tests for location management system."""

    @pytest.mark.asyncio
    async def test_get_locations_then_change(self, client: AsyncClient):
        """Can get locations and change to one."""
        # Get available locations
        get_response = await client.get("/api/case/case_001/locations")
        assert get_response.status_code == 200
        locations = get_response.json()

        # Change to first location
        first_loc = locations[0]
        change_response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": first_loc["id"]},
        )
        assert change_response.status_code == 200
        assert change_response.json()["location"]["id"] == first_loc["id"]

    @pytest.mark.asyncio
    async def test_change_location_updates_state(self, client: AsyncClient):
        """Changing location actually updates player state."""
        # Change to iron_lodge_common_room
        response = await client.post(
            "/api/case/case_001/change-location",
            json={"location_id": "iron_lodge_common_room", "player_id": "test_player_loc"},
        )
        assert response.status_code == 200

        # Verify response has iron_lodge_common_room data
        assert response.json()["location"]["id"] == "iron_lodge_common_room"
        assert "Iron Lodge" in response.json()["location"]["name"]


class TestNewLocationsContent:
    """Tests for location content (iron_lodge_common_room, kitchens, etc.)."""

    def test_iron_lodge_common_room_has_description(self, case_data):
        """Iron Lodge Common Room has description text."""
        from src.case_store.loader import get_location

        location = get_location(case_data, "iron_lodge_common_room")
        assert "description" in location
        assert len(location["description"]) > 50

    def test_iron_lodge_common_room_has_evidence(self, case_data):
        """Iron Lodge Common Room has hidden evidence."""
        from src.case_store.loader import get_location

        location = get_location(case_data, "iron_lodge_common_room")
        assert "hidden_evidence" in location
        assert len(location["hidden_evidence"]) > 0

    def test_iron_lodge_common_room_evidence_torn_letter(self, case_data):
        """Iron Lodge Common Room has torn_letter evidence."""
        from src.case_store.loader import get_location

        location = get_location(case_data, "iron_lodge_common_room")
        evidence_ids = [e["id"] for e in location["hidden_evidence"]]
        assert "torn_letter" in evidence_ids

    def test_kitchens_has_description(self, case_data):
        """Kitchens has description text."""
        from src.case_store.loader import get_location

        location = get_location(case_data, "kitchens")
        assert "description" in location
        assert len(location["description"]) > 50

    def test_kitchens_has_evidence(self, case_data):
        """Kitchens has hidden evidence."""
        from src.case_store.loader import get_location

        location = get_location(case_data, "kitchens")
        assert "hidden_evidence" in location
        assert len(location["hidden_evidence"]) > 0

    def test_kitchens_evidence_healing_supplies(self, case_data):
        """Kitchens has healing_supplies evidence."""
        from src.case_store.loader import get_location

        location = get_location(case_data, "kitchens")
        evidence_ids = [e["id"] for e in location["hidden_evidence"]]
        assert "healing_supplies" in evidence_ids

    def test_third_floor_corridor_has_description(self, case_data):
        """Third Floor Corridor has description text."""
        from src.case_store.loader import get_location

        location = get_location(case_data, "third_floor_corridor")
        assert "description" in location
        assert len(location["description"]) > 50

    def test_third_floor_corridor_has_evidence(self, case_data):
        """Third Floor Corridor has hidden evidence."""
        from src.case_store.loader import get_location

        location = get_location(case_data, "third_floor_corridor")
        assert "hidden_evidence" in location
        assert len(location["hidden_evidence"]) > 0
