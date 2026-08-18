"""Tests for Phase 4.1: Matthew LLM-powered spirit companion.

Tests:
- Matthew LLM prompt building
- Trust system state
- Auto-comment endpoint (mocked LLM)
- Direct chat endpoint (mocked LLM)
- Fallback behavior
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.context.matthew_llm import (
    MATTHEW_MAX_TOKENS,
    build_context_prompt,
    build_matthew_system_prompt,
    check_matthew_should_comment,
    generate_matthew_response,
    get_matthew_fallback_response,
)
from src.main import app
from src.state.player_state import MatthewCompanionState


class TestMatthewSystemPrompt:
    """Test Matthew character prompt building."""

    def test_prompt_includes_trust_level(self) -> None:
        """Prompt includes trust percentage."""
        prompt = build_matthew_system_prompt(trust_level=0.5, mode="helpful")
        assert "40-70%" in prompt or "Trust" in prompt

    def test_generation_budget_is_400_tokens(self) -> None:
        assert MATTHEW_MAX_TOKENS == 400

    @pytest.mark.asyncio
    async def test_generation_disables_reasoning(self) -> None:
        client = AsyncMock()
        client.get_response.return_value = "The frost points inward. Follow its center."

        with patch("src.context.matthew_llm.get_client", return_value=client):
            await generate_matthew_response({}, [], 0.5, [], mode="helpful")

        assert client.get_response.call_args.kwargs["max_tokens"] == 400
        assert client.get_response.call_args.kwargs["disable_reasoning"] is True

    def test_prompt_helpful_mode(self) -> None:
        """Helpful mode includes Socratic question guidance."""
        prompt = build_matthew_system_prompt(trust_level=0.5, mode="helpful")
        assert "HELPFUL" in prompt
        assert "Socratic" in prompt or "question" in prompt.lower()

    def test_prompt_misleading_mode(self) -> None:
        """Misleading mode includes plausible wrong assertion guidance."""
        prompt = build_matthew_system_prompt(trust_level=0.5, mode="misleading")
        assert "MISLEADING" in prompt
        assert "plausible" in prompt.lower() or "wrong" in prompt.lower()

    def test_prompt_includes_rule_10(self) -> None:
        """Prompt includes critical Rule #10 (no psychology explanation)."""
        prompt = build_matthew_system_prompt(trust_level=0.5, mode="helpful")
        assert "RULE #10" in prompt or "PARAMOUNT" in prompt
        assert "psychology" in prompt.lower()

    def test_trust_level_zero_no_personal_stories(self) -> None:
        """Trust 0% prevents personal stories."""
        prompt = build_matthew_system_prompt(trust_level=0.0, mode="helpful")
        assert "NO personal stories" in prompt or "0-30%" in prompt

    def test_trust_level_high_allows_sharing(self) -> None:
        """Trust 80%+ allows deeper sharing."""
        prompt = build_matthew_system_prompt(trust_level=0.9, mode="helpful")
        assert "80-100%" in prompt or "deeper" in prompt.lower()


class TestContextPrompt:
    """Test context prompt building."""

    def test_context_includes_case_facts(self) -> None:
        """Context includes victim, location, suspects, witnesses."""
        case_context = {
            "victim": "Third-year student (held in stillness)",
            "location": "Blackwood Collegiate Library",
            "suspects": ["Elena Marsh", "Cassian Thorne"],
            "witnesses": ["Miss Hawthorne"],
        }
        evidence = []

        prompt = build_context_prompt(case_context, evidence, [])

        assert "Third-year student" in prompt
        assert "Blackwood Collegiate Library" in prompt
        assert "Elena Marsh" in prompt or "Cassian Thorne" in prompt
        assert "Miss Hawthorne" in prompt

    def test_context_includes_evidence(self) -> None:
        """Context includes discovered evidence."""
        case_context = {"victim": "Test", "location": "Test", "suspects": [], "witnesses": []}
        evidence = [
            {"name": "Frost Pattern", "description": "Ice on window"},
            {"name": "Focus Signature", "description": "Traces of magic"},
        ]

        prompt = build_context_prompt(case_context, evidence, [])

        assert "Frost Pattern" in prompt
        assert "Focus Signature" in prompt

    def test_context_handles_empty_evidence(self) -> None:
        """Context handles no evidence discovered."""
        case_context = {"victim": "Test", "location": "Test", "suspects": [], "witnesses": []}
        evidence = []

        prompt = build_context_prompt(case_context, evidence, [])

        assert "None discovered yet" in prompt

    def test_context_includes_user_message(self) -> None:
        """Context includes player's direct question."""
        case_context = {"victim": "Test", "location": "Test", "suspects": [], "witnesses": []}
        evidence = []
        user_message = "Matthew, should I trust Elena?"

        prompt = build_context_prompt(case_context, evidence, [], user_message)

        assert "should I trust Elena" in prompt


