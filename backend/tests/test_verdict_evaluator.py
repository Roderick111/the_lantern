"""Tests for verdict evaluation logic."""

from src.verdict.evaluator import (
    _count_sentences,
    calculate_attempts_hint_level,
    check_verdict,
    score_reasoning,
)


class TestCheckVerdict:
    """Tests for check_verdict function."""

    def test_correct_verdict_exact_match(self) -> None:
        """Correct verdict with exact case match."""
        solution = {"culprit": "cassian"}
        assert check_verdict("cassian", solution) is True

    def test_correct_verdict_case_insensitive(self) -> None:
        """Correct verdict case-insensitive."""
        solution = {"culprit": "cassian"}
        assert check_verdict("Cassian", solution) is True
        assert check_verdict("CASSIAN", solution) is True

    def test_incorrect_verdict(self) -> None:
        """Incorrect verdict returns False."""
        solution = {"culprit": "cassian"}
        assert check_verdict("elena", solution) is False

    def test_verdict_empty_culprit(self) -> None:
        """Empty culprit in solution."""
        solution = {"culprit": ""}
        assert check_verdict("cassian", solution) is False

    def test_verdict_missing_culprit(self) -> None:
        """Missing culprit key in solution."""
        solution = {}
        assert check_verdict("cassian", solution) is False

    def test_verdict_whitespace_handling(self) -> None:
        """Verdict with whitespace (case-insensitive only, not trimmed)."""
        solution = {"culprit": "cassian"}
        # Only case-insensitivity is applied, not trimming
        assert check_verdict("cassian", solution) is True


