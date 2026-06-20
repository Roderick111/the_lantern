"""Tests for mentor feedback generation."""

import pytest

from src.context.mentor import (
    _build_fallacies_detailed,
    _determine_quality,
    _generate_adaptive_hint,
    _generate_critique,
    _generate_praise,
    build_mentor_feedback,
    get_wrong_suspect_response,
)


class TestBuildMentorFeedback:
    """Tests for build_mentor_feedback function."""

    def test_correct_verdict_excellent_score(self) -> None:
        """Correct verdict with excellent reasoning."""
        feedback = build_mentor_feedback(
            correct=True,
            score=95,
            fallacies=[],
            reasoning="The focus signature and frost pattern prove Cassian did it.",
            accused_id="cassian",
            solution={"culprit": "wisp", "key_evidence": ["focus_signature", "frost_pattern"]},
            feedback_templates={"fallacies": {}},
            attempts_remaining=9,
        )

        assert feedback["score"] == 95
        assert feedback["quality"] == "excellent"
        assert feedback["hint"] is None  # No hint for correct verdict
        assert "cassian" in feedback["analysis"]

    def test_incorrect_verdict_with_hint(self) -> None:
        """Incorrect verdict gets adaptive hint."""
        feedback = build_mentor_feedback(
            correct=False,
            score=40,
            fallacies=["confirmation_bias"],
            reasoning="She was there so she did it.",
            accused_id="elena",
            solution={"culprit": "wisp", "key_evidence": ["frost_pattern"]},
            feedback_templates={
                "fallacies": {"confirmation_bias": {"description": "test", "example": "ex"}}
            },
            attempts_remaining=7,
        )

        assert feedback["score"] == 40
        assert feedback["quality"] == "poor"
        assert feedback["hint"] is not None  # Gets hint for incorrect verdict
        assert "elena" in feedback["analysis"]

    def test_feedback_includes_fallacies(self) -> None:
        """Feedback includes detailed fallacies."""
        feedback = build_mentor_feedback(
            correct=False,
            score=30,
            fallacies=["confirmation_bias", "authority_bias"],
            reasoning="The witness said she did it.",
            accused_id="elena",
            solution={"culprit": "wisp"},
            feedback_templates={
                "fallacies": {
                    "confirmation_bias": {"description": "CB desc", "example": "CB ex"},
                    "authority_bias": {"description": "AB desc", "example": "AB ex"},
                }
            },
            attempts_remaining=5,
        )

        assert len(feedback["fallacies_detected"]) == 2
        assert feedback["fallacies_detected"][0]["name"] == "confirmation_bias"
        assert feedback["fallacies_detected"][0]["description"] == "CB desc"


class TestDetermineQuality:
    """Tests for _determine_quality helper."""

    def test_excellent_threshold(self) -> None:
        """Score >= 90 is excellent."""
        assert _determine_quality(90) == "excellent"
        assert _determine_quality(100) == "excellent"

    def test_good_threshold(self) -> None:
        """Score 75-89 is good."""
        assert _determine_quality(75) == "good"
        assert _determine_quality(89) == "good"

    def test_fair_threshold(self) -> None:
        """Score 60-74 is fair."""
        assert _determine_quality(60) == "fair"
        assert _determine_quality(74) == "fair"

    def test_poor_threshold(self) -> None:
        """Score 40-59 is poor."""
        assert _determine_quality(40) == "poor"
        assert _determine_quality(59) == "poor"

    def test_failing_threshold(self) -> None:
        """Score < 40 is failing."""
        assert _determine_quality(39) == "failing"
        assert _determine_quality(0) == "failing"