class TestTrustSystem:
    """Test MatthewCompanionState trust system."""

    def test_initial_trust_zero(self) -> None:
        """New MatthewCompanionState starts with trust 0."""
        state = MatthewCompanionState(case_id="test")
        assert state.trust_level == 0.0
        assert state.get_trust_percentage() == 0

    def test_increment_trust(self) -> None:
        """Trust increments correctly."""
        state = MatthewCompanionState(case_id="test")
        state.increment_trust(0.1)
        assert state.trust_level == 0.1
        assert state.get_trust_percentage() == 10

    def test_trust_caps_at_one(self) -> None:
        """Trust cannot exceed 1.0."""
        state = MatthewCompanionState(case_id="test", trust_level=0.95)
        state.increment_trust(0.2)
        assert state.trust_level == 1.0
        assert state.get_trust_percentage() == 100

    def test_mark_case_complete_increases_trust(self) -> None:
        """Completing a case increases trust by 10%."""
        state = MatthewCompanionState(case_id="test")
        state.mark_case_complete()
        assert state.cases_completed == 1
        assert state.trust_level == 0.1

    def test_calculate_trust_from_cases(self) -> None:
        """Trust calculation from case count is correct."""
        state = MatthewCompanionState(case_id="test", cases_completed=5)
        trust = state.calculate_trust_from_cases()
        assert trust == 0.5  # 5 cases * 10% = 50%

    def test_add_matthew_comment(self) -> None:
        """Adding Matthew comment updates state."""
        state = MatthewCompanionState(case_id="test")
        state.add_matthew_comment("What about Cassian?", "Check his alibi first.")

        assert state.total_comments == 1
        assert len(state.conversation_history) == 1
        assert state.conversation_history[0]["user"] == "What about Cassian?"
        assert state.conversation_history[0]["matthew"] == "Check his alibi first."
        assert state.last_comment_at is not None