class TestScoreReasoning:
    """Tests for score_reasoning function - HARSH grading."""

    def test_perfect_score(self) -> None:
        """Perfect reasoning: all key evidence, logical connectors, 2-5 sentences."""
        # Multi-sentence reasoning with 'because' and all key evidence
        reasoning = "The frost pattern proves Cassian's involvement. The focus signature confirms the spell. This happened because the evidence chain is complete."
        evidence = ["frost_pattern", "focus_signature", "window_damage"]
        solution = {"key_evidence": ["frost_pattern", "focus_signature", "window_damage"]}
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 40 (3+ critical) + 20 (because + 3 sentences) = 80
        assert score == 80

    def test_minimal_effort_gets_minimal_score(self) -> None:
        """Short reasoning (< 50 chars) gets minimal score."""
        reasoning = "They did it"  # < 50 chars
        evidence: list[str] = []
        solution = {"key_evidence": ["frost_pattern"]}
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        assert score == 5  # Minimal effort = 5

    def test_no_critical_evidence_heavy_penalty(self) -> None:
        """No critical evidence cited gets heavy penalty."""
        reasoning = "Elena did it because she was there. The evidence points to her clearly."
        evidence: list[str] = []  # No evidence cited
        solution = {"key_evidence": ["frost_pattern", "focus_signature"]}
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 - 30 (no critical) + 20 (because + 2 sentences) = 10
        assert score == 10

    def test_one_critical_evidence(self) -> None:
        """Citing one critical evidence gives +10."""
        reasoning = (
            "The frost pattern proves the spell was cast from outside. This shows clear intent."
        )
        evidence = ["frost_pattern"]
        solution = {"key_evidence": ["frost_pattern", "focus_signature", "window_damage"]}
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 10 (1 critical) + 5 (2 sentences, no logical connector) - 15 (no because/since) = 20
        assert score == 20

    def test_two_critical_evidence(self) -> None:
        """Citing two critical evidence gives +25."""
        reasoning = "The frost pattern proves it. The focus signature confirms because both match."
        evidence = ["frost_pattern", "focus_signature"]
        solution = {"key_evidence": ["frost_pattern", "focus_signature", "window_damage"]}
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 25 (2 critical) + 20 (because + 2 sentences) = 65
        assert score == 65

    def test_all_critical_evidence(self) -> None:
        """Citing all critical evidence gives +40."""
        reasoning = "The frost pattern shows the spell. The focus signature matches. Window damage proves it because everything aligns."
        evidence = ["frost_pattern", "focus_signature", "window_damage"]
        solution = {"key_evidence": ["frost_pattern", "focus_signature", "window_damage"]}
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 40 (3+ critical) + 20 (because + 3 sentences) = 80
        assert score == 80

    def test_coherence_with_logical_connectors(self) -> None:
        """Logical connectors (because, therefore, since) give +20 when 2-5 sentences."""
        # Provide evidence to avoid -30 penalty
        solution = {"key_evidence": ["frost_pattern"]}
        evidence = ["frost_pattern"]
        fallacies: list[str] = []

        # With 'because' and 2 sentences - gets full coherence bonus
        reasoning = (
            "The frost pattern proves guilt because the pattern matches. This is conclusive."
        )
        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 10 (1 critical) + 20 (because + 2 sentences) = 50
        assert score == 50

        # Without logical connectors but with sentences - lower score
        reasoning = "The frost pattern is there. The pattern matches. This looks conclusive."
        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 10 (1 critical) + 5 (3 sentences, no logic) - 15 (no because/since) = 20
        assert score == 20

    def test_too_short_penalty(self) -> None:
        """Less than 2 sentences gets penalty even with because."""
        # Provide evidence to avoid -30 penalty
        reasoning = (
            "The frost pattern proves guilt because of the evidence shown here."  # 1 sentence
        )
        solution = {"key_evidence": ["frost_pattern"]}
        evidence = ["frost_pattern"]
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 10 (1 critical) - 10 (< 2 sentences), has because so no -15
        # = 20
        assert score == 20

    def test_rambling_penalty(self) -> None:
        """More than 8 sentences gets rambling penalty."""
        # Provide evidence to avoid -30 penalty
        reasoning = "The frost pattern is key. One. Two. Three. Four. Five. Six. Seven. Eight. This proves guilt because evidence."
        solution = {"key_evidence": ["frost_pattern"]}
        evidence = ["frost_pattern"]
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 10 (1 critical) - 15 (> 8 sentences), has because so no -15 penalty
        # = 15
        assert score == 15

    def test_fallacy_penalty_harsh(self) -> None:
        """Fallacy penalty is -20 each (no cap)."""
        # Provide evidence to avoid -30 penalty
        reasoning = (
            "The frost pattern proves guilt clearly. This is obvious because of the evidence shown."
        )
        evidence = ["frost_pattern"]
        solution = {"key_evidence": ["frost_pattern"]}

        # 1 fallacy = -20
        fallacies = ["confirmation_bias"]
        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 10 (1 critical) + 20 (because + 2 sentences) - 20 (fallacy) = 30
        assert score == 30

        # 2 fallacies = -40
        fallacies = ["confirmation_bias", "authority_bias"]
        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 10 + 20 - 40 = 10
        assert score == 10

        # 3 fallacies = -60
        fallacies = ["confirmation_bias", "authority_bias", "post_hoc"]
        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 10 + 20 - 60 = -10 -> 0
        assert score == 0

    def test_vague_language_penalty(self) -> None:
        """Vague words like 'maybe', 'i guess' get -10 each."""
        reasoning = (
            "I think maybe she did it. I guess the evidence seems like it supports this theory."
        )
        evidence: list[str] = []
        solution = {"key_evidence": []}
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20, 2 sentences no logic = +5, no because/since = -15
        # No key_evidence so no -30 penalty
        # Wait - key_evidence is empty list, so critical_cited is also empty
        # len(critical_cited) == 0 is True, so -30 applies!
        # Vague: "i think" (-10), "maybe" (-10), "i guess" (-10), "seems like" (-10) = -40
        # Total: 20 - 30 + 5 - 15 - 40 = -60 -> clamped to 0
        assert score == 0

    def test_no_causal_reasoning_penalty(self) -> None:
        """Missing 'because' or 'since' gets -15."""
        reasoning = "The frost pattern points to guilt. The evidence matches perfectly. The conclusion is clear."
        evidence = ["frost_pattern"]
        solution = {"key_evidence": ["frost_pattern"]}
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 10 (1 critical) + 5 (3 sentences, no logic) - 15 (no causal words) = 20
        assert score == 20

    def test_bullshit_reasoning_low_score(self) -> None:
        """Total bullshit reasoning should get very low score."""
        reasoning = (
            "I guess maybe Elena did it. She seems like the type. I think it was probably her."
        )
        evidence: list[str] = []
        solution = {"key_evidence": ["frost_pattern", "focus_signature"]}
        fallacies = ["confirmation_bias"]

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 - 30 (no critical) + 5 (3 sentences, no logic) - 15 (no because/since) - 20 (fallacy)
        # Vague: "i guess", "maybe", "seems like", "i think", "probably" = -50
        # Total: 20 - 30 + 5 - 15 - 20 - 50 = -90 -> clamped to 0
        assert score == 0

    def test_good_reasoning_high_score(self) -> None:
        """Good reasoning with evidence and logic gets high score."""
        reasoning = "Cassian is guilty because the focus signature matches his focus. The frost pattern was cast from outside."
        evidence = ["frost_pattern", "focus_signature"]
        solution = {"key_evidence": ["frost_pattern", "focus_signature"]}
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 25 (2 critical) + 20 (has 'because' + 2 sentences) = 65
        assert score == 65

    def test_score_clamped_to_100(self) -> None:
        """Score cannot exceed 100."""
        reasoning = "The frost pattern proves it. Focus signature confirms. Window damage shows method. This happened because all evidence aligns."
        evidence = ["frost_pattern", "focus_signature", "window_damage", "extra_evidence"]
        solution = {
            "key_evidence": ["frost_pattern", "focus_signature", "window_damage", "extra_evidence"]
        }
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 + 40 (3+ critical) + 20 (because + 4 sentences) = 80
        assert score <= 100
        assert score == 80

    def test_score_clamped_to_0(self) -> None:
        """Score cannot go below 0."""
        reasoning = "I guess maybe probably she did it. I think it seems like she's guilty. Kind of obvious."
        evidence: list[str] = []
        solution = {"key_evidence": ["a", "b"]}
        fallacies = ["f1", "f2", "f3"]

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Many penalties stack up, should clamp to 0
        assert score == 0

    def test_non_key_evidence_not_counted(self) -> None:
        """Evidence not in key_evidence doesn't add bonus."""
        reasoning = "The hidden note proves guilt. This shows motive because it reveals intent."
        evidence = ["hidden_note"]  # Not in key_evidence
        solution = {"key_evidence": ["frost_pattern", "focus_signature"]}
        fallacies: list[str] = []

        score = score_reasoning(reasoning, evidence, solution, fallacies)
        # Base 20 - 30 (no critical cited) + 20 (has because + 2 sentences) = 10
        assert score == 10


