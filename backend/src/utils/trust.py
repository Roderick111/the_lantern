"""Trust mechanics for witness interrogation.

Handles trust adjustment based on question tone and secret trigger evaluation.
Phase 7: LLM-driven trust via [TRUST_DELTA: N] tags piggybacked on witness responses.
"""

import logging
import re
from difflib import SequenceMatcher
from typing import Any

logger = logging.getLogger(__name__)

# Regex for [TRUST_DELTA: N] tag in LLM responses
# Colon is optional — LLMs sometimes output [TRUST_DELTA +4] or [TRUST_DELTA4]
# Also matches abbreviations like "TA: -12]" or "TD: 5]"
TRUST_DELTA_TAG_RE = re.compile(
    r"\[?(?:TRUST_DELTA|TRUST_D|TD|TA):?\s*([+-]?\d+)\s*\]",
    re.IGNORECASE,
)
# For stripping: match any variant including the full tag
TRUST_DELTA_STRIP_RE = re.compile(
    r"\s*\[?(?:TRUST_DELTA|TRUST_D|TD|TA):?\s*[+-]?\d+\s*\]",
    re.IGNORECASE,
)
# Also match partial tags during streaming (safety net)
# Requires opening bracket to avoid false positives on normal text containing "T"
TRUST_DELTA_TAG_PARTIAL_RE = re.compile(
    r"\s*\[T(?:R(?:U(?:S(?:T(?:_(?:D(?:E(?:L(?:T(?:A)?)?)?)?)?)?)?)?)?)?:?\s*[^\]]*$", re.IGNORECASE
)

# Clamping range for LLM-provided trust deltas (symmetric)
TRUST_DELTA_MIN = -15
TRUST_DELTA_MAX = 10

# Natural warming: small trust bonus when LLM doesn't emit a tag.
# Simply engaging in conversation builds mild rapport over time.
NATURAL_WARMING_MIN = 0
NATURAL_WARMING_MAX = 3

# Trust boundaries
MIN_TRUST = 0
MAX_TRUST = 100


def natural_warming() -> int:
    """Return a small random trust bonus for natural conversation warming.

    When the LLM doesn't emit a [TRUST_DELTA] tag, we assume the exchange
    was neutral-to-positive and apply a small rapport bonus (0-5).
    """
    import random

    return random.randint(NATURAL_WARMING_MIN, NATURAL_WARMING_MAX)


def extract_trust_delta(response: str) -> int | None:
    """Extract trust delta from LLM response [TRUST_DELTA: N] tag.

    Args:
        response: Full LLM response text

    Returns:
        Clamped trust delta, or None if tag not found/invalid
    """
    match = TRUST_DELTA_TAG_RE.search(response)
    if not match:
        return None
    try:
        raw = int(match.group(1))
    except ValueError:
        return None
    clamped = max(TRUST_DELTA_MIN, min(TRUST_DELTA_MAX, raw))
    if clamped != raw:
        logger.warning("Trust delta clamped: %d → %d", raw, clamped)
    return clamped


def strip_trust_tag(text: str) -> str:
    """Strip [TRUST_DELTA: N] tags from text for display.

    Handles complete tags, LLM abbreviations (TA:, TD:), and partial tags during streaming.

    Args:
        text: Response text possibly containing trust tags

    Returns:
        Cleaned text with trust tags removed
    """
    cleaned = TRUST_DELTA_STRIP_RE.sub("", text)
    cleaned = TRUST_DELTA_TAG_PARTIAL_RE.sub("", cleaned)
    return cleaned.rstrip()


def clamp_trust(trust: int) -> int:
    """Clamp trust to valid range [0, 100].

    Args:
        trust: Raw trust value

    Returns:
        Clamped trust value
    """
    return max(MIN_TRUST, min(MAX_TRUST, trust))


def parse_trigger_condition(trigger: str) -> list[dict[str, Any]]:
    """Parse trigger string into evaluable conditions.

    Supports:
    - "trust>N" or "trust<N" (trust threshold)
    - "evidence:X" (requires evidence)
    - "evidence_count>N", "evidence_count>=N", "evidence_count==N", etc. (evidence count)
    - "AND" / "OR" operators

    Args:
        trigger: Trigger string (e.g., "evidence:frost_pattern OR trust>70")

    Returns:
        List of condition dicts with type, operator, value
    """
    conditions: list[dict[str, Any]] = []

    # Split by OR first (lower precedence)
    or_parts = re.split(r"\s+OR\s+", trigger, flags=re.IGNORECASE)

    for or_part in or_parts:
        # Split by AND (higher precedence)
        and_parts = re.split(r"\s+AND\s+", or_part, flags=re.IGNORECASE)
        and_conditions: list[dict[str, Any]] = []

        for part in and_parts:
            part = part.strip()

            # Parse evidence_count condition: evidence_count>N, evidence_count>=N, etc.
            # Must check BEFORE trust to avoid matching "trust" in evidence_count
            count_match = re.match(r"evidence_count\s*([<>=!]+)\s*(\d+)", part, re.IGNORECASE)
            if count_match:
                and_conditions.append(
                    {
                        "type": "evidence_count",
                        "operator": count_match.group(1),
                        "value": int(count_match.group(2)),
                    }
                )
                continue

            # Parse trust condition: trust>N or trust<N
            trust_match = re.match(r"trust\s*([<>])\s*(\d+)", part, re.IGNORECASE)
            if trust_match:
                and_conditions.append(
                    {
                        "type": "trust",
                        "operator": trust_match.group(1),
                        "value": int(trust_match.group(2)),
                    }
                )
                continue

            # Parse evidence condition: evidence:X
            evidence_match = re.match(r"evidence:(\w+)", part, re.IGNORECASE)
            if evidence_match:
                and_conditions.append(
                    {
                        "type": "evidence",
                        "value": evidence_match.group(1),
                    }
                )
                continue

        if and_conditions:
            conditions.append(
                {
                    "type": "and_group",
                    "conditions": and_conditions,
                }
            )

    return conditions


