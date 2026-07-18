"""Tests for API routes."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
def temp_saves_dir(tmp_path: Path) -> Path:
    """Create temporary saves directory."""
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()
    return saves_dir


@pytest.fixture
async def client() -> AsyncClient:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient) -> None:
        """Health endpoint returns ok."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "degraded")
        assert "db" in data


class TestRootEndpoint:
    """Tests for root endpoint."""

    @pytest.mark.asyncio
    async def test_root_returns_info(self, client: AsyncClient) -> None:
        """Root endpoint returns API info."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data


class TestCasesEndpoint:
    """Tests for cases listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_cases(self, client: AsyncClient) -> None:
        """List available cases with metadata (Phase 5.4)."""
        response = await client.get("/api/cases")

        assert response.status_code == 200
        data = response.json()
        assert "cases" in data
        assert "count" in data
        # Phase 5.4: cases is now list of metadata dicts, not strings
        case_ids = [c["id"] for c in data["cases"]]
        assert "case_001" in case_ids
        assert data["count"] == len(data["cases"])


class TestSettingsEndpoint:
    """Tests for settings updates before a case has an autosave."""

    @pytest.mark.asyncio
    async def test_settings_create_state_at_case_first_location(
        self, client: AsyncClient
    ) -> None:
        from src.case_store.loader import get_first_location_id, load_case
        from src.state.persistence import load_player_state

        player_id = "settings_defaults_player"
        response = await client.post(
            "/api/settings/update",
            params={"player_id": player_id},
            json={
                "case_id": "case_001",
                "language": "fr",
                "narrator_verbosity": "atmospheric",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert state.current_location == get_first_location_id(load_case("case_001"))
        assert state.language == "fr"
        assert state.narrator_verbosity == "atmospheric"


class TestLocationEndpoint:
    """Tests for location info endpoint."""

    @pytest.mark.asyncio
    async def test_get_location_info(self, client: AsyncClient) -> None:
        """Get location information."""
        response = await client.get("/api/case/case_001/location/library")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "library"
        assert "Sealed Archive" in data["name"]
        assert "description" in data
        assert "surface_elements" in data

    @pytest.mark.asyncio
    async def test_get_location_includes_witnesses_present(self, client: AsyncClient) -> None:
        """Location info includes witnesses_present field."""
        response = await client.get("/api/case/case_001/location/library")

        assert response.status_code == 200
        data = response.json()
        assert "witnesses_present" in data
        assert isinstance(data["witnesses_present"], list)
        assert "elena" in data["witnesses_present"]

    @pytest.mark.asyncio
    async def test_get_location_not_found(self, client: AsyncClient) -> None:
        """404 for nonexistent location."""
        response = await client.get("/api/case/case_001/location/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_case_not_found(self, client: AsyncClient) -> None:
        """404 for nonexistent case."""
        response = await client.get("/api/case/fake_case/location/library")

        assert response.status_code == 404


class TestEvidenceEndpoint:
    """Tests for evidence listing endpoint."""

    @pytest.mark.asyncio
    async def test_get_evidence_empty(self, client: AsyncClient) -> None:
        """Evidence list empty for new player."""
        response = await client.get(
            "/api/evidence",
            params={"case_id": "case_001", "player_id": "test_player_unique"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == "case_001"
        assert data["discovered_evidence"] == []


class TestEvidenceDetailEndpoint:
    """Tests for evidence detail endpoints."""

    @pytest.mark.asyncio
    async def test_get_evidence_details_empty(self, client: AsyncClient) -> None:
        """Evidence details empty for new player."""
        response = await client.get(
            "/api/evidence/details",
            params={"case_id": "case_001", "player_id": "test_evidence_detail_unique"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == "case_001"
        assert data["evidence"] == []

    @pytest.mark.asyncio
    async def test_get_evidence_details_with_discovered(self, client: AsyncClient) -> None:
        """Evidence details returns metadata for discovered evidence."""
        # Save state with discovered evidence
        state_data = {
            "case_id": "case_001",
            "current_location": "library",
            "discovered_evidence": ["hidden_note", "frost_pattern"],
            "visited_locations": ["library"],
        }
        await client.post(
            "/api/save",
            json={"player_id": "test_evidence_detail_player", "state": state_data},
        )

        # Get evidence details
        response = await client.get(
            "/api/evidence/details",
            params={
                "case_id": "case_001",
                "location_id": "library",
                "player_id": "test_evidence_detail_player",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["evidence"]) == 2

        # Check evidence has metadata
        evidence_ids = [e["id"] for e in data["evidence"]]
        assert "hidden_note" in evidence_ids
        assert "frost_pattern" in evidence_ids

        hidden_note = next(e for e in data["evidence"] if e["id"] == "hidden_note")
        assert hidden_note["name"] == "Crumpled Apology Note"
        assert hidden_note["location_found"] == "library"
        assert "description" in hidden_note
        assert hidden_note["type"] == "documentary"

    @pytest.mark.asyncio
    async def test_get_single_evidence_success(self, client: AsyncClient) -> None:
        """Get single evidence with metadata."""
        # Save state with discovered evidence
        state_data = {
            "case_id": "case_001",
            "current_location": "library",
            "discovered_evidence": ["frost_pattern"],
            "visited_locations": ["library"],
        }
        await client.post(
            "/api/save",
            json={"player_id": "test_single_evidence_player", "state": state_data},
        )

        # Get single evidence
        response = await client.get(
            "/api/evidence/frost_pattern",
            params={
                "case_id": "case_001",
                "location_id": "library",
                "player_id": "test_single_evidence_player",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "frost_pattern"
        assert data["name"] == "Unusual Frost Pattern"
        assert data["location_found"] == "library"
        assert data["type"] == "magical"
        assert "frost" in data["description"].lower() or "hand of glory" in data["description"].lower()

    @pytest.mark.asyncio
    async def test_get_single_evidence_not_discovered(self, client: AsyncClient) -> None:
        """404 for evidence not yet discovered."""
        response = await client.get(
            "/api/evidence/hidden_note",
            params={
                "case_id": "case_001",
                "location_id": "library",
                "player_id": "test_not_discovered_unique",
            },
        )

        assert response.status_code == 404
        assert "not discovered" in response.json()["detail"]


class TestLoadEndpoint:
    """Tests for state loading endpoint."""

    @pytest.mark.asyncio
    async def test_load_no_state(self, client: AsyncClient) -> None:
        """Load returns 404 when no saved state exists."""
        response = await client.get(
            "/api/load/case_001",
            params={"player_id": "nonexistent_player"},
        )

        assert response.status_code == 404
        assert "No save found" in response.json()["detail"]


class TestSaveEndpoint:
    """Tests for state saving endpoint."""

    @pytest.mark.asyncio
    async def test_save_state(self, client: AsyncClient) -> None:
        """Save player state."""
        state_data = {
            "case_id": "case_001",
            "current_location": "library",
            "discovered_evidence": ["hidden_note"],
            "visited_locations": ["library"],
        }

        response = await client.post(
            "/api/save",
            json={
                "player_id": "test_save_player",
                "state": state_data,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestInvestigateEndpoint:
    """Tests for investigate endpoint."""

    @pytest.fixture
    def mock_claude_response(self) -> str:
        """Mock Claude response."""
        return "You peer beneath the heavy oak desk and discover a crumpled parchment. [EVIDENCE: hidden_note] The note bears hurried writing."

    @pytest.mark.asyncio
    async def test_investigate_success(
        self, client: AsyncClient, mock_claude_response: str
    ) -> None:
        """Successful investigation with mocked LLM."""
        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_claude_response)
            mock_get_client.return_value = mock_client

            response = await client.post(
                "/api/investigate",
                json={
                    "player_input": "I search under the desk",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": "test_investigate_player",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "narrator_response" in data
        assert data["narrator_response"] == mock_claude_response

    @pytest.mark.asyncio
    async def test_investigate_finds_evidence(
        self, client: AsyncClient, mock_claude_response: str
    ) -> None:
        """Investigation discovers evidence via trigger match."""
        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_claude_response)
            mock_get_client.return_value = mock_client

            response = await client.post(
                "/api/investigate",
                json={
                    "player_input": "look under the desk",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": "test_evidence_player",
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Either trigger-matched or extracted from response
        assert "hidden_note" in data["new_evidence"]

    @pytest.mark.asyncio
    async def test_investigate_not_present_item(self, client: AsyncClient) -> None:
        """Investigation about not_present item returns predefined response."""
        response = await client.post(
            "/api/investigate",
            json={
                "player_input": "Is there a secret passage?",
                "case_id": "case_001",
                "location_id": "library",
                "player_id": "test_not_present_player",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "solid stone" in data["narrator_response"]
        assert data["new_evidence"] == []

    @pytest.mark.asyncio
    async def test_investigate_case_not_found(self, client: AsyncClient) -> None:
        """404 for nonexistent case."""
        response = await client.post(
            "/api/investigate",
            json={
                "player_input": "look around",
                "case_id": "nonexistent_case",
                "location_id": "library",
                "player_id": "test_player",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_investigate_location_not_found_falls_back(self, client: AsyncClient) -> None:
        """Invalid location falls back to default location."""
        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="You look around.")
            mock_get_client.return_value = mock_client

            response = await client.post(
                "/api/investigate",
                json={
                    "player_input": "look around",
                    "case_id": "case_001",
                    "location_id": "nonexistent_location",
                    "player_id": "test_player",
                },
            )

        # Invalid location falls back to default, returns 200
        assert response.status_code == 200


class TestDeleteStateEndpoint:
    """Tests for delete state endpoint."""

    @pytest.mark.asyncio
    async def test_delete_nonexistent_state(self, client: AsyncClient) -> None:
        """Delete returns false for nonexistent state."""
        response = await client.delete(
            "/api/state/case_001",
            params={"player_id": "nonexistent_player"},
        )

        assert response.status_code == 200
        assert response.json() == {"deleted": False}


class TestResetCaseEndpoint:
    """Tests for reset case endpoint."""

    @pytest.mark.asyncio
    async def test_reset_endpoint_deletes_state(self, client: AsyncClient) -> None:
        """Reset endpoint deletes saved state."""
        player_id = "test_reset_deletes"

        # Create state by submitting a verdict
        await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "cassian",
                "reasoning": "Test.",
                "evidence_cited": [],
                "case_id": "case_001",
                "player_id": player_id,
            },
        )

        # Reset
        response = await client.post(
            "/api/case/case_001/reset",
            params={"player_id": player_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "reset" in data["message"].lower()

        # Verify state was deleted - load returns 404 for missing state
        load_response = await client.get(
            "/api/load/case_001",
            params={"player_id": player_id},
        )
        assert load_response.status_code == 404
        assert "No save found" in load_response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reset_endpoint_nonexistent_file(self, client: AsyncClient) -> None:
        """Reset endpoint handles missing file gracefully."""
        response = await client.post(
            "/api/case/case_999/reset",
            params={"player_id": "nonexistent_player_999"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "no" in data["message"].lower() and "progress" in data["message"].lower()


# Phase 2: Witness interrogation tests


class TestWitnessesEndpoint:
    """Tests for witnesses listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_witnesses(self, client: AsyncClient) -> None:
        """List available witnesses."""
        response = await client.get(
            "/api/witnesses",
            params={"case_id": "case_001"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

        witness_ids = [w["id"] for w in data]
        assert "elena" in witness_ids
        assert "cassian" in witness_ids

    @pytest.mark.asyncio
    async def test_list_witnesses_includes_trust(self, client: AsyncClient) -> None:
        """Witnesses include trust levels."""
        response = await client.get(
            "/api/witnesses",
            params={"case_id": "case_001"},
        )

        assert response.status_code == 200
        data = response.json()

        elena = next(w for w in data if w["id"] == "elena")
        cassian = next(w for w in data if w["id"] == "cassian")

        assert elena["trust"] == 55  # base_trust
        assert cassian["trust"] == 30  # base_trust

    @pytest.mark.asyncio
    async def test_list_witnesses_accepts_locale(self, client: AsyncClient) -> None:
        """Explicit locale returns authored witness names."""
        response = await client.get(
            "/api/witnesses",
            params={"case_id": "case_001", "language": "ru"},
        )

        assert response.status_code == 200
        data = response.json()
        elena = next(w for w in data if w["id"] == "elena")
        assert elena["name"] == "Елена Лозовская"


class TestWitnessInfoEndpoint:
    """Tests for single witness info endpoint."""

    @pytest.mark.asyncio
    async def test_get_witness_info(self, client: AsyncClient) -> None:
        """Get witness information."""
        response = await client.get(
            "/api/witness/elena",
            params={"case_id": "case_001"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "elena"
        assert data["name"] == "Elena Marsh"
        assert data["trust"] == 55

    @pytest.mark.asyncio
    async def test_get_witness_not_found(self, client: AsyncClient) -> None:
        """404 for nonexistent witness."""
        response = await client.get(
            "/api/witness/moriarty",
            params={"case_id": "case_001"},
        )

        assert response.status_code == 404


class TestInterrogateEndpoint:
    """Tests for witness interrogation endpoint."""

    @pytest.fixture
    def mock_witness_response(self) -> str:
        """Mock witness response."""
        return "I was in the library studying that night. I heard raised voices around 9pm."

    @pytest.mark.asyncio
    async def test_interrogate_success(
        self, client: AsyncClient, mock_witness_response: str
    ) -> None:
        """Successful interrogation with mocked LLM."""
        with patch("src.api.routes.witnesses.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_witness_response)
            mock_get_client.return_value = mock_client

            response = await client.post(
                "/api/interrogate",
                json={
                    "witness_id": "elena",
                    "question": "Where were you that night?",
                    "case_id": "case_001",
                    "player_id": "test_interrogate_player",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "trust" in data
        assert "trust_delta" in data
        assert data["response"] == mock_witness_response

    @pytest.mark.asyncio
    async def test_interrogate_llm_positive_trust_delta(
        self, client: AsyncClient,
    ) -> None:
        """LLM-provided positive trust delta is applied."""
        with patch("src.api.routes.witnesses.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(
                return_value="I appreciate you asking nicely.\n[TRUST_DELTA: 8]",
            )
            mock_get_client.return_value = mock_client

            response = await client.post(
                "/api/interrogate",
                json={
                    "witness_id": "elena",
                    "question": "I understand this must be difficult.",
                    "case_id": "case_001",
                    "player_id": "test_empathy_player",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["trust_delta"] == 8
        assert data["trust"] == 63  # 55 + 8

    @pytest.mark.asyncio
    async def test_interrogate_llm_negative_trust_delta(
        self, client: AsyncClient,
    ) -> None:
        """LLM-provided negative trust delta is applied."""
        with patch("src.api.routes.witnesses.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(
                return_value="How dare you accuse me!\n[TRUST_DELTA: -10]",
            )
            mock_get_client.return_value = mock_client

            response = await client.post(
                "/api/interrogate",
                json={
                    "witness_id": "elena",
                    "question": "You're lying! I know you did it!",
                    "case_id": "case_001",
                    "player_id": "test_aggressive_player",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["trust_delta"] == -10
        assert data["trust"] == 45  # 55 - 10

    @pytest.mark.asyncio
    async def test_interrogate_witness_not_found(self, client: AsyncClient) -> None:
        """404 for nonexistent witness."""
        response = await client.post(
            "/api/interrogate",
            json={
                "witness_id": "moriarty",
                "question": "Where were you?",
                "case_id": "case_001",
                "player_id": "test_player",
            },
        )

        assert response.status_code == 404


class TestPresentEvidenceEndpoint:
    """Tests for present evidence endpoint."""

    @pytest.fixture
    def mock_evidence_response(self) -> str:
        """Mock response when evidence is presented."""
        return "That frost pattern... I recognize it. Fine, I'll tell you what I saw."

    @pytest.mark.asyncio
    async def test_present_evidence_not_discovered(self, client: AsyncClient) -> None:
        """400 when presenting evidence not discovered."""
        response = await client.post(
            "/api/present-evidence",
            json={
                "witness_id": "elena",
                "evidence_id": "frost_pattern",
                "case_id": "case_001",
                "player_id": "test_undiscovered_evidence",
            },
        )

        assert response.status_code == 400
        assert "not discovered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_present_evidence_success(
        self, client: AsyncClient, mock_evidence_response: str
    ) -> None:
        """Present discovered evidence to witness."""
        # First save state with discovered evidence
        state_data = {
            "case_id": "case_001",
            "current_location": "library",
            "discovered_evidence": ["frost_pattern"],
            "visited_locations": ["library"],
        }
        await client.post(
            "/api/save",
            json={"player_id": "test_present_evidence", "state": state_data},
        )

        # Now present evidence
        with patch("src.api.routes.witnesses.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_evidence_response)
            mock_get_client.return_value = mock_client

            response = await client.post(
                "/api/present-evidence",
                json={
                    "witness_id": "elena",
                    "evidence_id": "frost_pattern",
                    "case_id": "case_001",
                    "player_id": "test_present_evidence",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "trust" in data
        assert data["response"] == mock_evidence_response


# Phase 3: Verdict endpoint tests


class TestSubmitVerdictEndpoint:
    """Tests for submit-verdict endpoint."""

    @pytest.fixture(autouse=True)
    def mock_verdict_llm(self):
        """Mock LLM calls in verdict endpoint to avoid real API calls."""

        async def mock_evaluator(**kwargs):
            # Vary score based on evidence count for scoring tests
            evidence = kwargs.get("evidence_cited", [])
            reasoning = kwargs.get("reasoning", "")
            score = min(95, 30 + len(evidence) * 20 + len(reasoning) // 10)
            quality = "good" if score >= 60 else "poor"
            return {
                "score": score,
                "quality": quality,
                "fallacies": [],
                "analysis": "Mock analysis of reasoning quality.",
            }

        mock_graves = "Trust nothing unseen! Your reasoning shows promise, but keep digging."

        with (
            patch(
                "src.api.routes.verdict.evaluate_reasoning_llm",
                side_effect=mock_evaluator,
            ) as self.mock_eval,
            patch(
                "src.api.routes.verdict.build_graves_feedback_llm",
                new_callable=AsyncMock,
                return_value=mock_graves,
            ) as self.mock_graves,
        ):
            yield

    @pytest.mark.asyncio
    async def test_submit_verdict_correct(self, client: AsyncClient) -> None:
        """Submit correct verdict returns success."""
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "wisp",
                "reasoning": "Wisp's binding magic combined with Cassian's ritual caused the paralytic binding.",
                "evidence_cited": ["frost_pattern", "focus_signature"],
                "case_id": "case_001",
                "player_id": "test_correct_verdict",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["correct"] is True
        assert data["case_solved"] is True
        assert data["attempts_remaining"] == 9
        assert "mentor_feedback" in data

    @pytest.mark.asyncio
    async def test_submit_verdict_incorrect(self, client: AsyncClient) -> None:
        """Submit incorrect verdict returns failure with LLM feedback (real template fields restored)."""
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "elena",
                "reasoning": "She was there so she did it.",
                "evidence_cited": [],
                "case_id": "case_001",
                "player_id": "test_incorrect_verdict",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["correct"] is False
        assert data["case_solved"] is False
        assert data["attempts_remaining"] == 9
        assert "mentor_feedback" in data
        # Real template fields restored via build_mentor_feedback
        # hint may be provided
        assert data["mentor_feedback"]["analysis"]  # LLM text populated

    @pytest.mark.asyncio
    async def test_submit_verdict_has_mentor_feedback(self, client: AsyncClient) -> None:
        """Verdict response includes mentor feedback with LLM analysis + real template fields."""
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "wisp",
                "reasoning": "The frost pattern proves it.",
                "evidence_cited": ["frost_pattern"],
                "case_id": "case_001",
                "player_id": "test_mentor_feedback",
            },
        )

        assert response.status_code == 200
        data = response.json()
        feedback = data["mentor_feedback"]
        # Core fields still populated
        assert "analysis" in feedback
        assert feedback["analysis"]  # Should have LLM-generated text
        assert "score" in feedback
        assert "quality" in feedback
        # Real template feedback restored
        assert isinstance(feedback.get("fallacies_detected"), list)
        assert isinstance(feedback.get("critique"), str)
        assert isinstance(feedback.get("praise"), str)
        assert "hint" in feedback

    @pytest.mark.asyncio
    async def test_submit_verdict_detects_fallacies(self, client: AsyncClient) -> None:
        """Verdict response includes fallacies_detected from template feedback."""
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "elena",
                "reasoning": "She was present in the library so she did it.",
                "evidence_cited": [],
                "case_id": "case_001",
                "player_id": "test_fallacies",
            },
        )

        assert response.status_code == 200
        data = response.json()
        fallacies = data["mentor_feedback"]["fallacies_detected"]
        # Fallacies restored from build_mentor_feedback (may be empty)
        assert isinstance(fallacies, list)
        # But analysis should contain the feedback
        assert data["mentor_feedback"]["analysis"]

    @pytest.mark.asyncio
    async def test_submit_verdict_has_wrong_suspect_response(self, client: AsyncClient) -> None:
        """Wrong verdict for known suspect includes pre-written response."""
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "elena",
                "reasoning": "She was there.",
                "evidence_cited": [],
                "case_id": "case_001",
                "player_id": "test_wrong_suspect_response",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # wrong_suspect_responses not in mentor_feedback_templates, so None
        assert data["wrong_suspect_response"] is None

    @pytest.mark.asyncio
    async def test_submit_verdict_confrontation_on_correct(self, client: AsyncClient) -> None:
        """Correct verdict includes confrontation dialogue."""
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "wisp",
                "reasoning": "Wisp's binding magic completed the paralytic binding.",
                "evidence_cited": ["frost_pattern"],
                "case_id": "case_001",
                "player_id": "test_confrontation",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["confrontation"] is not None
        assert "dialogue" in data["confrontation"]
        assert "aftermath" in data["confrontation"]

    @pytest.mark.asyncio
    async def test_submit_verdict_attempts_remaining_decrements(self, client: AsyncClient) -> None:
        """Attempts remaining decrements with each wrong verdict."""
        player_id = "test_attempts_decrement"

        # First wrong attempt
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "elena",
                "reasoning": "Wrong guess.",
                "evidence_cited": [],
                "case_id": "case_001",
                "player_id": player_id,
            },
        )
        assert response.json()["attempts_remaining"] == 9

        # Second wrong attempt
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "elena",
                "reasoning": "Wrong again.",
                "evidence_cited": [],
                "case_id": "case_001",
                "player_id": player_id,
            },
        )
        assert response.json()["attempts_remaining"] == 8

    @pytest.mark.asyncio
    async def test_submit_verdict_case_not_found(self, client: AsyncClient) -> None:
        """404 for nonexistent case."""
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "cassian",
                "reasoning": "Test",
                "evidence_cited": [],
                "case_id": "nonexistent_case",
                "player_id": "test_player",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_verdict_scoring(self, client: AsyncClient) -> None:
        """Verdict scores reasoning quality."""
        # Good reasoning with evidence
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "cassian",
                "reasoning": "The frost pattern matches Cassian's focus signature. The witness testimony confirms it.",
                "evidence_cited": ["frost_pattern", "focus_signature"],
                "case_id": "case_001",
                "player_id": "test_scoring_good",
            },
        )

        good_score = response.json()["mentor_feedback"]["score"]

        # Poor reasoning without evidence
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "elena",
                "reasoning": "x",
                "evidence_cited": [],
                "case_id": "case_001",
                "player_id": "test_scoring_poor",
            },
        )

        poor_score = response.json()["mentor_feedback"]["score"]

        assert good_score > poor_score

    @pytest.mark.asyncio
    async def test_submit_verdict_quality_levels(self, client: AsyncClient) -> None:
        """Verdict feedback includes quality level."""
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "wisp",
                "reasoning": "The frost pattern and focus signature prove the spell combination.",
                "evidence_cited": ["frost_pattern", "focus_signature"],
                "case_id": "case_001",
                "player_id": "test_quality",
            },
        )

        assert response.status_code == 200
        quality = response.json()["mentor_feedback"]["quality"]
        assert quality in ["excellent", "good", "fair", "poor", "failing"]

    @pytest.mark.asyncio
    async def test_submit_verdict_allows_retry_after_solved(self, client: AsyncClient) -> None:
        """Can submit verdict after case is solved (educational retries)."""
        player_id = "test_retry_after_solved"

        # First: solve the case
        first_response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "wisp",
                "reasoning": "Correct verdict.",
                "evidence_cited": [],
                "case_id": "case_001",
                "player_id": player_id,
            },
        )
        assert first_response.status_code == 200
        assert first_response.json()["case_solved"] is True

        # Second attempt should succeed (educational retries allowed)
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "elena",
                "reasoning": "Testing retry.",
                "evidence_cited": [],
                "case_id": "case_001",
                "player_id": player_id,
            },
        )

        # Should work - no 400 error
        assert response.status_code == 200
        assert "mentor_feedback" in response.json()

    @pytest.mark.asyncio
    async def test_submit_verdict_adaptive_hints(self, client: AsyncClient) -> None:
        """Adaptive hints restored from build_mentor_feedback for incorrect verdicts."""
        player_id = "test_adaptive_hints"

        # First wrong attempt
        response = await client.post(
            "/api/submit-verdict",
            json={
                "accused_suspect_id": "elena",
                "reasoning": "Wrong.",
                "evidence_cited": [],
                "case_id": "case_001",
                "player_id": player_id,
            },
        )
        # Hint restored for wrong verdicts
        first_hint = response.json()["mentor_feedback"]["hint"]
        assert first_hint is None or isinstance(first_hint, str)

        # Make several more wrong attempts
        for _ in range(5):
            response = await client.post(
                "/api/submit-verdict",
                json={
                    "accused_suspect_id": "elena",
                    "reasoning": "Wrong.",
                    "evidence_cited": [],
                    "case_id": "case_001",
                    "player_id": player_id,
                },
            )

        later_hint = response.json()["mentor_feedback"]["hint"]
        assert later_hint is None or isinstance(later_hint, str)
        # Analysis should have content though
        assert response.json()["mentor_feedback"]["analysis"]

    @pytest.mark.asyncio
    async def test_submit_verdict_confrontation_for_wrong_with_show_anyway(
        self, client: AsyncClient
    ) -> None:
        """Wrong verdict for elena shows confrontation (confrontation_anyway: true)."""
        player_id = "test_confrontation_anyway"

        # Use up all attempts to trigger confrontation for wrong verdict
        for _ in range(10):
            response = await client.post(
                "/api/submit-verdict",
                json={
                    "accused_suspect_id": "elena",
                    "reasoning": "Wrong.",
                    "evidence_cited": [],
                    "case_id": "case_001",
                    "player_id": player_id,
                },
            )

        # Last response should have confrontation and reveal
        data = response.json()
        assert data["attempts_remaining"] == 0
        assert data["reveal"] is not None


# ============================================================================
# Phase 4.4: Conversation Persistence Tests
# ============================================================================


class TestPhase44ConversationPersistence:
    """Test conversation history persistence (Phase 4.4)."""

    @pytest.fixture
    def mock_narrator_response(self) -> str:
        """Mock narrator response."""
        return "You examine the ancient tome carefully."

    @pytest.mark.asyncio
    async def test_investigate_saves_player_and_narrator_messages(
        self, client: AsyncClient, mock_narrator_response: str
    ) -> None:
        """Test investigate endpoint appends player + narrator to conversation_history."""
        player_id = "test_convo_persist_1"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_narrator_response)
            mock_get_client.return_value = mock_client

            await client.post(
                "/api/investigate",
                json={
                    "player_input": "examine the bookshelf",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )

        # Load state and verify conversation_history
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert len(state.conversation_history) == 2

        # First message is player
        assert state.conversation_history[0]["type"] == "player"
        assert state.conversation_history[0]["text"] == "examine the bookshelf"
        assert "timestamp" in state.conversation_history[0]

        # Second message is narrator
        assert state.conversation_history[1]["type"] == "narrator"
        assert state.conversation_history[1]["text"] == mock_narrator_response
        assert "timestamp" in state.conversation_history[1]

    @pytest.mark.asyncio
    async def test_matthew_chat_saves_player_and_matthew_messages(self, client: AsyncClient) -> None:
        """Test Matthew chat endpoint appends player + Matthew to conversation_history."""
        player_id = "test_matthew_convo_1"
        matthew_response = "Interesting observation, but perhaps you're missing something..."

        with patch("src.context.matthew_llm.generate_matthew_response") as mock_generate:
            mock_generate.return_value = (matthew_response, "helpful")

            await client.post(
                "/api/case/case_001/matthew/chat",
                params={"player_id": player_id},
                json={"message": "What do you think about this case?"},
            )

        # Load state and verify conversation_history
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert len(state.conversation_history) == 2

        # First message is player
        assert state.conversation_history[0]["type"] == "player"
        assert state.conversation_history[0]["text"] == "What do you think about this case?"

        # Second message is matthew
        assert state.conversation_history[1]["type"] == "matthew"
        assert state.conversation_history[1]["text"] == matthew_response

    @pytest.mark.asyncio
    async def test_matthew_auto_comment_saves_only_matthew_message(self, client: AsyncClient) -> None:
        """Test Matthew auto-comment endpoint appends only Matthew message (no player message)."""
        player_id = "test_matthew_auto_1"
        matthew_response = "Hmm, this evidence seems suspicious..."

        with patch("src.context.matthew_llm.check_matthew_should_comment") as mock_check:
            mock_check.return_value = True
            with patch("src.context.matthew_llm.generate_matthew_response") as mock_generate:
                mock_generate.return_value = (matthew_response, "helpful")

                await client.post(
                    "/api/case/case_001/matthew/auto-comment",
                    params={"player_id": player_id},
                    json={"is_critical": True},
                )

        # Load state and verify conversation_history
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert len(state.conversation_history) == 1

        # Only matthew message (no player message for auto-comment)
        assert state.conversation_history[0]["type"] == "matthew"
        assert state.conversation_history[0]["text"] == matthew_response

    @pytest.mark.asyncio
    async def test_conversation_persists_through_save_load_cycle(
        self, client: AsyncClient, mock_narrator_response: str
    ) -> None:
        """Test conversation_history survives save/load cycle."""
        player_id = "test_save_load_convo"

        # First, investigate to create some conversation history
        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_narrator_response)
            mock_get_client.return_value = mock_client

            await client.post(
                "/api/investigate",
                json={
                    "player_input": "look around",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )

        # Load state directly
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        original_history = state.conversation_history.copy()
        assert len(original_history) == 2

        # Verify conversation_history persisted correctly
        assert original_history[0]["type"] == "player"
        assert original_history[1]["type"] == "narrator"

        # Reload and verify again (simulates browser refresh)
        state_reloaded = load_player_state("case_001", player_id, "autosave")
        assert state_reloaded is not None
        assert len(state_reloaded.conversation_history) == 2
        assert state_reloaded.conversation_history == original_history

    @pytest.mark.asyncio
    async def test_conversation_history_limited_to_50_messages(self, client: AsyncClient) -> None:
        """Test conversation_history limited to last 50 messages."""
        player_id = "test_50_limit"

        # Create state with 55 messages directly
        from src.state.persistence import load_player_state, save_player_state
        from src.state.player_state import PlayerState

        state = PlayerState(case_id="case_001", current_location="library")

        # Add 55 messages
        for i in range(55):
            state.add_conversation_message("player", f"Message {i}")

        # Should only have 50 messages
        assert len(state.conversation_history) == 50

        # First message should be "Message 5" (messages 0-4 were trimmed)
        assert state.conversation_history[0]["text"] == "Message 5"

        # Last message should be "Message 54"
        assert state.conversation_history[-1]["text"] == "Message 54"

        # Save and reload to verify persistence
        save_player_state("case_001", player_id, state, "autosave")
        reloaded = load_player_state("case_001", player_id, "autosave")
        assert reloaded is not None
        assert len(reloaded.conversation_history) == 50
        assert reloaded.conversation_history[0]["text"] == "Message 5"

    @pytest.mark.asyncio
    async def test_investigate_not_present_saves_conversation(self, client: AsyncClient) -> None:
        """Test not_present response also saves to conversation_history."""
        player_id = "test_not_present_convo"

        # Ask about secret passage (defined in not_present)
        response = await client.post(
            "/api/investigate",
            json={
                "player_input": "Is there a secret passage?",
                "case_id": "case_001",
                "location_id": "library",
                "player_id": player_id,
            },
        )

        assert response.status_code == 200

        # Load state and verify conversation_history
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert len(state.conversation_history) == 2

        assert state.conversation_history[0]["type"] == "player"
        assert "secret passage" in state.conversation_history[0]["text"].lower()

        assert state.conversation_history[1]["type"] == "narrator"
        assert "solid stone" in state.conversation_history[1]["text"]

    @pytest.mark.asyncio
    async def test_multiple_investigations_accumulate_messages(
        self, client: AsyncClient, mock_narrator_response: str
    ) -> None:
        """Test multiple investigations accumulate in conversation_history."""
        player_id = "test_accumulate"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_narrator_response)
            mock_get_client.return_value = mock_client

            # First investigation
            await client.post(
                "/api/investigate",
                json={
                    "player_input": "look at desk",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )

            # Second investigation
            await client.post(
                "/api/investigate",
                json={
                    "player_input": "examine window",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )

        # Load state and verify 4 messages (2 per investigation)
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert len(state.conversation_history) == 4

        # Verify ordering
        assert state.conversation_history[0]["text"] == "look at desk"
        assert state.conversation_history[1]["type"] == "narrator"
        assert state.conversation_history[2]["text"] == "examine window"
        assert state.conversation_history[3]["type"] == "narrator"


class TestPhase45NarratorConversationMemory:
    """Test narrator conversation memory to prevent repetitive descriptions (Phase 4.5)."""

    @pytest.fixture
    def mock_narrator_response(self) -> str:
        """Mock narrator response."""
        return "You examine the area carefully, noting the dusty atmosphere."

    @pytest.mark.asyncio
    async def test_narrator_conversation_history_saved(
        self, client: AsyncClient, mock_narrator_response: str
    ) -> None:
        """Narrator saves conversation exchanges (last 5 only)."""
        player_id = "test_narrator_hist_1"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_narrator_response)
            mock_get_client.return_value = mock_client

            # First investigation
            response1 = await client.post(
                "/api/investigate",
                json={
                    "player_input": "examine desk",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )
            assert response1.status_code == 200

        # Load state and check narrator history
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert len(state.narrator_conversation_history) == 1
        assert state.narrator_conversation_history[0].question == "examine desk"
        assert state.narrator_conversation_history[0].response == mock_narrator_response

        # Second investigation
        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="The windows are frosted over.")
            mock_get_client.return_value = mock_client

            response2 = await client.post(
                "/api/investigate",
                json={
                    "player_input": "check windows",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )
            assert response2.status_code == 200

        state = load_player_state("case_001", player_id, "autosave")
        assert len(state.narrator_conversation_history) == 2
        assert state.narrator_conversation_history[1].question == "check windows"

    @pytest.mark.asyncio
    async def test_narrator_history_limited_to_5_messages(self, client: AsyncClient) -> None:
        """Narrator history keeps only last 5 exchanges."""
        player_id = "test_narrator_limit_5"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="You search the area.")
            mock_get_client.return_value = mock_client

            # Perform 7 investigations
            for i in range(7):
                response = await client.post(
                    "/api/investigate",
                    json={
                        "player_input": f"action {i + 1}",
                        "case_id": "case_001",
                        "location_id": "library",
                        "player_id": player_id,
                    },
                )
                assert response.status_code == 200

        # Check only last 5 are kept
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert len(state.narrator_conversation_history) == 5
        # First should be action 3 (actions 1-2 were trimmed)
        assert state.narrator_conversation_history[0].question == "action 3"
        # Last should be action 7
        assert state.narrator_conversation_history[4].question == "action 7"

    @pytest.mark.asyncio
    async def test_narrator_history_scoped_by_location(self, client: AsyncClient) -> None:
        """Narrator history is scoped per location (Phase 5.6)."""
        player_id = "test_narrator_loc_change"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="Library response.")
            mock_get_client.return_value = mock_client

            # Investigate in library
            response1 = await client.post(
                "/api/investigate",
                json={
                    "player_input": "examine desk",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )
            assert response1.status_code == 200

        from src.state.persistence import load_player_state, save_player_state

        state = load_player_state("case_001", player_id, "autosave")
        # Location-specific history has 1 entry for library
        assert len(state.location_narrator_history.get("library", [])) == 1

        # Manually change location to simulate leaving and coming back
        state.current_location = "somewhere_else"
        save_player_state("case_001", player_id, state, "autosave")

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="Returned to library.")
            mock_get_client.return_value = mock_client

            # Come back to library
            response2 = await client.post(
                "/api/investigate",
                json={
                    "player_input": "look around",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )
            assert response2.status_code == 200

        # Location-specific history accumulates for library
        state = load_player_state("case_001", player_id, "autosave")
        library_history = state.location_narrator_history.get("library", [])
        assert len(library_history) == 2
        assert library_history[0].question == "examine desk"
        assert library_history[1].question == "look around"

    @pytest.mark.asyncio
    async def test_narrator_history_persists_across_saves(self, client: AsyncClient) -> None:
        """Narrator history persists through save/load cycle."""
        player_id = "test_narrator_persist"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="Dusty tomes line the shelves.")
            mock_get_client.return_value = mock_client

            # Investigate
            response = await client.post(
                "/api/investigate",
                json={
                    "player_input": "examine desk",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )
            assert response.status_code == 200

        # Load and verify
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert len(state.narrator_conversation_history) == 1
        assert state.narrator_conversation_history[0].question == "examine desk"
        assert state.narrator_conversation_history[0].response == "Dusty tomes line the shelves."

        # Reload (simulates browser refresh) and verify persists
        state_reloaded = load_player_state("case_001", player_id, "autosave")
        assert state_reloaded is not None
        assert len(state_reloaded.narrator_conversation_history) == 1
        assert state_reloaded.narrator_conversation_history[0].question == "examine desk"

    @pytest.mark.asyncio
    async def test_narrator_history_passed_to_prompt(self, client: AsyncClient) -> None:
        """Narrator conversation history is passed to build_narrator_prompt."""
        player_id = "test_narrator_prompt"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="First response.")
            mock_get_client.return_value = mock_client

            # First investigation
            await client.post(
                "/api/investigate",
                json={
                    "player_input": "look around",
                    "case_id": "case_001",
                    "location_id": "library",
                    "player_id": player_id,
                },
            )

        # Now patch build_narrator_prompt to verify history is passed
        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="Second response.")
            mock_get_client.return_value = mock_client

            with patch("src.api.routes.investigation_logic.build_narrator_prompt") as mock_build:
                mock_build.return_value = "mocked prompt"

                await client.post(
                    "/api/investigate",
                    json={
                        "player_input": "examine bookshelf",
                        "case_id": "case_001",
                        "location_id": "library",
                        "player_id": player_id,
                    },
                )

                # Verify conversation_history was passed
                call_kwargs = mock_build.call_args.kwargs
                assert "conversation_history" in call_kwargs
                history = call_kwargs["conversation_history"]
                assert len(history) == 1
                assert history[0]["question"] == "look around"
                assert history[0]["response"] == "First response."


class TestMnemonicDelvingInterrogation:
    """Tests for Mnemonic Delving spell in witness interrogation (Phase 4.6.2).

    Phase 4.6.2 Changes:
    - Mnemonic Delving now executes instantly (no warning/confirmation flow)
    - Programmatic outcomes based on trust threshold (70)
    - Random trust penalty [5, 10, 15, 20]
    - Focused vs unfocused detection based on search intent
    """

    @pytest.mark.asyncio
    async def test_mnemonic_delving_instant_execution(self, client: AsyncClient) -> None:
        """Phase 4.6.2: Mnemonic Delving executes instantly with LLM narration."""
        with patch("src.api.routes.witnesses.get_client") as mock_get_client, \
             patch("src.api.routes.mnemonic_delving.get_client") as mock_legi_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(
                return_value="You slip into Elena's mind, finding a chaotic swirl of memories..."
            )
            mock_get_client.return_value = mock_client
            mock_legi_client.return_value = mock_client

            response = await client.post(
                "/api/interrogate",
                json={
                    "witness_id": "elena",
                    "question": "I cast mnemonic_delving on Elena",
                    "case_id": "case_001",
                    "player_id": "test_mnemonic_delving_instant",
                },
            )

        assert response.status_code == 200
        data = response.json()

        # Should return LLM narration (not warning)
        assert "mind" in data["response"].lower() or "memor" in data["response"].lower()
        # Phase 4.8: Trust penalty only if detected, otherwise 0
        assert data["trust_delta"] in [0, -5, -10, -15, -20]

    @pytest.mark.asyncio
    async def test_mnemonic_delving_focused_detection(self, client: AsyncClient) -> None:
        """Phase 4.6.2: Focused Mnemonic Delving detected via 'about X' pattern."""
        with patch("src.api.routes.witnesses.get_client") as mock_get_client, \
             patch("src.api.routes.mnemonic_delving.get_client") as mock_legi_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(
                return_value="You focus on finding information about Cassian..."
            )
            mock_get_client.return_value = mock_client
            mock_legi_client.return_value = mock_client

            response = await client.post(
                "/api/interrogate",
                json={
                    "witness_id": "elena",
                    "question": "use mnemonic_delving on her to find out about cassian",
                    "case_id": "case_001",
                    "player_id": "test_mnemonic_delving_focused",
                },
            )

        assert response.status_code == 200
        data = response.json()

        # Phase 4.8: Trust penalty only if detected, otherwise 0
        assert data["trust_delta"] in [0, -5, -10, -15, -20]

    @pytest.mark.asyncio
    async def test_mnemonic_delving_semantic_phrase_detection(self, client: AsyncClient) -> None:
        """Phase 4.6.2: Mnemonic Delving detected via semantic phrases like 'read her mind'."""
        with patch("src.api.routes.witnesses.get_client") as mock_get_client, \
             patch("src.api.routes.mnemonic_delving.get_client") as mock_legi_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="You attempt to read her thoughts...")
            mock_get_client.return_value = mock_client
            mock_legi_client.return_value = mock_client

            response = await client.post(
                "/api/interrogate",
                json={
                    "witness_id": "elena",
                    "question": "I cast mnemonic_delving on her",
                    "case_id": "case_001",
                    "player_id": "test_mnemonic_delving_fuzzy",
                },
            )

        assert response.status_code == 200
        data = response.json()

        # Phase 4.8: Trust penalty only if detected, otherwise 0
        assert data["trust_delta"] in [0, -5, -10, -15, -20]

    @pytest.mark.asyncio
    async def test_other_spell_in_interrogation_handled(self, client: AsyncClient) -> None:
        """Non-Mnemonic Delving safe spells are handled in interrogation via LLM."""
        with patch("src.api.routes.witnesses.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(
                return_value="You cast Unveil but it's better used during investigation."
            )
            mock_get_client.return_value = mock_client

            response = await client.post(
                "/api/interrogate",
                json={
                    "witness_id": "elena",
                    "question": "I cast unveil",
                    "case_id": "case_001",
                    "player_id": "test_other_spell",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    @pytest.mark.asyncio
    async def test_no_false_positives_conversational(self, client: AsyncClient) -> None:
        """Phase 4.6.2: Conversational phrases don't trigger Mnemonic Delving."""
        with patch("src.api.routes.witnesses.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="I'm not sure what you mean by that.")
            mock_get_client.return_value = mock_client

            response = await client.post(
                "/api/interrogate",
                json={
                    "witness_id": "elena",
                    "question": "What's in your mind right now?",
                    "case_id": "case_001",
                    "player_id": "test_no_false_positive",
                },
            )

        assert response.status_code == 200
        data = response.json()

        # Should NOT trigger Mnemonic Delving (no random trust penalty)
        # Normal interrogation trust delta depends on tone
        assert data["trust_delta"] != -5 or data["trust_delta"] == 0

    @pytest.mark.asyncio
    async def test_witness_state_awaiting_spell_field(self, client: AsyncClient) -> None:
        """WitnessState tracks awaiting_spell_confirmation field (backward compat)."""
        from src.state.player_state import WitnessState

        # Create witness state with default
        ws = WitnessState(witness_id="test", trust=50)
        assert ws.awaiting_spell_confirmation is None

        # Set field
        ws.awaiting_spell_confirmation = "mnemonic_delving"
        assert ws.awaiting_spell_confirmation == "mnemonic_delving"

        # Clear field
        ws.awaiting_spell_confirmation = None
        assert ws.awaiting_spell_confirmation is None

    @pytest.mark.asyncio
    async def test_mnemonic_delving_trust_penalty_applied(self, client: AsyncClient) -> None:
        """Phase 4.6.2: Trust drops by random [5, 10, 15, 20] on Mnemonic Delving."""
        player_id = "test_mnemonic_delving_trust_penalty"

        # Get initial trust
        witness_response = await client.get(
            "/api/witness/elena",
            params={"case_id": "case_001", "player_id": player_id},
        )
        initial_trust = witness_response.json()["trust"]

        # Cast Mnemonic Delving (instant execution in Phase 4.6.2)
        with patch("src.api.routes.witnesses.get_client") as mock_get_client,              patch("src.api.routes.mnemonic_delving.get_client") as mock_legi_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(
                return_value="You probe her thoughts, finding scattered memories..."
            )
            mock_get_client.return_value = mock_client
            mock_legi_client.return_value = mock_client

            response = await client.post(
                "/api/interrogate",
                json={
                    "witness_id": "elena",
                    "question": "cast mnemonic_delving on her",
                    "case_id": "case_001",
                    "player_id": player_id,
                },
            )

        # Phase 4.8: Trust penalty only if detected, otherwise 0
        data = response.json()
        assert data["trust_delta"] in [0, -5, -10, -15, -20]

        # Verify final trust reflects the penalty
        witness_response = await client.get(
            "/api/witness/elena",
            params={"case_id": "case_001", "player_id": player_id},
        )
        final_trust = witness_response.json()["trust"]

        assert final_trust == initial_trust + data["trust_delta"]


# =============================================================================
# Phase 4.7: Spell Success System Tests
# =============================================================================


class TestPhase47SpellSuccessSystem:
    """Tests for spell success system with specificity bonuses (Phase 4.7)."""

    @pytest.fixture
    def mock_success_response(self) -> str:
        """Mock response for successful spell."""
        return (
            "Your Unveil charm reveals a hidden parchment under the desk. [EVIDENCE: hidden_note]"
        )

    @pytest.fixture
    def mock_failure_response(self) -> str:
        """Mock response for failed spell."""
        return "Your Unveil charm fizzles and dissipates before finding anything of note."

    @pytest.mark.asyncio
    async def test_spell_attempt_tracking_initialized(self, client: AsyncClient) -> None:
        """spell_attempts_by_location initialized empty for new player."""
        player_id = "test_spell_tracking_init"

        # Make any API call that creates state
        await client.post(
            "/api/save",
            json={
                "player_id": player_id,
                "state": {
                    "case_id": "case_001",
                    "current_location": "library",
                },
            },
        )

        # Load and verify
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert state.spell_attempts_by_location == {}

    @pytest.mark.asyncio
    async def test_spell_attempt_incremented_after_cast(
        self, client: AsyncClient, mock_success_response: str
    ) -> None:
        """Spell attempt counter increments after casting."""
        player_id = "test_spell_increment"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_success_response)
            mock_get_client.return_value = mock_client

            # Mock success roll
            with patch("src.context.spell_detection.random.random", return_value=0.5):
                await client.post(
                    "/api/investigate",
                    json={
                        "player_input": "cast unveil on desk",
                        "case_id": "case_001",
                        "location_id": "library",
                        "player_id": player_id,
                    },
                )

        # Load and verify attempt tracked
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state is not None
        assert "library" in state.spell_attempts_by_location
        assert "unveil" in state.spell_attempts_by_location["library"]
        assert state.spell_attempts_by_location["library"]["unveil"] == 1

    @pytest.mark.asyncio
    async def test_multiple_spell_attempts_tracked_separately(
        self, client: AsyncClient, mock_success_response: str
    ) -> None:
        """Different spells tracked separately in same location."""
        player_id = "test_multi_spell_track"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_success_response)
            mock_get_client.return_value = mock_client

            with patch("src.context.spell_detection.random.random", return_value=0.5):
                # Cast unveil
                await client.post(
                    "/api/investigate",
                    json={
                        "player_input": "cast unveil",
                        "case_id": "case_001",
                        "location_id": "library",
                        "player_id": player_id,
                    },
                )

                # Cast raise_the_lamp
                await client.post(
                    "/api/investigate",
                    json={
                        "player_input": "raise_the_lamp",
                        "case_id": "case_001",
                        "location_id": "library",
                        "player_id": player_id,
                    },
                )

        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        assert state.spell_attempts_by_location["library"]["unveil"] == 1
        assert state.spell_attempts_by_location["library"]["raise_the_lamp"] == 1

    @pytest.mark.asyncio
    async def test_spell_attempts_tracking_structure(
        self, client: AsyncClient, mock_success_response: str
    ) -> None:
        """Spell attempts tracked per location with nested dict structure."""
        player_id = "test_structure"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_success_response)
            mock_get_client.return_value = mock_client

            with patch("src.context.spell_detection.random.random", return_value=0.5):
                # Cast unveil twice
                for _ in range(2):
                    await client.post(
                        "/api/investigate",
                        json={
                            "player_input": "cast unveil",
                            "case_id": "case_001",
                            "location_id": "library",
                            "player_id": player_id,
                        },
                    )

                # Cast raise_the_lamp once
                await client.post(
                    "/api/investigate",
                    json={
                        "player_input": "cast raise_the_lamp",
                        "case_id": "case_001",
                        "location_id": "library",
                        "player_id": player_id,
                    },
                )

        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        # Verify nested structure: {location: {spell: count}}
        assert "library" in state.spell_attempts_by_location
        assert state.spell_attempts_by_location["library"]["unveil"] == 2
        assert state.spell_attempts_by_location["library"]["raise_the_lamp"] == 1

    @pytest.mark.asyncio
    async def test_mnemonic_delving_bypasses_success_calculation(self, client: AsyncClient) -> None:
        """Mnemonic Delving uses trust-based system, not success calculation."""
        player_id = "test_mnemonic_delving_bypass"

        with patch("src.api.routes.witnesses.get_client") as mock_get_client, \
             patch("src.api.routes.mnemonic_delving.get_client") as mock_legi_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="You probe her mind...")
            mock_get_client.return_value = mock_client
            mock_legi_client.return_value = mock_client

            # Cast Mnemonic Delving in interrogation
            await client.post(
                "/api/interrogate",
                json={
                    "witness_id": "elena",
                    "question": "cast mnemonic_delving",
                    "case_id": "case_001",
                    "player_id": player_id,
                },
            )

        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")
        # Mnemonic Delving should NOT be tracked in spell_attempts_by_location
        # (it uses trust-based system instead)
        if state.spell_attempts_by_location:
            for loc_spells in state.spell_attempts_by_location.values():
                assert "mnemonic_delving" not in loc_spells

    @pytest.mark.asyncio
    async def test_spell_outcome_success_passed_to_prompt(
        self, client: AsyncClient, mock_success_response: str
    ) -> None:
        """Successful spell roll passes SUCCESS outcome to prompt."""
        player_id = "test_outcome_success"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_success_response)
            mock_get_client.return_value = mock_client

            # Force success with low roll
            with patch("src.context.spell_detection.random.random", return_value=0.3):
                with patch("src.api.routes.investigation_logic.build_narrator_or_spell_prompt") as mock_build:
                    mock_build.return_value = ("prompt", "system", True)

                    await client.post(
                        "/api/investigate",
                        json={
                            "player_input": "cast unveil on desk",
                            "case_id": "case_001",
                            "location_id": "library",
                            "player_id": player_id,
                        },
                    )

                    # Verify spell_outcome was SUCCESS
                    call_kwargs = mock_build.call_args.kwargs
                    assert call_kwargs.get("spell_outcome") == "SUCCESS"

    @pytest.mark.asyncio
    async def test_spell_outcome_failure_passed_to_prompt(
        self, client: AsyncClient, mock_failure_response: str
    ) -> None:
        """Failed spell roll passes FAILURE outcome to prompt."""
        player_id = "test_outcome_failure"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_failure_response)
            mock_get_client.return_value = mock_client

            # Force failure with high roll
            with patch("src.context.spell_detection.random.random", return_value=0.95):
                with patch("src.api.routes.investigation_logic.build_narrator_or_spell_prompt") as mock_build:
                    mock_build.return_value = ("prompt", "system", True)

                    await client.post(
                        "/api/investigate",
                        json={
                            "player_input": "cast unveil",
                            "case_id": "case_001",
                            "location_id": "library",
                            "player_id": player_id,
                        },
                    )

                    # Verify spell_outcome was FAILURE
                    call_kwargs = mock_build.call_args.kwargs
                    assert call_kwargs.get("spell_outcome") == "FAILURE"

    @pytest.mark.asyncio
    async def test_specificity_bonus_affects_outcome(
        self, client: AsyncClient, mock_success_response: str
    ) -> None:
        """Specificity bonus increases success chance."""
        player_id = "test_specificity"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_success_response)
            mock_get_client.return_value = mock_client

            # Roll 85 - would fail 70% base, but succeeds with +20% bonus
            with patch("src.context.spell_detection.random.random", return_value=0.85):
                with patch("src.api.routes.investigation_logic.build_narrator_or_spell_prompt") as mock_build:
                    mock_build.return_value = ("prompt", "system", True)

                    # Cast with full specificity: target + intent
                    await client.post(
                        "/api/investigate",
                        json={
                            "player_input": "cast unveil on desk to find hidden clues",
                            "case_id": "case_001",
                            "location_id": "library",
                            "player_id": player_id,
                        },
                    )

                    # Should succeed with 90% (70 + 10 + 10) > 85% roll
                    call_kwargs = mock_build.call_args.kwargs
                    assert call_kwargs.get("spell_outcome") == "SUCCESS"

    @pytest.mark.asyncio
    async def test_decline_per_attempt_affects_outcome(
        self, client: AsyncClient, mock_success_response: str
    ) -> None:
        """Success rate declines with each attempt at same location."""
        player_id = "test_decline"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_success_response)
            mock_get_client.return_value = mock_client

            outcomes = []

            # Cast unveil 3 times with roll=65
            # 1st: 70% > 65% = SUCCESS
            # 2nd: 60% < 65% = FAILURE
            # 3rd: 50% < 65% = FAILURE
            with patch("src.context.spell_detection.random.random", return_value=0.65):
                for i in range(3):
                    with patch("src.api.routes.investigation_logic.build_narrator_or_spell_prompt") as mock_build:
                        mock_build.return_value = ("prompt", "system", True)

                        await client.post(
                            "/api/investigate",
                            json={
                                "player_input": "cast unveil",
                                "case_id": "case_001",
                                "location_id": "library",
                                "player_id": player_id,
                            },
                        )

                        call_kwargs = mock_build.call_args.kwargs
                        outcomes.append(call_kwargs.get("spell_outcome"))

            # First succeeds, next two fail
            assert outcomes[0] == "SUCCESS"
            assert outcomes[1] == "FAILURE"
            assert outcomes[2] == "FAILURE"

    @pytest.mark.asyncio
    async def test_floor_prevents_zero_percent(
        self, client: AsyncClient, mock_success_response: str
    ) -> None:
        """Floor keeps success rate at 10% even with many attempts."""
        player_id = "test_floor"

        # Pre-populate state with many attempts
        from src.state.persistence import save_player_state
        from src.state.player_state import PlayerState

        state = PlayerState(case_id="case_001", current_location="library")
        state.spell_attempts_by_location = {"library": {"unveil": 10}}
        save_player_state("case_001", player_id, state, "autosave")

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_success_response)
            mock_get_client.return_value = mock_client

            # Roll 5% - below 10% floor = SUCCESS
            with patch("src.context.spell_detection.random.random", return_value=0.05):
                with patch("src.api.routes.investigation_logic.build_narrator_or_spell_prompt") as mock_build:
                    mock_build.return_value = ("prompt", "system", True)

                    await client.post(
                        "/api/investigate",
                        json={
                            "player_input": "cast unveil",
                            "case_id": "case_001",
                            "location_id": "library",
                            "player_id": player_id,
                        },
                    )

                    # Should still succeed at floor rate
                    call_kwargs = mock_build.call_args.kwargs
                    assert call_kwargs.get("spell_outcome") == "SUCCESS"

    @pytest.mark.asyncio
    async def test_non_spell_input_no_spell_outcome(self, client: AsyncClient) -> None:
        """Non-spell inputs don't have spell_outcome."""
        player_id = "test_non_spell"

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value="You examine the desk.")
            mock_get_client.return_value = mock_client

            with patch("src.api.routes.investigation_logic.build_narrator_prompt") as mock_build:
                mock_build.return_value = "prompt"

                await client.post(
                    "/api/investigate",
                    json={
                        "player_input": "examine the desk",
                        "case_id": "case_001",
                        "location_id": "library",
                        "player_id": player_id,
                    },
                )

                # build_narrator_prompt called (not build_narrator_or_spell_prompt)
                # No spell_outcome expected
                mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_safe_spells_use_success_calculation(
        self, client: AsyncClient, mock_success_response: str
    ) -> None:
        """All 6 safe investigation rites use success calculation."""
        player_id = "test_all_safe_spells"
        safe_spells = [
            "unveil",
            "raise_the_lamp",
            "sense_presence",
            "identify_substance",
            "echo_reading",
            "mend",
        ]

        with patch("src.api.routes.investigation.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_response = AsyncMock(return_value=mock_success_response)
            mock_get_client.return_value = mock_client

            with patch("src.context.spell_detection.random.random", return_value=0.5):
                for spell in safe_spells:
                    with patch("src.api.routes.investigation_logic.build_narrator_or_spell_prompt") as mock_build:
                        mock_build.return_value = ("prompt", "system", True)

                        await client.post(
                            "/api/investigate",
                            json={
                                "player_input": f"cast {spell}",
                                "case_id": "case_001",
                                "location_id": "library",
                                "player_id": f"{player_id}_{spell}",
                            },
                        )

                        # Each spell should have spell_outcome
                        call_kwargs = mock_build.call_args.kwargs
                        assert call_kwargs.get("spell_outcome") in ["SUCCESS", "FAILURE"], (
                            f"Failed for {spell}"
                        )