class TestCountSentences:
    """Tests for _count_sentences helper."""

    def test_count_periods(self) -> None:
        """Count periods as sentence terminators."""
        assert _count_sentences("One. Two. Three.") == 3

    def test_count_exclamations(self) -> None:
        """Count exclamation marks."""
        assert _count_sentences("Wow! Amazing!") == 2

    def test_count_questions(self) -> None:
        """Count question marks."""
        assert _count_sentences("Why? How?") == 2

    def test_mixed_punctuation(self) -> None:
        """Count mixed punctuation."""
        assert _count_sentences("Yes. Why? Amazing!") == 3

    def test_no_terminal_punctuation(self) -> None:
        """Text without terminal punctuation counts as 1."""
        assert _count_sentences("No punctuation here") == 1

    def test_empty_string(self) -> None:
        """Empty string returns 0."""
        assert _count_sentences("") == 0

    def test_whitespace_only(self) -> None:
        """Whitespace only returns 0."""
        assert _count_sentences("   ") == 0


class TestCalculateAttemptsHintLevel:
    """Tests for calculate_attempts_hint_level function."""

    def test_harsh_level_10_attempts(self) -> None:
        """10 attempts remaining = harsh."""
        assert calculate_attempts_hint_level(10) == "harsh"

    def test_harsh_level_7_attempts(self) -> None:
        """7 attempts remaining = harsh."""
        assert calculate_attempts_hint_level(7) == "harsh"

    def test_specific_level_6_attempts(self) -> None:
        """6 attempts remaining = specific."""
        assert calculate_attempts_hint_level(6) == "specific"

    def test_specific_level_4_attempts(self) -> None:
        """4 attempts remaining = specific."""
        assert calculate_attempts_hint_level(4) == "specific"

    def test_direct_level_3_attempts(self) -> None:
        """3 attempts remaining = direct."""
        assert calculate_attempts_hint_level(3) == "direct"

    def test_direct_level_1_attempt(self) -> None:
        """1 attempt remaining = direct."""
        assert calculate_attempts_hint_level(1) == "direct"

    def test_direct_level_0_attempts(self) -> None:
        """0 attempts remaining = direct."""
        assert calculate_attempts_hint_level(0) == "direct"