class TestGeneratePraise:
    """Tests for _generate_praise helper (Graves-style harsh feedback)."""

    def test_praise_excellent_score(self) -> None:
        """High score gets competent Lantern Inspector praise."""
        praise = _generate_praise(95, True, [])
        assert "Outstanding" in praise or "competent Lantern Inspector" in praise

    def test_praise_good_score(self) -> None:
        """Good score gets acknowledgment."""
        praise = _generate_praise(80, True, [])
        assert "Good work" in praise or "cited" in praise

    def test_praise_adequate_score(self) -> None:
        """Adequate score (60-74) gets barely acceptable feedback."""
        praise = _generate_praise(65, True, [])
        assert "Adequate" in praise or "barely" in praise

    def test_praise_correct_with_fallacies(self) -> None:
        """Correct but with fallacies gets harsh feedback about luck."""
        praise = _generate_praise(55, True, ["confirmation_bias"])
        assert "luck" in praise.lower() or "wrong path" in praise.lower()

    def test_praise_incorrect(self) -> None:
        """Incorrect gets harsh embarrassing feedback."""
        praise = _generate_praise(50, False, [])
        assert "Try harder" in praise or "embarrassing" in praise


class TestGenerateCritique:
    """Tests for _generate_critique helper (Graves-style harsh feedback)."""

    def test_critique_correct_no_fallacies(self) -> None:
        """Correct with no fallacies - acceptable but don't get cocky."""
        critique = _generate_critique(True, "cassian", {}, [])
        assert "Acceptable" in critique or "don't let it go" in critique

    def test_critique_correct_with_fallacies(self) -> None:
        """Correct but with fallacies gets WRONG reasoning critique."""
        critique = _generate_critique(True, "cassian", {}, ["confirmation_bias"])
        assert "confirmation_bias" in critique
        assert "WRONG reasoning" in critique or "Sloppy" in critique

    def test_critique_incorrect_verdict(self) -> None:
        """Incorrect verdict gets harsh 'Pathetic' critique."""
        solution = {"culprit": "wisp", "key_evidence": ["frost_pattern"]}
        critique = _generate_critique(False, "elena", solution, [])
        assert "elena" in critique
        assert "wisp" in critique
        assert "frost_pattern" in critique
        assert "WRONG" in critique or "Pathetic" in critique


class TestGenerateAdaptiveHint:
    """Tests for _generate_adaptive_hint helper."""

    def test_harsh_hint_many_attempts(self) -> None:
        """Many attempts remaining = vague hint."""
        solution = {"key_evidence": ["frost"], "culprit": "wisp", "method": "spell"}
        hint = _generate_adaptive_hint(8, solution)
        assert "Think harder" in hint or "Review" in hint

    def test_specific_hint_few_attempts(self) -> None:
        """Few attempts = more specific hint."""
        solution = {
            "key_evidence": ["frost_pattern", "focus_signature"],
            "culprit": "wisp",
            "method": "spell",
        }
        hint = _generate_adaptive_hint(5, solution)
        assert "frost_pattern" in hint or "focus_signature" in hint or "key evidence" in hint.lower()

    def test_direct_hint_last_attempts(self) -> None:
        """Last attempts = almost give away."""
        solution = {"key_evidence": ["frost"], "culprit": "wisp", "method": "Freezing charm"}
        hint = _generate_adaptive_hint(2, solution)
        assert "freezing charm" in hint.lower() or "culprit" in hint.lower()


class TestBuildFallaciesDetailed:
    """Tests for _build_fallacies_detailed helper."""

    def test_build_with_templates(self) -> None:
        """Build detailed fallacies from templates."""
        fallacies = ["confirmation_bias"]
        templates = {
            "fallacies": {
                "confirmation_bias": {
                    "description": "Test description",
                    "example": "Test example",
                }
            }
        }

        result = _build_fallacies_detailed(fallacies, templates)
        assert len(result) == 1
        assert result[0]["name"] == "confirmation_bias"
        assert result[0]["description"] == "Test description"
        assert result[0]["example"] == "Test example"

    def test_build_without_template(self) -> None:
        """Build fallacy without matching template."""
        fallacies = ["unknown_fallacy"]
        templates = {"fallacies": {}}

        result = _build_fallacies_detailed(fallacies, templates)
        assert len(result) == 1
        assert result[0]["name"] == "unknown_fallacy"
        assert "unknown_fallacy" in result[0]["description"]

    def test_build_empty_fallacies(self) -> None:
        """Build with no fallacies returns empty list."""
        result = _build_fallacies_detailed([], {"fallacies": {}})
        assert result == []