class TestShouldComment:
    """Test auto-comment probability."""

    @pytest.mark.asyncio
    async def test_critical_always_comments(self) -> None:
        """Critical evidence always triggers comment."""
        result = await check_matthew_should_comment(is_critical=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_non_critical_has_30_percent_chance(self) -> None:
        """Non-critical has ~30% chance (statistical test)."""
        # Run 1000 times and check roughly 30% are True
        results = [await check_matthew_should_comment(is_critical=False) for _ in range(1000)]
        true_count = sum(results)
        # Should be roughly 300 +/- 50 (allowing for variance)
        assert 200 < true_count < 400


class TestFallbackResponses:
    """Test template fallback responses."""

    def test_helpful_fallback(self) -> None:
        """Helpful mode returns Socratic question."""
        response = get_matthew_fallback_response("helpful", 0)
        assert "?" in response  # Should be a question

    def test_misleading_fallback(self) -> None:
        """Misleading mode returns confident assertion."""
        response = get_matthew_fallback_response("misleading", 0)
        # Should be a statement, not a question (or at least confident)
        assert len(response) > 20

    def test_fallback_varies_by_evidence_count(self) -> None:
        """Different evidence counts give different responses."""
        r1 = get_matthew_fallback_response("helpful", 0)
        r2 = get_matthew_fallback_response("helpful", 1)
        r3 = get_matthew_fallback_response("helpful", 2)

        # At least 2 of 3 should be different
        responses = {r1, r2, r3}
        assert len(responses) >= 2


class TestMatthewAutoCommentEndpoint:
    """Test POST /api/case/{case_id}/matthew/auto-comment endpoint."""

    @pytest.mark.asyncio
    async def test_auto_comment_case_not_found(self) -> None:
        """Returns 404 for missing case."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/case/nonexistent/matthew/auto-comment",
                json={"is_critical": True},
            )
            assert response.status_code == 404
            assert "Case not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_auto_comment_matthew_stays_quiet(self) -> None:
        """Returns 204 when Matthew chooses not to comment (mocked 0% chance)."""
        transport = ASGITransport(app=app)

        with patch(
            "src.context.matthew_llm.check_matthew_should_comment",
            new_callable=AsyncMock,
            return_value=False,
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/case/case_001/matthew/auto-comment",
                    json={"is_critical": False},
                )
                assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_auto_comment_success_with_mocked_llm(self) -> None:
        """Returns Matthew response with mocked LLM."""
        transport = ASGITransport(app=app)

        mock_response = ("Check the frost pattern direction.", "helpful")

        with (
            patch(
                "src.context.matthew_llm.check_matthew_should_comment",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "src.context.matthew_llm.generate_matthew_response",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/case/case_001/matthew/auto-comment",
                    json={"is_critical": True},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["text"] == "Check the frost pattern direction."
                assert "auto_helpful" in data["mode"]
                assert data["trust_level"] >= 0

    @pytest.mark.asyncio
    async def test_auto_comment_fallback_on_llm_failure(self) -> None:
        """Falls back to template when LLM fails."""
        transport = ASGITransport(app=app)

        with (
            patch(
                "src.context.matthew_llm.check_matthew_should_comment",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "src.context.matthew_llm.generate_matthew_response",
                new_callable=AsyncMock,
                side_effect=Exception("LLM failed"),
            ),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/case/case_001/matthew/auto-comment",
                    json={"is_critical": True},
                )
                # Should still return 200 with fallback
                assert response.status_code == 200
                data = response.json()
                assert len(data["text"]) > 0  # Got a fallback response


class TestMatthewDirectChatEndpoint:
    """Test POST /api/case/{case_id}/matthew/chat endpoint."""

    @pytest.mark.asyncio
    async def test_direct_chat_case_not_found(self) -> None:
        """Returns 404 for missing case."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/case/nonexistent/matthew/chat",
                json={"message": "Matthew, what do you think?"},
            )
            assert response.status_code == 404
            assert "Case not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_direct_chat_empty_message(self) -> None:
        """Rejects empty message."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/case/case_001/matthew/chat",
                json={"message": ""},
            )
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_direct_chat_success_with_mocked_llm(self) -> None:
        """Returns Matthew response with mocked LLM."""
        transport = ASGITransport(app=app)

        mock_response = ("Trust the evidence, not your gut feeling.", "misleading")

        with patch(
            "src.context.matthew_llm.generate_matthew_response",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/case/case_001/matthew/chat",
                    json={"message": "Matthew, should I trust Elena?"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["text"] == "Trust the evidence, not your gut feeling."
                assert "direct_chat_misleading" in data["mode"]
                assert data["trust_level"] >= 0

    @pytest.mark.asyncio
    async def test_direct_chat_always_responds(self) -> None:
        """Direct chat always responds (unlike auto-comment)."""
        transport = ASGITransport(app=app)

        mock_response = ("Good question. What does the evidence say?", "helpful")

        with patch(
            "src.context.matthew_llm.generate_matthew_response",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Call multiple times - should always get 200
                for _ in range(3):
                    response = await client.post(
                        "/api/case/case_001/matthew/chat",
                        json={"message": "Matthew?"},
                    )
                    assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_direct_chat_fallback_on_llm_failure(self) -> None:
        """Falls back to template when LLM fails."""
        transport = ASGITransport(app=app)

        with patch(
            "src.context.matthew_llm.generate_matthew_response",
            new_callable=AsyncMock,
            side_effect=Exception("LLM failed"),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/case/case_001/matthew/chat",
                    json={"message": "Matthew, help me out here."},
                )
                # Should still return 200 with fallback
                assert response.status_code == 200
                data = response.json()
                assert len(data["text"]) > 0  # Got a fallback response


class TestPhase43BehavioralPatterns:
    """Test Phase 4.3: Matthew personality enhancement patterns in prompt."""

    def test_trust_0_helpful_contains_verification_questions(self) -> None:
        """Trust 0%, helpful mode includes verification question templates."""
        prompt = build_matthew_system_prompt(trust_level=0.0, mode="helpful")
        # Should include Case #1 failure reference (witness coordination)
        assert "witnesses" in prompt.lower() or "coordinate" in prompt.lower()
        assert "verify" in prompt.lower()
        # Should be in helpful mode
        assert "HELPFUL" in prompt

    def test_trust_0_misleading_contains_misapplied_principles(self) -> None:
        """Trust 0%, misleading mode includes confident misapplication structure."""
        prompt = build_matthew_system_prompt(trust_level=0.0, mode="misleading")
        # Should include misapplied principle structure
        assert "MISLEADING" in prompt
        assert "Corroboration" in prompt or "Physical evidence" in prompt
        # Should have reassurance tone
        assert "solid" in prompt.lower() or "trust" in prompt.lower()

    def test_trust_50_contains_doubling_down_pattern(self) -> None:
        """Trust 50% prompt includes Alpha doubling down pattern."""
        prompt = build_matthew_system_prompt(trust_level=0.5, mode="helpful")
        assert "Doubling Down" in prompt or "Alpha" in prompt
        assert "I KNOW" in prompt or "double down" in prompt.lower()

    def test_trust_90_contains_full_candlewick_details(self) -> None:
        """Trust 90% prompt includes full Candlewick séance acknowledgment."""
        prompt = build_matthew_system_prompt(trust_level=0.9, mode="helpful")
        assert "Candlewick" in prompt
        assert "ward" in prompt.lower() or "circle" in prompt.lower()
        assert "I don't know" in prompt or "NOTICED" in prompt

    def test_trust_90_contains_dark_humor_section(self) -> None:
        """Trust 90% prompt includes dark humor templates."""
        prompt = build_matthew_system_prompt(trust_level=0.9, mode="helpful")
        assert "DARK HUMOR" in prompt or "dark humor" in prompt.lower()
        assert "ward" in prompt.lower() or "circle" in prompt.lower() or "theatre" in prompt.lower()

    def test_fairweather_references_differ_by_trust(self) -> None:
        """Fairweather's patter decreases from trust 30% to 80%."""
        prompt_low = build_matthew_system_prompt(trust_level=0.2, mode="helpful")
        prompt_high = build_matthew_system_prompt(trust_level=0.9, mode="helpful")

        assert "Fairweather" in prompt_low
        low_trust_section = prompt_low[prompt_low.find("TRUST 0-30%") : prompt_low.find("VOICE")]
        assert "patter" in low_trust_section.lower() or "trade" in low_trust_section.lower()

        assert "Fairweather sold" in prompt_high or "scenery" in prompt_high.lower()

    def test_voice_progression_eager_at_low_trust(self) -> None:
        """Trust 0-30% has eager showman voice tone."""
        prompt = build_matthew_system_prompt(trust_level=0.2, mode="helpful")
        voice_section = prompt[prompt.find("VOICE") : prompt.find("════")]
        assert "Eager" in voice_section or "showman" in voice_section.lower()

    def test_voice_progression_wise_at_high_trust(self) -> None:
        """Trust 80%+ has wise/questioning voice tone."""
        prompt = build_matthew_system_prompt(trust_level=0.9, mode="helpful")
        # Should include wisdom markers
        assert "Wisdom" in prompt or "I don't know" in prompt

    def test_relationship_markers_present(self) -> None:
        """Prompt includes relationship markers section."""
        prompt = build_matthew_system_prompt(trust_level=0.5, mode="helpful")
        # Should have relationship section
        assert "RELATIONSHIPS" in prompt or "TO PLAYER" in prompt
        # Should have Graves marker
        assert "Graves" in prompt

    def test_rule_10_enforced_no_psychology_explanations(self) -> None:
        """Rule #10 enforced: no psychology explanation examples."""
        prompt = build_matthew_system_prompt(trust_level=0.5, mode="helpful")
        # Should have CANNOT say examples (optimized from FORBIDDEN)
        assert "CANNOT say" in prompt or "❌" in prompt
        assert "defensive because" in prompt.lower() or "trauma" in prompt.lower()
        # Should have INSTEAD behavior guidance (optimized from CORRECT)
        assert "INSTEAD" in prompt or "Show through" in prompt

    def test_mode_helpful_has_candlewick_failures(self) -> None:
        """Helpful mode references Matthew's séance and circus failures."""
        prompt = build_matthew_system_prompt(trust_level=0.5, mode="helpful")
        assert "Candlewick" in prompt or "planted" in prompt.lower()

    def test_mode_misleading_sounds_professional(self) -> None:
        """Misleading mode structure sounds professional (not obviously wrong)."""
        prompt = build_matthew_system_prompt(trust_level=0.5, mode="misleading")
        # Should have professional-sounding structure
        assert "Principle" in prompt or "principle" in prompt
        # Should have reassurance language
        assert "experienced" in prompt.lower() or "I've seen" in prompt

    def test_self_aware_deflection_pattern_present(self) -> None:
        """Beta pattern (self-aware deflection) included with 5% guidance."""
        prompt = build_matthew_system_prompt(trust_level=0.5, mode="helpful")
        # Should include Beta pattern
        assert "Beta" in prompt or "Self-Aware Deflection" in prompt
        # Should have 5% frequency guidance
        assert "5%" in prompt

    def test_prompt_under_token_budget(self) -> None:
        """Full prompt stays under ~3000 token budget (Phase 4.3+ enhanced)."""
        prompt = build_matthew_system_prompt(trust_level=0.9, mode="helpful")
        # Rough estimate: 1 token ~= 4 characters for English text
        # Phase 4.3 enhanced BACKGROUND: ~2400 tokens (~9500 chars)
        # Still well within Claude Haiku's 200K context window
        assert len(prompt) < 12000  # ~3000 tokens with buffer
