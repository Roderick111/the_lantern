"""Tests for fallacy detection logic."""

from src.verdict.fallacies import (
    _check_authority_bias,
    _check_confirmation_bias,
    _check_correlation_not_causation,
    _check_post_hoc,
    _check_weak_reasoning,
    detect_fallacies,
)


class TestDetectFallacies:
    """Tests for detect_fallacies main function."""

    def test_no_fallacies_good_reasoning(self) -> None:
        """Good reasoning with evidence has no fallacies."""
        reasoning = (
            "The focus signature proves Wisp cast the spell. The frost pattern confirms this."
        )
        accused_id = "wisp"
        evidence_cited = ["focus_signature", "frost_pattern"]
        case_data = {
            "solution": {"culprit": "wisp"},
            "wrong_suspects": {},
        }

        fallacies = detect_fallacies(reasoning, accused_id, evidence_cited, case_data)
        assert fallacies == []

    def test_detect_multiple_fallacies(self) -> None:
        """Detect multiple fallacies in bad reasoning."""
        reasoning = "She was present in the library. The witness said she did it. She argued before the incident."
        accused_id = "elena"
        evidence_cited: list[str] = []
        case_data = {
            "solution": {"culprit": "wisp"},
            "wrong_suspects": {
                "elena": {
                    "exoneration_evidence": ["focus_signature"],
                }
            },
        }

        fallacies = detect_fallacies(reasoning, accused_id, evidence_cited, case_data)

        # Should detect: confirmation_bias (wrong suspect, no exoneration evidence)
        # correlation_not_causation (was present)
        # authority_bias (witness said)
        # post_hoc (argued before)
        assert "confirmation_bias" in fallacies
        assert "correlation_not_causation" in fallacies
        assert "authority_bias" in fallacies
        assert "post_hoc" in fallacies

    def test_detect_single_fallacy(self) -> None:
        """Detect single specific fallacy."""
        reasoning = "She was there at the scene so she must have done it."
        accused_id = "wisp"
        evidence_cited: list[str] = []
        case_data = {
            "solution": {"culprit": "wisp"},
            "wrong_suspects": {},
        }

        fallacies = detect_fallacies(reasoning, accused_id, evidence_cited, case_data)
        assert "correlation_not_causation" in fallacies


class TestCheckConfirmationBias:
    """Tests for confirmation bias detection."""

    def test_confirmation_bias_wrong_suspect_no_exoneration(self) -> None:
        """Confirmation bias: wrong suspect, didn't cite exoneration evidence."""
        accused_id = "elena"
        evidence_cited = ["hidden_note"]  # Not the exoneration evidence
        case_data = {
            "solution": {"culprit": "wisp"},
            "wrong_suspects": {
                "elena": {
                    "exoneration_evidence": ["focus_signature"],
                }
            },
        }

        assert _check_confirmation_bias(accused_id, evidence_cited, case_data) is True

    def test_no_confirmation_bias_cited_exoneration(self) -> None:
        """No confirmation bias if player cited exoneration evidence."""
        accused_id = "elena"
        evidence_cited = ["focus_signature"]  # This is the exoneration evidence
        case_data = {
            "solution": {"culprit": "wisp"},
            "wrong_suspects": {
                "elena": {
                    "exoneration_evidence": ["focus_signature"],
                }
            },
        }

        assert _check_confirmation_bias(accused_id, evidence_cited, case_data) is False

    def test_no_confirmation_bias_correct_suspect(self) -> None:
        """No confirmation bias for correct suspect."""
        accused_id = "wisp"
        evidence_cited: list[str] = []
        case_data = {
            "solution": {"culprit": "wisp"},
            "wrong_suspects": {},
        }

        assert _check_confirmation_bias(accused_id, evidence_cited, case_data) is False

    def test_no_confirmation_bias_no_exoneration_defined(self) -> None:
        """No confirmation bias if no exoneration evidence defined."""
        accused_id = "elena"
        evidence_cited: list[str] = []
        case_data = {
            "solution": {"culprit": "wisp"},
            "wrong_suspects": {
                "elena": {
                    "exoneration_evidence": [],  # Empty
                }
            },
        }

        assert _check_confirmation_bias(accused_id, evidence_cited, case_data) is False


class TestCheckCorrelationNotCausation:
    """Tests for correlation/causation fallacy detection."""

    def test_detect_presence_claim_without_evidence(self) -> None:
        """Detect presence claim without causal evidence."""
        reasoning = "she was present at the scene"
        evidence_cited: list[str] = []

        assert _check_correlation_not_causation(reasoning, evidence_cited) is True

    def test_detect_nearby_claim(self) -> None:
        """Detect 'nearby' claims."""
        reasoning = "he was nearby when it happened"
        assert _check_correlation_not_causation(reasoning, []) is True

    def test_no_fallacy_with_causal_evidence(self) -> None:
        """No fallacy if presence claim + causal evidence."""
        reasoning = "she was present at the scene and the focus signature proves it"
        assert _check_correlation_not_causation(reasoning, []) is False

    def test_no_fallacy_no_presence_claim(self) -> None:
        """No fallacy if no presence claim made."""
        reasoning = "the evidence clearly shows guilt"
        assert _check_correlation_not_causation(reasoning, []) is False

    def test_detect_in_library_claim(self) -> None:
        """Detect 'was in the library' type claims."""
        reasoning = "elena was in the library so she did it"
        assert _check_correlation_not_causation(reasoning, []) is True


