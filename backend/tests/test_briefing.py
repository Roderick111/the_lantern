"""Tests for briefing system (Phase 3.5).

Tests:
- BriefingState model
- Briefing YAML structure
- Briefing endpoints (GET, POST question, POST complete)
- LLM fallback behavior
- Conversation history persistence
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.context.briefing import (
    build_graves_briefing_prompt,
    get_template_response,
)
from src.main import app
from src.state.player_state import BriefingState, PlayerState


@pytest.fixture
async def client() -> AsyncClient:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================================
# BriefingState Model Tests
# ============================================================================


class TestBriefingStateModel:
    """Tests for BriefingState model."""

    def test_briefing_state_creation(self) -> None:
        """Create BriefingState with defaults."""
        state = BriefingState(case_id="case_001")

        assert state.case_id == "case_001"
        assert state.briefing_completed is False
        assert state.conversation_history == []
        assert state.completed_at is None

    def test_briefing_state_add_question(self) -> None:
        """Add Q&A to conversation history."""
        state = BriefingState(case_id="case_001")

        state.add_question("What are base rates?", "Base rates are...")

        assert len(state.conversation_history) == 1
        assert state.conversation_history[0]["question"] == "What are base rates?"
        assert state.conversation_history[0]["answer"] == "Base rates are..."

    def test_briefing_state_add_multiple_questions(self) -> None:
        """Add multiple Q&As to conversation history."""
        state = BriefingState(case_id="case_001")

        state.add_question("Q1", "A1")
        state.add_question("Q2", "A2")
        state.add_question("Q3", "A3")

        assert len(state.conversation_history) == 3
        assert state.conversation_history[0]["question"] == "Q1"
        assert state.conversation_history[2]["question"] == "Q3"

    def test_briefing_state_mark_complete(self) -> None:
        """Mark briefing as completed."""
        state = BriefingState(case_id="case_001")

        state.mark_complete()

        assert state.briefing_completed is True
        assert state.completed_at is not None

    def test_briefing_state_mark_complete_sets_timestamp(self) -> None:
        """Completed_at is set when marked complete."""
        state = BriefingState(case_id="case_001")
        assert state.completed_at is None

        state.mark_complete()

        assert state.completed_at is not None


class TestPlayerStateBriefingIntegration:
    """Tests for PlayerState with BriefingState."""

    def test_player_state_briefing_state_default_none(self) -> None:
        """PlayerState.briefing_state is None by default."""
        state = PlayerState(case_id="case_001", current_location="library")

        assert state.briefing_state is None

    def test_player_state_get_briefing_state_creates(self) -> None:
        """get_briefing_state creates BriefingState if None."""
        state = PlayerState(case_id="case_001", current_location="library")

        briefing = state.get_briefing_state()

        assert briefing is not None
        assert briefing.case_id == "case_001"
        assert state.briefing_state is briefing

    def test_player_state_get_briefing_state_reuses(self) -> None:
        """get_briefing_state reuses existing BriefingState."""
        state = PlayerState(case_id="case_001", current_location="library")
        first = state.get_briefing_state()
        first.add_question("Q", "A")

        second = state.get_briefing_state()

        assert first is second
        assert len(second.conversation_history) == 1

    def test_player_state_mark_briefing_complete(self) -> None:
        """mark_briefing_complete creates state and marks complete."""
        state = PlayerState(case_id="case_001", current_location="library")

        state.mark_briefing_complete()

        assert state.briefing_state is not None
        assert state.briefing_state.briefing_completed is True


# ============================================================================
# LLM Prompt Tests
# ============================================================================


class TestGravesBriefingPrompt:
    """Tests for build_graves_briefing_prompt."""

    def test_build_prompt_includes_question(self) -> None:
        """Prompt includes player's question."""
        prompt = build_graves_briefing_prompt(
            question="What are base rates?",
            case_assignment="VICTIM: student",
            teaching_moment="Base rates are...",
            rationality_concept="base_rates",
            concept_description="Start with likely scenarios.",
            conversation_history=[],
        )

        assert "What are base rates?" in prompt

    def test_build_prompt_includes_case_assignment(self) -> None:
        """Prompt includes case assignment."""
        prompt = build_graves_briefing_prompt(
            question="Test",
            case_assignment="VICTIM: Third-year student",
            teaching_moment="Teaching",
            rationality_concept="base_rates",
            concept_description="Description",
            conversation_history=[],
        )

        assert "VICTIM: Third-year student" in prompt

    def test_build_prompt_includes_concept(self) -> None:
        """Prompt includes rationality concept."""
        prompt = build_graves_briefing_prompt(
            question="Test",
            case_assignment="Case",
            teaching_moment="Teaching",
            rationality_concept="base_rates",
            concept_description="Start with likely scenarios.",
            conversation_history=[],
        )

        assert "base_rates" in prompt
        assert "Start with likely scenarios" in prompt

    def test_build_prompt_includes_conversation_history(self) -> None:
        """Prompt includes prior conversation."""
        history = [
            {"question": "First Q?", "answer": "First A."},
            {"question": "Second Q?", "answer": "Second A."},
        ]

        prompt = build_graves_briefing_prompt(
            question="Third Q?",
            case_assignment="Case",
            teaching_moment="Teaching",
            rationality_concept="base_rates",
            concept_description="Description",
            conversation_history=history,
        )

        assert "First Q?" in prompt
        assert "First A." in prompt
        assert "Second Q?" in prompt
        assert "Second A." in prompt

    def test_build_prompt_empty_history(self) -> None:
        """Prompt handles empty conversation history."""
        prompt = build_graves_briefing_prompt(
            question="Test",
            case_assignment="Case",
            teaching_moment="Teaching",
            rationality_concept="base_rates",
            concept_description="Description",
            conversation_history=[],
        )

        assert "(None yet)" in prompt

    def test_build_prompt_limits_history_to_5(self) -> None:
        """Prompt limits history to last 5 exchanges."""
        history = [{"question": f"Q{i}", "answer": f"A{i}"} for i in range(10)]

        prompt = build_graves_briefing_prompt(
            question="Test",
            case_assignment="Case",
            teaching_moment="Teaching",
            rationality_concept="base_rates",
            concept_description="Description",
            conversation_history=history,
        )

        # Should only include last 5 (Q5-Q9)
        assert "Q5" in prompt
        assert "Q9" in prompt
        # Should not include first 5 (Q0-Q4)
        assert "Q0" not in prompt
        assert "Q4" not in prompt