class TestGetWrongSuspectResponse:
    """Tests for get_wrong_suspect_response function."""

    def test_get_existing_response(self) -> None:
        """Get pre-written response for wrong suspect."""
        templates = {
            "wrong_suspect_responses": {
                "elena": "GRAVES: Wrong! {attempts_remaining} attempts left."
            }
        }

        response = get_wrong_suspect_response("elena", templates, 5)
        assert response is not None
        assert "5" in response
        assert "Wrong!" in response

    def test_get_response_case_insensitive(self) -> None:
        """Response lookup is case-insensitive."""
        templates = {"wrong_suspect_responses": {"elena": "Response for Elena"}}

        response = get_wrong_suspect_response("ELENA", templates, 5)
        assert response is not None

    def test_no_response_for_unknown_suspect(self) -> None:
        """No response for suspect without template."""
        templates = {"wrong_suspect_responses": {"elena": "Response"}}

        response = get_wrong_suspect_response("cassian", templates, 5)
        assert response is None

    def test_no_wrong_suspect_responses_key(self) -> None:
        """Handle missing wrong_suspect_responses key."""
        templates = {}
        response = get_wrong_suspect_response("elena", templates, 5)
        assert response is None


class TestBuildGravesPrompts:
    """Tests for LLM prompt builders."""

    def test_roast_prompt_includes_context(self) -> None:
        """Roast prompt includes context but NOT the actual culprit."""
        from src.context.mentor import build_graves_roast_prompt

        prompt = build_graves_roast_prompt(
            player_reasoning="She was nearby so she did it",
            accused_suspect="elena",
            actual_culprit="cassian",  # Passed but should NOT appear in prompt
            evidence_cited=["witness_testimony"],
            key_evidence_missed=["frost_pattern", "focus_signature"],
            fallacies=["confirmation_bias"],
            score=35,
        )

        # Should include accused suspect
        assert "elena" in prompt
        # Should NOT reveal actual culprit
        assert "cassian" not in prompt.lower() or "don't reveal" in prompt.lower()
        # Should include evidence context
        assert "frost_pattern" in prompt or "focus_signature" in prompt
        assert "35" in prompt
        # Should request concise feedback
        assert "3-4 sentences" in prompt
        assert "Graves" in prompt
        # Should request rationality principle
        assert "rationality" in prompt.lower()
        # Should request hints without revealing
        assert "hint" in prompt.lower() or "without" in prompt.lower()

    def test_roast_prompt_includes_rationality_lessons(self) -> None:
        """Roast prompt instructs LLM to include rationality lessons."""
        from src.context.mentor import build_graves_roast_prompt

        prompt = build_graves_roast_prompt(
            player_reasoning="She was nearby so she did it",
            accused_suspect="elena",
            actual_culprit="cassian",
            evidence_cited=[],
            key_evidence_missed=["frost_pattern"],
            fallacies=["confirmation_bias"],
            score=30,
        )

        # Check prompt includes rationality principle instruction
        assert "rationality" in prompt.lower()
        # Check for natural integration instruction (no separate sections)
        assert "naturally" in prompt.lower() or "no separate sections" in prompt.lower()
        # Check for natural weaving instruction
        assert "woven" in prompt.lower() or "weave" in prompt.lower()

    def test_praise_prompt_includes_context(self) -> None:
        """Praise prompt includes all relevant context."""
        from src.context.mentor import build_graves_praise_prompt

        prompt = build_graves_praise_prompt(
            player_reasoning="The frost pattern and focus signature prove it",
            accused_suspect="cassian",
            evidence_cited=["frost_pattern", "focus_signature"],
            score=90,
            fallacies=[],
        )

        assert "cassian" in prompt
        assert "frost_pattern" in prompt or "focus_signature" in prompt
        assert "90" in prompt
        assert "CORRECT" in prompt
        assert "3-4 sentences" in prompt

    def test_praise_prompt_includes_rationality_lessons(self) -> None:
        """Praise prompt instructs LLM to include rationality lessons."""
        from src.context.mentor import build_graves_praise_prompt

        prompt = build_graves_praise_prompt(
            player_reasoning="Wisp did it because of the focus signature",
            accused_suspect="wisp",
            evidence_cited=["focus_signature"],
            score=75,
            fallacies=[],
        )

        # Check prompt includes rationality principle instruction
        assert "rationality" in prompt.lower()
        # Check for natural weaving instruction
        assert "naturally" in prompt.lower() or "weave" in prompt.lower()