class TestCheckAuthorityBias:
    """Tests for authority bias detection."""

    def test_detect_witness_said(self) -> None:
        """Detect 'witness said' without evidence."""
        reasoning = "the witness said she did it"
        assert _check_authority_bias(reasoning) is True

    def test_detect_testimony_shows(self) -> None:
        """Detect 'testimony shows' without evidence."""
        reasoning = "testimony shows he was guilty"
        assert _check_authority_bias(reasoning) is True

    def test_detect_claimed(self) -> None:
        """Detect 'claimed' without evidence."""
        reasoning = "cassian claimed he was innocent but i don't believe him"
        assert _check_authority_bias(reasoning) is True

    def test_no_fallacy_with_evidence_verification(self) -> None:
        """No fallacy if testimony + evidence verification."""
        reasoning = "the witness said it, and the focus evidence confirms this"
        assert _check_authority_bias(reasoning) is False

    def test_no_fallacy_no_testimony_reliance(self) -> None:
        """No fallacy if not relying on testimony."""
        reasoning = "the physical evidence clearly shows guilt"
        assert _check_authority_bias(reasoning) is False


class TestCheckPostHoc:
    """Tests for post hoc fallacy detection."""

    def test_detect_argued_before(self) -> None:
        """Detect 'argued before' temporal reasoning."""
        reasoning = "they argued before the incident so they must be guilty"
        assert _check_post_hoc(reasoning) is True

    def test_detect_had_motive(self) -> None:
        """Detect 'had motive' without evidence."""
        reasoning = "he had motive to do it"
        assert _check_post_hoc(reasoning) is True

    def test_detect_grudge(self) -> None:
        """Detect grudge-based reasoning."""
        reasoning = "she held a grudge against the victim"
        assert _check_post_hoc(reasoning) is True

    def test_detect_threatened(self) -> None:
        """Detect threat-based reasoning."""
        reasoning = "he threatened the victim days ago"
        assert _check_post_hoc(reasoning) is True

    def test_no_fallacy_with_evidence_connection(self) -> None:
        """No fallacy if temporal reasoning + evidence."""
        reasoning = "they argued before and the focus signature proves they cast the spell"
        assert _check_post_hoc(reasoning) is False

    def test_no_fallacy_no_temporal_reasoning(self) -> None:
        """No fallacy if no temporal reasoning."""
        reasoning = "the evidence shows they cast the spell"
        assert _check_post_hoc(reasoning) is False

    def test_detect_angry_at(self) -> None:
        """Detect 'angry at' reasoning."""
        reasoning = "he was angry at her so he attacked"
        assert _check_post_hoc(reasoning) is True


class TestCheckWeakReasoning:
    """Tests for weak reasoning detection."""

    def test_detect_i_guess(self) -> None:
        """Detect 'I guess' weak reasoning."""
        reasoning = "i guess elena did it"
        assert _check_weak_reasoning(reasoning) is True

    def test_detect_i_think_maybe(self) -> None:
        """Detect 'I think maybe' weak reasoning."""
        reasoning = "i think maybe cassian is guilty"
        assert _check_weak_reasoning(reasoning) is True

    def test_detect_probably(self) -> None:
        """Detect 'probably' weak reasoning."""
        reasoning = "they probably cast the spell"
        assert _check_weak_reasoning(reasoning) is True

    def test_detect_not_sure(self) -> None:
        """Detect 'not sure' weak reasoning."""
        reasoning = "not sure but i think it was her"
        assert _check_weak_reasoning(reasoning) is True

    def test_detect_i_dont_know(self) -> None:
        """Detect 'I don't know' weak reasoning."""
        reasoning = "i don't know but maybe cassian"
        assert _check_weak_reasoning(reasoning) is True

    def test_detect_no_idea(self) -> None:
        """Detect 'no idea' weak reasoning."""
        reasoning = "no idea really but going with elena"
        assert _check_weak_reasoning(reasoning) is True

    def test_detect_just_a_feeling(self) -> None:
        """Detect 'just a feeling' weak reasoning."""
        reasoning = "just a feeling that cassian is guilty"
        assert _check_weak_reasoning(reasoning) is True

    def test_detect_no_reason(self) -> None:
        """Detect 'no reason' weak reasoning."""
        reasoning = "elena did it. no real reason."
        assert _check_weak_reasoning(reasoning) is True

    def test_detect_gut_feeling(self) -> None:
        """Detect 'gut feeling' weak reasoning."""
        reasoning = "my gut feeling says it was cassian"
        assert _check_weak_reasoning(reasoning) is True

    def test_no_fallacy_confident_reasoning(self) -> None:
        """No fallacy for confident reasoning."""
        reasoning = "the focus signature proves cassian cast the spell"
        assert _check_weak_reasoning(reasoning) is False

    def test_no_fallacy_evidence_based(self) -> None:
        """No fallacy for evidence-based reasoning."""
        reasoning = "the frost pattern clearly shows the spell came from outside"
        assert _check_weak_reasoning(reasoning) is False

    def test_weak_reasoning_in_detect_fallacies(self) -> None:
        """Weak reasoning detected by main function."""
        reasoning = "I guess Elena did it. Not sure though."
        accused_id = "elena"
        evidence_cited: list[str] = []
        case_data = {
            "solution": {"culprit": "wisp"},
            "wrong_suspects": {},
        }

        fallacies = detect_fallacies(reasoning, accused_id, evidence_cited, case_data)
        assert "weak_reasoning" in fallacies