class TestTemplateResponses:
    """Tests for template fallback responses."""

    def test_template_response_base_rates_question(self) -> None:
        """Template response for base rates question."""
        response = get_template_response("What are base rates?", "base_rates")

        assert "Base rates" in response or "base rates" in response.lower()

    def test_template_response_where_start(self) -> None:
        """Template response for 'where to start' question."""
        response = get_template_response("Where should I start?", "base_rates")

        assert "crime scene" in response.lower() or "start" in response.lower()

    def test_template_response_default(self) -> None:
        """Default template response for unknown questions."""
        response = get_template_response("Random unrelated question", "base_rates")

        assert "Trust nothing unseen" in response


# ============================================================================
# Briefing Endpoint Tests
# ============================================================================


class TestGetBriefingEndpoint:
    """Tests for GET /api/briefing/{case_id}."""

    @pytest.mark.asyncio
    async def test_get_briefing_success(self, client: AsyncClient) -> None:
        """GET briefing returns BriefingContent."""
        response = await client.get("/api/briefing/case_001")

        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == "case_001"
        assert "dossier" in data
        assert "teaching_questions" in data
        assert len(data["teaching_questions"]) > 0
        assert "prompt" in data["teaching_questions"][0]
        assert "choices" in data["teaching_questions"][0]
        assert "rationality_concept" in data
        assert "concept_description" in data
        assert "transition" in data

    @pytest.mark.asyncio
    async def test_get_briefing_includes_case_assignment(self, client: AsyncClient) -> None:
        """Briefing includes dossier with victim/location/time."""
        response = await client.get("/api/briefing/case_001")

        assert response.status_code == 200
        data = response.json()
        dossier = data["dossier"]
        assert "victim" in dossier
        assert "location" in dossier
        assert "time" in dossier

    @pytest.mark.asyncio
    async def test_get_briefing_includes_teaching_question(self, client: AsyncClient) -> None:
        """Briefing includes teaching question about base rates with choices."""
        response = await client.get("/api/briefing/case_001")

        assert response.status_code == 200
        data = response.json()
        teaching_qs = data["teaching_questions"]
        assert len(teaching_qs) > 0
        teaching_q = teaching_qs[0]
        # Has prompt and choices
        assert "prompt" in teaching_q
        assert "choices" in teaching_q
        # Has at least one choice
        assert len(teaching_q["choices"]) > 0
        # Each choice has id, text, response
        for choice in teaching_q["choices"]:
            assert "id" in choice
            assert "text" in choice
            assert "response" in choice

    @pytest.mark.asyncio
    async def test_get_briefing_includes_transition(self, client: AsyncClient) -> None:
        """Briefing includes transition with 'Trust nothing unseen'."""
        response = await client.get("/api/briefing/case_001")

        assert response.status_code == 200
        data = response.json()
        assert "Trust nothing unseen" in data["transition"]

    @pytest.mark.asyncio
    async def test_get_briefing_404_invalid_case(self, client: AsyncClient) -> None:
        """404 for nonexistent case."""
        response = await client.get("/api/briefing/nonexistent_case")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_briefing_rationality_concept(self, client: AsyncClient) -> None:
        """Briefing includes rationality_concept ID."""
        response = await client.get("/api/briefing/case_001")

        assert response.status_code == 200
        data = response.json()
        assert data["rationality_concept"] == "physical_evidence_primacy"

    @pytest.mark.asyncio
    async def test_get_briefing_includes_completed_flag_false_by_default(
        self, client: AsyncClient
    ) -> None:
        """GET briefing includes briefing_completed flag, defaults to false."""
        response = await client.get("/api/briefing/case_001?player_id=test_new_player_xyz")

        assert response.status_code == 200
        data = response.json()
        assert "briefing_completed" in data
        assert data["briefing_completed"] is False

    @pytest.mark.asyncio
    async def test_get_briefing_completed_flag_true_after_complete(
        self, client: AsyncClient
    ) -> None:
        """GET briefing returns briefing_completed=true after completing briefing."""
        player_id = "test_completed_flag_check"

        # First, complete the briefing
        complete_response = await client.post(
            f"/api/briefing/case_001/complete?player_id={player_id}"
        )
        assert complete_response.status_code == 200

        # Now GET briefing should return briefing_completed=true
        response = await client.get(f"/api/briefing/case_001?player_id={player_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["briefing_completed"] is True


class TestAskBriefingQuestionEndpoint:
    """Tests for POST /api/briefing/{case_id}/question."""

    @pytest.mark.asyncio
    async def test_ask_question_success(self, client: AsyncClient) -> None:
        """POST question returns Graves's response."""
        response = await client.post(
            "/api/briefing/case_001/question",
            json={"question": "What are base rates?", "player_id": "test_ask_q1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    @pytest.mark.asyncio
    async def test_ask_question_saves_history(self, client: AsyncClient) -> None:
        """Question/answer saved to conversation history."""
        player_id = "test_history_persist"

        # Clean up any leftover state from previous runs
        from src.state.persistence import delete_player_save

        delete_player_save("case_001", player_id, "autosave")

        # Ask first question
        await client.post(
            "/api/briefing/case_001/question",
            json={"question": "First question?", "player_id": player_id},
        )

        # Ask second question
        await client.post(
            "/api/briefing/case_001/question",
            json={"question": "Second question?", "player_id": player_id},
        )

        # Load state to verify history
        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")

        assert state is not None
        assert state.briefing_state is not None
        assert len(state.briefing_state.conversation_history) == 2

    @pytest.mark.asyncio
    async def test_ask_question_404_invalid_case(self, client: AsyncClient) -> None:
        """404 for question on nonexistent case."""
        response = await client.post(
            "/api/briefing/nonexistent_case/question",
            json={"question": "Test?", "player_id": "test"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_ask_question_creates_briefing_state(self, client: AsyncClient) -> None:
        """First question creates BriefingState in PlayerState."""
        player_id = "test_create_state"

        await client.post(
            "/api/briefing/case_001/question",
            json={"question": "Question?", "player_id": player_id},
        )

        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")

        assert state is not None
        assert state.briefing_state is not None
        assert state.briefing_state.case_id == "case_001"

    @pytest.mark.asyncio
    async def test_ask_question_llm_fallback(self, client: AsyncClient) -> None:
        """Uses template fallback when LLM fails."""
        with patch(
            "src.api.llm_client.get_client",
            side_effect=Exception("LLM unavailable"),
        ):
            response = await client.post(
                "/api/briefing/case_001/question",
                json={
                    "question": "What are base rates?",
                    "player_id": "test_fallback",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0


class TestCompleteBriefingEndpoint:
    """Tests for POST /api/briefing/{case_id}/complete."""

    @pytest.mark.asyncio
    async def test_complete_briefing_success(self, client: AsyncClient) -> None:
        """POST complete marks briefing as completed."""
        player_id = "test_complete"

        response = await client.post(f"/api/briefing/case_001/complete?player_id={player_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_complete_briefing_sets_completed_flag(self, client: AsyncClient) -> None:
        """Complete sets briefing_completed=True in state."""
        player_id = "test_complete_flag"

        await client.post(f"/api/briefing/case_001/complete?player_id={player_id}")

        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")

        assert state is not None
        assert state.briefing_state is not None
        assert state.briefing_state.briefing_completed is True

    @pytest.mark.asyncio
    async def test_complete_briefing_sets_completed_at(self, client: AsyncClient) -> None:
        """Complete sets completed_at timestamp."""
        player_id = "test_complete_timestamp"

        await client.post(f"/api/briefing/case_001/complete?player_id={player_id}")

        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")

        assert state is not None
        assert state.briefing_state is not None
        assert state.briefing_state.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_briefing_404_invalid_case(self, client: AsyncClient) -> None:
        """404 for complete on nonexistent case."""
        response = await client.post("/api/briefing/nonexistent_case/complete?player_id=test")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_complete_briefing_preserves_history(self, client: AsyncClient) -> None:
        """Complete preserves conversation history."""
        player_id = f"test_complete_history_{uuid4()}"

        # Ask some questions first
        await client.post(
            "/api/briefing/case_001/question",
            json={"question": "Q1?", "player_id": player_id},
        )
        await client.post(
            "/api/briefing/case_001/question",
            json={"question": "Q2?", "player_id": player_id},
        )

        # Complete briefing
        await client.post(f"/api/briefing/case_001/complete?player_id={player_id}")

        from src.state.persistence import load_player_state

        state = load_player_state("case_001", player_id, "autosave")

        assert state is not None
        assert state.briefing_state is not None
        assert len(state.briefing_state.conversation_history) == 2
        assert state.briefing_state.briefing_completed is True


# ============================================================================
# YAML Structure Tests
# ============================================================================


class TestBriefingYamlStructure:
    """Tests for briefing section in case YAML."""

    @pytest.mark.asyncio
    async def test_yaml_has_briefing_section(self, client: AsyncClient) -> None:
        """case_001.yaml has briefing section."""
        response = await client.get("/api/briefing/case_001")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_yaml_case_assignment_format(self, client: AsyncClient) -> None:
        """dossier has victim/location/time format."""
        response = await client.get("/api/briefing/case_001")
        data = response.json()

        dossier = data["dossier"]
        # Check for key elements
        assert len(dossier["victim"]) > 0
        assert len(dossier["location"]) > 0
        assert len(dossier["time"]) > 0

    @pytest.mark.asyncio
    async def test_yaml_teaching_question_content(self, client: AsyncClient) -> None:
        """teaching_question teaches concept via choices."""
        response = await client.get("/api/briefing/case_001")
        data = response.json()

        teaching_qs = data["teaching_questions"]
        assert len(teaching_qs) > 0
        teaching_q = teaching_qs[0]
        # Should have prompt and choices
        assert len(teaching_q["prompt"]) > 0
        assert len(teaching_q["choices"]) > 0

    @pytest.mark.asyncio
    async def test_yaml_concept_description_present(self, client: AsyncClient) -> None:
        """concept_description summarizes the concept."""
        response = await client.get("/api/briefing/case_001")
        data = response.json()

        assert len(data["concept_description"]) > 10

    @pytest.mark.asyncio
    async def test_yaml_transition_has_trust_nothing_unseen(self, client: AsyncClient) -> None:
        """transition ends with 'Trust nothing unseen'."""
        response = await client.get("/api/briefing/case_001")
        data = response.json()

        assert "Trust nothing unseen" in data["transition"]


# ============================================================================
# Briefing Context Tests (Phase 3.8)
# ============================================================================


class TestBriefingContext:
    """Tests for briefing_context functionality (Phase 3.8)."""

    def test_briefing_context_loaded_from_yaml(self) -> None:
        """briefing_context loads from case YAML."""
        from src.case_store.loader import load_case

        case_data = load_case("case_001")
        case_section = case_data.get("case", case_data)
        briefing_context = case_section.get("briefing_context")

        assert briefing_context is not None
        assert "witnesses" in briefing_context
        assert "suspects" in briefing_context
        assert "location" in briefing_context
        assert "case_overview" in briefing_context

    def test_briefing_context_has_witnesses(self) -> None:
        """briefing_context contains witness info."""
        from src.case_store.loader import load_case

        case_data = load_case("case_001")
        case_section = case_data.get("case", case_data)
        briefing_context = case_section.get("briefing_context", {})
        witnesses = briefing_context.get("witnesses", [])

        assert len(witnesses) >= 2
        # Check first witness has required fields
        elena = next((w for w in witnesses if "Elena" in w.get("name", "")), None)
        assert elena is not None
        assert "personality" in elena
        assert "background" in elena
        assert "general_knowledge" in elena

    def test_briefing_context_no_secrets(self) -> None:
        """briefing_context does NOT contain secrets."""
        from src.case_store.loader import load_case

        case_data = load_case("case_001")
        case_section = case_data.get("case", case_data)
        briefing_context = case_section.get("briefing_context", {})

        # Convert to string to search for secret keywords
        context_str = str(briefing_context).lower()

        # Should NOT contain secret triggers or culprit reveal
        assert "saw_cassian" not in context_str
        assert "borrowed_restricted" not in context_str
        assert "culprit" not in context_str
        assert "guilty" not in context_str

    def test_briefing_context_no_lies(self) -> None:
        """briefing_context does NOT contain lie information."""
        from src.case_store.loader import load_case

        case_data = load_case("case_001")
        case_section = case_data.get("case", case_data)
        briefing_context = case_section.get("briefing_context", {})
        witnesses = briefing_context.get("witnesses", [])

        for witness in witnesses:
            # Witnesses should NOT have 'lies' or 'secrets' fields in context
            assert "lies" not in witness
            assert "secrets" not in witness

    def test_prompt_includes_witness_summary(self) -> None:
        """Prompt includes witness summary when briefing_context provided."""
        briefing_context = {
            "witnesses": [
                {
                    "name": "Elena Marsh",
                    "personality": "Brilliant student",
                    "background": "Top of class",
                }
            ],
            "suspects": ["Elena Marsh"],
            "location": {"name": "Library", "description": "Big room"},
            "case_overview": "Student found held in stillness",
        }

        prompt = build_graves_briefing_prompt(
            question="Who are the witnesses?",
            case_assignment="Case details",
            teaching_moment="Teaching",
            rationality_concept="base_rates",
            concept_description="Description",
            conversation_history=[],
            briefing_context=briefing_context,
        )

        assert "Elena Marsh" in prompt
        assert "Brilliant student" in prompt
        assert "Top of class" in prompt

    def test_prompt_includes_suspect_list(self) -> None:
        """Prompt includes suspect list when briefing_context provided."""
        briefing_context = {
            "witnesses": [],
            "suspects": [
                "Elena Marsh (present)",
                "Cassian Thorne (nearby)",
            ],
            "location": {"name": "Library", "description": "Big room"},
            "case_overview": "Student found held in stillness",
        }

        prompt = build_graves_briefing_prompt(
            question="Who are suspects?",
            case_assignment="Case details",
            teaching_moment="Teaching",
            rationality_concept="base_rates",
            concept_description="Description",
            conversation_history=[],
            briefing_context=briefing_context,
        )

        assert "Elena Marsh" in prompt
        assert "Cassian Thorne" in prompt

    def test_prompt_includes_rationality_context(self) -> None:
        """Prompt includes rationality principles when context provided."""
        briefing_context = {
            "witnesses": [],
            "suspects": [],
            "location": {"name": "Library", "description": "Big room"},
            "case_overview": "Student found held in stillness",
        }

        prompt = build_graves_briefing_prompt(
            question="What is confirmation bias?",
            case_assignment="Case details",
            teaching_moment="Teaching",
            rationality_concept="base_rates",
            concept_description="Description",
            conversation_history=[],
            briefing_context=briefing_context,
        )

        # Should include rationality guide
        assert "Confirmation Bias" in prompt or "confirmation bias" in prompt.lower()
        assert "Base Rates" in prompt or "base rates" in prompt.lower()

    def test_prompt_handles_missing_context(self) -> None:
        """Prompt works without briefing_context (backward compat)."""
        prompt = build_graves_briefing_prompt(
            question="Test question",
            case_assignment="Case details",
            teaching_moment="Teaching",
            rationality_concept="base_rates",
            concept_description="Description",
            conversation_history=[],
            briefing_context=None,
        )

        # Should still work, just without context section
        assert "Test question" in prompt
        assert "Alastor" in prompt or "Graves" in prompt

    def test_prompt_handles_empty_context(self) -> None:
        """Prompt works with empty briefing_context dict."""
        prompt = build_graves_briefing_prompt(
            question="Test question",
            case_assignment="Case details",
            teaching_moment="Teaching",
            rationality_concept="base_rates",
            concept_description="Description",
            conversation_history=[],
            briefing_context={},
        )

        # Should still work
        assert "Test question" in prompt


class TestRationalityContextModule:
    """Tests for rationality_context module."""

    def test_get_rationality_context_returns_string(self) -> None:
        """get_rationality_context returns non-empty string."""
        from src.context.rationality_context import get_rationality_context

        context = get_rationality_context()

        assert isinstance(context, str)
        assert len(context) > 100  # Should be substantial

    def test_rationality_context_contains_key_concepts(self) -> None:
        """Rationality context includes key concepts."""
        from src.context.rationality_context import get_rationality_context

        context = get_rationality_context()

        # Should contain key rationality concepts
        assert "Base Rates" in context or "base rates" in context.lower()
        assert "Confirmation Bias" in context or "confirmation bias" in context.lower()
        assert "Correlation" in context or "correlation" in context.lower()
        assert "Causation" in context or "causation" in context.lower()
        assert "Burden of Proof" in context or "burden of proof" in context.lower()
