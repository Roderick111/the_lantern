"""Fallacy detection for player reasoning analysis."""

from typing import Any


def detect_fallacies(
    reasoning: str,
    accused_suspect_id: str,
    evidence_cited: list[str],
    case_data: dict[str, Any],
) -> list[str]:
    """Detect logical fallacies in player reasoning.

    Args:
        reasoning: Player's reasoning text (will be lowercased for matching)
        accused_suspect_id: Who player accused
        evidence_cited: Evidence IDs player selected
        case_data: Full case data (for checking witness/evidence relationships)

    Returns:
        List of fallacy names detected
    """
    fallacies: list[str] = []
    reasoning_lower = reasoning.lower()

    # Confirmation bias: only cited evidence supporting accused
    if _check_confirmation_bias(accused_suspect_id, evidence_cited, case_data):
        fallacies.append("confirmation_bias")

    # Correlation not causation: "they were there so they did it"
    if _check_correlation_not_causation(reasoning_lower, evidence_cited):
        fallacies.append("correlation_not_causation")

    # Authority bias: "witness said so"
    if _check_authority_bias(reasoning_lower):
        fallacies.append("authority_bias")

    # Post hoc: "they argued earlier, so they must be guilty"
    if _check_post_hoc(reasoning_lower):
        fallacies.append("post_hoc")

    # Weak reasoning: guessing, uncertainty, no logic
    if _check_weak_reasoning(reasoning_lower):
        fallacies.append("weak_reasoning")

    return fallacies


def _check_confirmation_bias(
    accused_id: str,
    evidence_cited: list[str],
    case_data: dict[str, Any],
) -> bool:
    """Check if player only cited evidence supporting their theory.

    Returns True if player ignored contradictory evidence (exoneration evidence).

    Args:
        accused_id: Who player accused
        evidence_cited: Evidence IDs player cited
        case_data: Full case data

    Returns:
        True if confirmation bias detected
    """
    solution = case_data.get("solution", {})
    actual_culprit = solution.get("culprit", "")

    # If accused is wrong, check if player ignored exoneration evidence
    if accused_id.lower() != actual_culprit.lower():
        wrong_suspects = case_data.get("wrong_suspects", {})
        for suspect_id, suspect_data in wrong_suspects.items():
            if suspect_id.lower() == accused_id.lower():
                # Check if player cited exoneration evidence
                exoneration = suspect_data.get("exoneration_evidence", []) if isinstance(suspect_data, dict) else []
                if exoneration and not any(e in evidence_cited for e in exoneration):
                    return True  # Confirmation bias detected

    return False


def _check_correlation_not_causation(
    reasoning_lower: str,
    evidence_cited: list[str],
) -> bool:
    """Check if player assumed presence = guilt.

    Detects phrases like "was present", "was there", "at the scene"
    without citing actual causal evidence.

    Args:
        reasoning_lower: Lowercased reasoning text
        evidence_cited: Evidence IDs cited

    Returns:
        True if correlation/causation fallacy detected
    """
    presence_phrases = [
        "was present",
        "was there",
        "at the scene",
        "in the area",
        "nearby",
        "was in the library",
        "was at the window",
        "seen near",
        "spotted at",
    ]

    # Check if reasoning mentions presence
    has_presence_claim = any(phrase in reasoning_lower for phrase in presence_phrases)

    if not has_presence_claim:
        return False

    # Check if reasoning lacks actual causal evidence keywords
    causal_keywords = [
        "focus",
        "signature",
        "cast",
        "spell",
        "magical",
        "evidence",
        "frost",
        "incantato",
        "charm",
        "proves",
        "because the",
    ]

    has_causal_evidence = any(word in reasoning_lower for word in causal_keywords)

    # If presence claim without causal evidence = fallacy
    return has_presence_claim and not has_causal_evidence


def _check_authority_bias(reasoning_lower: str) -> bool:
    """Check if player relied on testimony without evidence verification.

    Args:
        reasoning_lower: Lowercased reasoning text

    Returns:
        True if authority bias detected
    """
    testimony_phrases = [
        "witness said",
        "testimony shows",
        "they told me",
        "claimed",
        "according to",
        "stated that",
        "told us",
        "said they saw",
    ]

    # Check if reasoning relies on testimony
    has_testimony_reliance = any(phrase in reasoning_lower for phrase in testimony_phrases)

    if not has_testimony_reliance:
        return False

    # Check if reasoning mentions physical/magical evidence verification
    evidence_verification_keywords = [
        "evidence",
        "focus",
        "frost",
        "signature",
        "proves",
        "confirmed by",
        "verified",
        "physical",
        "magical trace",
    ]

    has_evidence_verification = any(
        word in reasoning_lower for word in evidence_verification_keywords
    )

    # If testimony reliance without evidence verification = fallacy
    return has_testimony_reliance and not has_evidence_verification


def _check_post_hoc(reasoning_lower: str) -> bool:
    """Check if player assumed temporal sequence implies causation.

    Detects "argued earlier", "had motive", "wanted to" type reasoning
    without connecting to physical evidence.

    Args:
        reasoning_lower: Lowercased reasoning text

    Returns:
        True if post hoc fallacy detected
    """
    temporal_phrases = [
        "argued before",
        "argued earlier",
        "had motive",
        "wanted to",
        "angry at",
        "threatened",
        "made threats",
        "before the",
        "days ago",
        "earlier that",
        "prior to",
        "grudge against",
    ]

    has_temporal_reasoning = any(phrase in reasoning_lower for phrase in temporal_phrases)

    if not has_temporal_reasoning:
        return False

    # Check if connected to physical evidence
    evidence_keywords = [
        "focus",
        "signature",
        "physical evidence",
        "frost",
        "spell residue",
        "proves",
        "confirms",
        "and the evidence",
    ]

    has_evidence_connection = any(word in reasoning_lower for word in evidence_keywords)

    # If temporal reasoning without evidence connection = fallacy
    return has_temporal_reasoning and not has_evidence_connection


def _check_weak_reasoning(reasoning_lower: str) -> bool:
    """Check if player is guessing or showing uncertainty without evidence.

    Detects phrases like "I guess", "I think maybe", "probably", etc.
    that indicate weak reasoning without logical basis.

    Args:
        reasoning_lower: Lowercased reasoning text

    Returns:
        True if weak reasoning detected
    """
    weak_phrases = [
        "i guess",
        "i think maybe",
        "probably",
        "not sure",
        "i don't know",
        "no idea",
        "just a feeling",
        "maybe it was",
        "could be",
        "might have",
        "just seems",
        "i assume",
        "gut feeling",
        "seems like",
        "no reason",
        "no real reason",
    ]

    return any(phrase in reasoning_lower for phrase in weak_phrases)
