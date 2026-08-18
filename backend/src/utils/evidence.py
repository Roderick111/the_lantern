"""Evidence trigger matching utilities.

Matches player input to evidence triggers and extracts evidence tags from responses.
"""

import re
from typing import Any

# Canonical form is [EVIDENCE_id]. Legacy [EVIDENCE: id] remains readable.
EVIDENCE_TAG_PATTERN = re.compile(
    r"\[EVIDENCE(?::\s*|_)([a-z0-9_]+)\s*\]", re.IGNORECASE
)
EVIDENCE_MARKER_SOURCE = r"\[EVIDENCE(?::\s*|_)[a-z0-9_]+\s*\]"
NO_EVIDENCE_MARKER = "[NO_EVIDENCE]"
RITE_CONTROL_MARKER_PATTERN = re.compile(
    r"\[(?:EVIDENCE|NO_EVIDENCE)[^\]]*\]", re.IGNORECASE
)
RITE_CONTROL_RESULT_PATTERN = re.compile(
    rf"(?:{EVIDENCE_MARKER_SOURCE}\s*)+$|\[NO_EVIDENCE\]\s*$",
    re.IGNORECASE,
)


def matches_trigger(player_input: str, triggers: list[str]) -> bool:
    """Check if player input matches any trigger keyword.

    Uses case-insensitive substring matching.

    Args:
        player_input: Raw player action text
        triggers: List of trigger phrases to match

    Returns:
        True if any trigger is found in player input
    """
    input_lower = player_input.lower()
    return any(trigger.lower() in input_lower for trigger in triggers)



def find_not_present_response(
    player_input: str,
    not_present: list[dict[str, Any]],
) -> str | None:
    """Find not_present response for player input (hallucination prevention).

    Args:
        player_input: Raw player action text
        not_present: List of not_present items with 'triggers' and 'response'

    Returns:
        Predefined response if triggers match, None otherwise
    """
    for item in not_present:
        triggers = item.get("triggers", [])
        if matches_trigger(player_input, triggers):
            response: str = item.get("response", "You search but find nothing of note.")
            return response

    return None


def extract_evidence_from_response(response: str) -> list[str]:
    """Extract evidence IDs from LLM response.

    Parses canonical [EVIDENCE_id] and legacy [EVIDENCE: id] tags.

    Args:
        response: LLM response text

    Returns:
        List of evidence IDs found in response
    """
    matches = EVIDENCE_TAG_PATTERN.findall(response)
    # Clean up extracted IDs (strip whitespace)
    return [m.strip() for m in matches]


def validate_rite_control_result(
    response: str,
    allowed_evidence_ids: set[str],
) -> tuple[bool, str | None]:
    """Validate terminal rite control output without inferring evidence."""
    markers = RITE_CONTROL_MARKER_PATTERN.findall(response)
    for marker in markers:
        if marker.upper() == NO_EVIDENCE_MARKER:
            continue
        if EVIDENCE_TAG_PATTERN.fullmatch(marker) is None:
            return False, "malformed_evidence_marker"

    evidence_ids = extract_evidence_from_response(response)
    has_no_evidence = NO_EVIDENCE_MARKER in response.upper()
    if evidence_ids and has_no_evidence:
        return False, "mixed_control_result"
    if any(evidence_id not in allowed_evidence_ids for evidence_id in evidence_ids):
        return False, "invalid_evidence_id"
    if not RITE_CONTROL_RESULT_PATTERN.search(response.rstrip()):
        return False, "missing_terminal_control_result"
    return True, None


def extract_rite_control_result(response: str) -> str | None:
    """Return terminal rite control result exactly as emitted."""
    match = RITE_CONTROL_RESULT_PATTERN.search(response.rstrip())
    return match.group(0).strip() if match else None


def normalize_rite_response(response: str, control_result: str | None) -> str:
    """Remove malformed/duplicate control markers and append validated result."""
    narration = RITE_CONTROL_MARKER_PATTERN.sub("", response).strip()
    if not control_result or control_result.upper() == NO_EVIDENCE_MARKER:
        return narration
    return f"{narration}\n\n{control_result}" if narration else control_result


def check_already_discovered(
    player_input: str,
    hidden_evidence: list[dict[str, Any]],
    discovered_ids: list[str],
) -> bool:
    """Check if player is asking about already-discovered evidence.

    Args:
        player_input: Raw player action text
        hidden_evidence: List of evidence dicts
        discovered_ids: List of already-discovered evidence IDs

    Returns:
        True if player is investigating something already found
    """
    for evidence in hidden_evidence:
        evidence_id = evidence.get("id", "")

        if evidence_id not in discovered_ids:
            continue

        triggers = evidence.get("triggers", [])
        if matches_trigger(player_input, triggers):
            return True

    return False


# Regex pattern for [FLAG: name] tags
FLAG_TAG_PATTERN = re.compile(r"\[FLAG:\s*(\w+)\]", re.IGNORECASE)


def extract_flags_from_response(response: str) -> list[str]:
    """Extract spell outcome flags from narrator response.

    Parses [FLAG: name] tags from response text. Used to detect
    spell consequences like relationship damage or mental strain.

    Example flags:
        - [FLAG: relationship_damaged] - Mnemonic Delving detected by target
        - [FLAG: mental_strain] - Backlash from Mind-shield shields

    Args:
        response: LLM narrator response text

    Returns:
        List of flag names found (e.g., ["relationship_damaged"])
    """
    matches = FLAG_TAG_PATTERN.findall(response)
    return [m.strip() for m in matches]