def evaluate_condition(
    condition: dict[str, Any],
    trust: int,
    discovered_evidence: list[str],
    evidence_count: int | None = None,
) -> bool:
    """Evaluate a single parsed condition.

    Args:
        condition: Parsed condition dict
        trust: Current trust level
        discovered_evidence: List of discovered evidence IDs
        evidence_count: Optional explicit evidence count (defaults to len(discovered_evidence))

    Returns:
        True if condition is met
    """
    cond_type = condition.get("type")

    # Default evidence_count to len of discovered_evidence if not provided
    if evidence_count is None:
        evidence_count = len(discovered_evidence)

    if cond_type == "trust":
        operator = condition.get("operator")
        threshold = condition.get("value", 0)

        if operator == ">":
            return trust > threshold
        elif operator == "<":
            return trust < threshold

    elif cond_type == "evidence":
        evidence_id = condition.get("value", "")
        return evidence_id in discovered_evidence

    elif cond_type == "evidence_count":
        operator = condition.get("operator")
        threshold = condition.get("value", 0)

        if operator == ">":
            return evidence_count > threshold
        elif operator == ">=":
            return evidence_count >= threshold
        elif operator == "==":
            return evidence_count == threshold
        elif operator == "<":
            return evidence_count < threshold
        elif operator == "<=":
            return evidence_count <= threshold
        elif operator == "!=":
            return evidence_count != threshold

    elif cond_type == "and_group":
        # All conditions in AND group must be true
        sub_conditions = condition.get("conditions", [])
        return all(
            evaluate_condition(c, trust, discovered_evidence, evidence_count)
            for c in sub_conditions
        )

    return False


def check_secret_triggers(
    secret: dict[str, Any],
    trust: int,
    discovered_evidence: list[str],
) -> bool:
    """Check if secret trigger conditions are met.

    Args:
        secret: Secret dict with 'trigger' field
        trust: Current trust level (0-100)
        discovered_evidence: List of discovered evidence IDs

    Returns:
        True if trigger conditions are met and secret should be revealed
    """
    trigger = secret.get("trigger", "")
    if not trigger:
        return False

    conditions = parse_trigger_condition(trigger)

    # OR logic: any condition group being true triggers the secret
    return any(evaluate_condition(cond, trust, discovered_evidence) for cond in conditions)


def get_available_secrets(
    witness: dict[str, Any],
    trust: int,
    discovered_evidence: list[str],
) -> list[dict[str, Any]]:
    """Get list of secrets available to reveal based on trust and evidence.

    Args:
        witness: Witness data dict
        trust: Current trust level
        discovered_evidence: List of discovered evidence IDs

    Returns:
        List of secrets whose trigger conditions are met
    """
    secrets = witness.get("secrets", [])
    return [s for s in secrets if check_secret_triggers(s, trust, discovered_evidence)]


def should_lie(
    witness: dict[str, Any],
    question: str,
    trust: int,
) -> dict[str, Any] | None:
    """Check if witness should lie based on trust level and question topic.

    Args:
        witness: Witness data dict
        question: Player's question
        trust: Current trust level

    Returns:
        Lie dict with 'response' if witness should lie, None otherwise
    """
    lies = witness.get("lies", [])
    question_lower = question.lower()

    for lie in lies:
        condition = lie.get("condition", "")
        topics = lie.get("topics", [])

        # Parse trust condition from lie (e.g., "trust<30")
        trust_match = re.match(r"trust\s*([<>])\s*(\d+)", condition, re.IGNORECASE)
        if not trust_match:
            continue

        operator = trust_match.group(1)
        threshold = int(trust_match.group(2))

        # Check if trust condition is met
        trust_met = (operator == "<" and trust < threshold) or (
            operator == ">" and trust > threshold
        )

        if not trust_met:
            continue

        # Check if question matches any lie topic
        if any(topic.lower() in question_lower for topic in topics):
            return lie

    return None


