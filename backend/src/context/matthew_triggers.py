"""Matthew spirit companion — LEGACY trigger selection logic.

NOTE: Phase 4.1 replaces this with LLM-powered responses (see matthew_llm.py).
This module is kept for:
1. Backward compatibility with existing /inner-voice/check endpoint
2. Fallback if LLM calls fail
3. Reference for trigger structure

For Matthew responses, use:
- POST /api/case/{case_id}/matthew/auto-comment (LLM-powered)
- POST /api/case/{case_id}/matthew/chat (LLM-powered)

LEGACY SYSTEM - Handles tier-based trigger selection with:
- Priority tier evaluation (3 > 2 > 1)
- Random selection within tier
- Rare trigger chance (7%)
- Fired trigger exclusion
"""

import random
import re
from functools import lru_cache
from typing import Any

from src.case_store.loader import load_case


def select_matthew_trigger(
    triggers_by_tier: dict[int, list[dict[str, Any]]],
    evidence_count: int,
    fired_triggers: list[str],
) -> dict[str, Any] | None:
    """Select Matthew companion trigger to fire.

    Algorithm:
    1. Check Tier 3 first (evidence_count >= 6), then Tier 2 (>= 3), then Tier 1
    2. Skip tier if evidence_count doesn't meet tier threshold
    3. Filter to unfired triggers with met conditions
    4. 7% chance for rare triggers if available
    5. Random selection within tier
    6. Return None if no eligible triggers

    Args:
        triggers_by_tier: Dict mapping tier (1/2/3) to list of trigger dicts
        evidence_count: Current evidence count
        fired_triggers: List of already-fired trigger IDs

    Returns:
        Selected trigger dict or None if no eligible triggers
    """
    # Tier thresholds - tier only eligible if evidence_count meets minimum
    tier_thresholds = {
        3: 6,  # Tier 3: evidence_count >= 6
        2: 3,  # Tier 2: evidence_count >= 3
        1: 0,  # Tier 1: always eligible (evidence_count >= 0)
    }

    # Check tiers in priority order (highest first)
    for tier in [3, 2, 1]:
        # Skip tier if evidence_count doesn't meet threshold
        if evidence_count < tier_thresholds[tier]:
            continue

        tier_triggers = triggers_by_tier.get(tier, [])

        # Filter to eligible (condition met, not fired)
        eligible = [
            t
            for t in tier_triggers
            if t.get("id") not in fired_triggers
            and _check_condition(t.get("condition", ""), evidence_count)
        ]

        if not eligible:
            continue

        # Separate rare from regular
        rare = [t for t in eligible if t.get("is_rare", False)]
        regular = [t for t in eligible if not t.get("is_rare", False)]

        # 7% chance for rare trigger if available
        if rare and random.random() < 0.07:
            return random.choice(rare)

        # Otherwise pick regular
        if regular:
            return random.choice(regular)

        # Fallback to rare if no regular triggers
        if rare:
            return random.choice(rare)

    return None  # No eligible triggers  # No eligible triggers


def _check_condition(condition: str, evidence_count: int) -> bool:
    """Evaluate evidence_count condition.

    Supports: >, >=, ==, <, <=, !=

    Args:
        condition: Condition string (e.g., "evidence_count>=3")
        evidence_count: Current evidence count

    Returns:
        True if condition is met
    """
    if not condition:
        return True  # No condition = always eligible

    # Parse "evidence_count>5" -> operator=">" threshold=5
    match = re.match(r"evidence_count\s*([<>=!]+)\s*(\d+)", condition, re.IGNORECASE)
    if not match:
        return False  # Malformed condition

    operator, threshold = match.group(1), int(match.group(2))

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

    return False


@lru_cache(maxsize=16)
def load_matthew_triggers(case_id: str) -> dict[int, list[dict[str, Any]]]:
    """Load Matthew companion triggers from case YAML.

    Loads and caches triggers organized by tier.

    Args:
        case_id: Case identifier

    Returns:
        Dict mapping tier (1/2/3) to list of trigger dicts.
        Returns empty dict if no inner_voice section exists.
    """
    try:
        case_data = load_case(case_id)
    except FileNotFoundError:
        return {}

    case_section = case_data.get("case", case_data)
    inner_voice = case_section.get("inner_voice", {})

    if not inner_voice:
        return {}

    # Get the triggers section from inner_voice
    triggers_section = inner_voice.get("triggers", {})
    if not triggers_section:
        return {}

    triggers_by_tier: dict[int, list[dict[str, Any]]] = {}

    # Load triggers from each tier
    for tier_key in ["tier_1", "tier_2", "tier_3"]:
        tier_num = int(tier_key.split("_")[1])
        tier_triggers = triggers_section.get(tier_key, [])

        if tier_triggers:
            # Add tier number to each trigger for reference
            for trigger in tier_triggers:
                trigger["tier"] = tier_num

            triggers_by_tier[tier_num] = tier_triggers

    return triggers_by_tier


def clear_trigger_cache() -> None:
    """Clear cached triggers (useful for testing or hot-reload)."""
    load_matthew_triggers.cache_clear()