class TestBuildGravesFeedbackLLM:
    """Tests for LLM feedback generation with fallback."""

    @pytest.mark.asyncio
    async def test_llm_feedback_fallback_on_error(self) -> None:
        """LLM failure falls back to templates gracefully."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.context.mentor import build_graves_feedback_llm

        # Mock get_client to raise an exception
        mock_client = MagicMock()
        mock_client.get_response = AsyncMock(side_effect=Exception("API timeout"))

        with patch("src.api.llm_client.get_client", return_value=mock_client):
            feedback = await build_graves_feedback_llm(
                correct=False,
                score=50,
                fallacies=[],
                reasoning="Test reasoning",
                accused_id="elena",
                solution={"culprit": "wisp"},
                attempts_remaining=8,
                evidence_cited=[],
                feedback_templates={},
            )

        # Should return template fallback (not crash)
        assert isinstance(feedback, str)
        assert len(feedback) > 0
        # Template fallback contains "Incorrect" for wrong verdict
        assert "Incorrect" in feedback or "wisp" in feedback.lower()

    @pytest.mark.asyncio
    async def test_llm_feedback_correct_calls_praise_prompt(self) -> None:
        """Correct verdict uses praise prompt."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.context.mentor import build_graves_feedback_llm

        mock_client = MagicMock()
        mock_client.get_response = AsyncMock(
            return_value="Good work, recruit. You cited key evidence."
        )

        with patch("src.api.llm_client.get_client", return_value=mock_client):
            feedback = await build_graves_feedback_llm(
                correct=True,
                score=85,
                fallacies=[],
                reasoning="The evidence points to cassian",
                accused_id="cassian",
                solution={"culprit": "wisp"},
                attempts_remaining=9,
                evidence_cited=["frost_pattern"],
                feedback_templates={},
            )

        assert "Good work" in feedback
        mock_client.get_response.assert_called_once()
        # Verify it was called with praise prompt (contains CORRECT)
        call_args = mock_client.get_response.call_args
        assert "CORRECT" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_llm_feedback_incorrect_calls_roast_prompt(self) -> None:
        """Incorrect verdict uses roast prompt."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.context.mentor import build_graves_feedback_llm

        mock_client = MagicMock()
        mock_client.get_response = AsyncMock(return_value="WRONG. You missed the obvious evidence.")

        with patch("src.api.llm_client.get_client", return_value=mock_client):
            feedback = await build_graves_feedback_llm(
                correct=False,
                score=40,
                fallacies=["confirmation_bias"],
                reasoning="She was there",
                accused_id="elena",
                solution={"culprit": "wisp", "key_evidence": ["frost_pattern"]},
                attempts_remaining=7,
                evidence_cited=[],
                feedback_templates={},
            )

        assert "WRONG" in feedback
        mock_client.get_response.assert_called_once()
        # Verify it was called with roast prompt (contains INCORRECT)
        call_args = mock_client.get_response.call_args
        assert "INCORRECT" in call_args[0][0]