def _get_discovered_evidence_objs(
    discovered_evidence: list[str],
    case_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Get evidence objects for all discovered evidence IDs."""
    case_inner = case_data.get("case", case_data)
    all_evidence: list[dict[str, Any]] = []
    for location in case_inner.get("locations", {}).values():
        all_evidence.extend(location.get("hidden_evidence", []))
    return [e for e in all_evidence if e.get("id") in discovered_evidence]


_MIN_SUBSTR_LEN = 3  # minimum token length for substring containment matching


def _tokenize(text: str) -> list[str]:
    """Lowercase split, strip common articles/prepositions."""
    stop = {"the", "a", "an", "this", "that", "of", "to", "in", "on", "is", "it", "i"}
    return [w for w in text.lower().split() if w not in stop]


_FUZZY_TOKEN_THRESHOLD = 0.75  # minimum similarity for fuzzy token match


def _token_overlap_score(
    input_tokens: list[str],
    name_tokens: list[str],
) -> float:
    """Fraction of name tokens matched by input tokens.

    Tries substring match first, falls back to SequenceMatcher similarity.
    """
    if not name_tokens:
        return 0.0
    matched = 0
    for nt in name_tokens:
        # Exact substring match (fast path, require min length for containment)
        if any(
            (nt == it) or (len(min(nt, it, key=len)) >= _MIN_SUBSTR_LEN and (nt in it or it in nt))
            for it in input_tokens
        ):
            matched += 1
            continue
        # Fuzzy match (typo tolerance)
        if any(
            SequenceMatcher(None, nt, it).ratio() >= _FUZZY_TOKEN_THRESHOLD for it in input_tokens
        ):
            matched += 1
    return matched / len(name_tokens)


# Verb patterns that signal explicit evidence presentation intent
_PRESENTATION_VERBS = re.compile(
    r"\b(show|present|give|reveal|hand|display)\b",
    re.IGNORECASE,
)

# Minimum token overlap required (fraction of evidence name tokens matched)
_MIN_OVERLAP_MULTI = 0.5  # multi-word names: at least half the tokens
_VERB_BOOST = 0.25  # bonus when explicit presentation verb present

# Generic words that should NOT count as distinctive evidence matches on their own
_EVIDENCE_GENERIC_WORDS = {
    "evidence",
    "proof",
    "clue",
    "item",
    "thing",
    "object",
    "found",
    "discovered",
    "hidden",
    "unknown",
    "old",
    "new",
    "small",
    "large",
    "broken",
    "open",
    "closed",
    "wet",
    "dry",
}


def detect_evidence_in_message(
    player_input: str,
    discovered_evidence: list[str],
    case_data: dict[str, Any],
) -> str | None:
    """Detect if player's message references any discovered evidence.

    Scans the full message for evidence name mentions using token overlap.
    Explicit presentation verbs ("show", "present", etc.) lower the threshold.

    Args:
        player_input: Raw player input text
        discovered_evidence: List of evidence IDs player has found
        case_data: Full case data with evidence definitions

    Returns:
        Matched evidence ID, or None
    """
    if not discovered_evidence:
        return None

    input_lower = player_input.lower()
    input_tokens = _tokenize(player_input)
    has_verb = bool(_PRESENTATION_VERBS.search(player_input))

    evidence_objs = _get_discovered_evidence_objs(discovered_evidence, case_data)

    best_id: str | None = None
    best_score: float = 0.0

    for ev in evidence_objs:
        eid: str = str(ev.get("id", ""))
        ename: str = str(ev.get("name", "")).lower()
        name_tokens = _tokenize(ename)

        # 1) Exact ID mention (e.g., "hidden_note" or "hidden note")
        if eid.lower() in input_lower or eid.replace("_", " ") in input_lower:
            return eid

        # 2) Full name substring
        if ename in input_lower:
            return eid

        # 3) Token overlap scoring
        score = _token_overlap_score(input_tokens, name_tokens)
        if has_verb:
            score += _VERB_BOOST

        # Single-word evidence names need exact token match (avoid false positives)
        if len(name_tokens) == 1:
            if name_tokens[0] in input_tokens:
                score = 1.0
            else:
                score = 0.0
                if has_verb:
                    # With verb, allow substring: "show note" matches "note"
                    if any(
                        len(min(name_tokens[0], it, key=len)) >= _MIN_SUBSTR_LEN
                        and (name_tokens[0] in it or it in name_tokens[0])
                        for it in input_tokens
                    ):
                        score = 1.0

        # Multi-word: require distinctive token matches
        if len(name_tokens) > 1:
            matched_tokens = [
                nt
                for nt in name_tokens
                if any(
                    (nt == it)
                    or (len(min(nt, it, key=len)) >= _MIN_SUBSTR_LEN and (nt in it or it in nt))
                    for it in input_tokens
                )
                or any(
                    SequenceMatcher(None, nt, it).ratio() >= _FUZZY_TOKEN_THRESHOLD
                    for it in input_tokens
                )
            ]
            raw_matched = len(matched_tokens)
            distinctive = [t for t in matched_tokens if t not in _EVIDENCE_GENERIC_WORDS]

            if not distinctive:
                # No distinctive tokens matched — reject
                score = 0.0
            elif raw_matched < 2 and not has_verb:
                # Single distinctive token without verb — not enough
                score = 0.0

        if score > best_score:
            best_score = score
            best_id = eid

    if best_score >= _MIN_OVERLAP_MULTI:
        return best_id

    return None
