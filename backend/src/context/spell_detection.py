"""Spell detection: explicit formulas, aliases, fuzzy matching, and intent extraction.

Detects spell casts from player input using multi-priority matching:
1. Exact match multi-word spell names
2. Fuzzy match spell name (70% threshold)
3. Explicit formula/legacy alias substring match
4. Fuzzy formula/name match (65% threshold)

Fuzzy (detect_spell_with_fuzzy) is the source of truth for spell detection.
Legacy is_spell_input/parse_spell_from_input now delegate to it (A2 unification).

Phase 4.6.2: Single-stage fuzzy + semantic phrase detection for all 7 rites.
Phase 4.7: Spell success calculation with specificity bonuses.
Phase 5.7: Intent validation to reduce false positives.
"""

import logging
import random
import re

from rapidfuzz import fuzz

from src.spells.definitions import SPELL_DEFINITIONS

logger = logging.getLogger(__name__)

# =============================================================================
# Semantic Phrases for Single-Stage Spell Detection
# =============================================================================

# Priority 1: Fuzzy match spell name (handles typos like "legulemancy")
# Priority 2: Exact match spell ID
# Priority 3: Semantic phrase substring match
SPELL_SEMANTIC_PHRASES: dict[str, list[str]] = {
    "mnemonic_delving": [
        "memory, open",
        "memory open",
        "memory, open on",
        "mnemonic_delving",
        "mnemonic delving",
        "legulemancy",
        "read mind",
        "read her mind",
        "read his mind",
        "read their mind",
        "peek into mind",
        "peek into thought",
        "search memor",  # Catches "memories", "memory"
        "probe mind",
        "enter mind",
        "invade mind",
        "see thought",
        # Russian (player freeform)
        "погружение в память",
        "чтение мыслей",
        "заглянуть в мысли",
        "прочитать мысли",
        "в её мысли",
        "в его мысли",
        "в память",
        "читать мысли",
        "чужая память, отворись",
        "чужая память отворись",
    ],
    "unveil": [
        "veil, dissolve",
        "veil dissolve",
        "hidden things, reveal yourselves",
        "hidden things reveal yourselves",
        "unveil",
        "reveal hidden",
        "show hidden",
        "uncover hidden",
        "make visible",
        "снять покров",
        "снять покровы",
        "раскрыть скрытое",
        "явить скрытое",
        "показать скрытое",
        "снять маскировку",
        "проявить невидимые",
        "скрытое, явись",
        "скрытое явись",
    ],
    "raise_the_lamp": [
        "trace, gleam",
        "trace gleam",
        "light, show the trace",
        "light show the trace",
        "raise_the_lamp",
        "raise the lamp",
        "light up",
        "illuminate",
        "brighten",
        "cast light",
        "поднять лампу",
        "подними лампу",
        "осветить",
        "освещаю",
        "зажечь лампу",
        "свет лампы",
        "свет, укажи след",
        "свет укажи след",
    ],
    "sense_presence": [
        "presence, answer",
        "presence answer",
        "presence, make yourself known",
        "presence make yourself known",
        "sense_presence",
        "sense presence",
        "homenum unveil",
        "homenum",
        "detect people",
        "detect person",
        "find people",
        "locate people",
        "ощутить присутствие",
        "почувствовать присутствие",
        "ощущаю присутствие",
        "кто рядом",
        "есть ли кто",
        "присутствие, отзовись",
        "присутствие отзовись",
    ],
    "identify_substance": [
        "essence, speak",
        "essence speak",
        "essence, declare yourself",
        "essence declare yourself",
        "identify_substance",
        "specialis unveil",
        "specialis",
        "identify substance",
        "identify potion",
        "analyze substance",
        "опознать вещество",
        "определить вещество",
        "опознать зелье",
        "анализ вещества",
        "что за вещество",
        "суть, откройся",
        "суть откройся",
    ],
    "echo_reading": [
        "echo, speak",
        "echo speak",
        "echo_reading",
        "echo reading",
        "last spell",
        "focus history",
        "previous spell",
        "чтение эха",
        "прочитать эхо",
        "эхо на фокусе",
        "последнее заклинание",
        "история фокуса",
        "отзвук чар, явись",
        "отзвук чар явись",
    ],
    "mend": [
        "shards, unite",
        "shards unite",
        "broken thing, be whole",
        "broken thing be whole",
        "broken glass, be whole",
        "mend",
        "repair this",
        "fix this",
        "mend this",
        "restore this",
        "починить",
        "почини",
        "восстановить",
        "чинить",
        "собрать разбитое",
        "разбитое, сойдись",
        "разбитое сойдись",
        "разбитое стекло, сойдись",
        "разбитое стекло сойдись",
    ],
}

# 6 safe investigation rites (excludes Mnemonic Delving which uses trust-based system)
SAFE_INVESTIGATION_SPELLS = {
    "unveil",
    "raise_the_lamp",
    "sense_presence",
    "identify_substance",
    "echo_reading",
    "mend",
}

# Intent phrases that grant +10% bonus
INTENT_PHRASES = [
    "to find",
    "to reveal",
    "to show",
    "to uncover",
    "to detect",
    "to search",
    "to check",
    "to look",
    "to examine",
    "to inspect",
    "to see",
    "searching for",
    "looking for",
    "checking for",
    # Russian
    "чтобы найти",
    "чтобы увидеть",
    "чтобы проверить",
    "чтобы осмотреть",
    "чтобы раскрыть",
    "ищу",
    "проверяю",
    "осматриваю",
]


# =============================================================================
# Input Extraction Helpers
# =============================================================================


def extract_target_from_input(text: str) -> str | None:
    """Extract target from spell input.

    Patterns:
    - "cast spell on TARGET"
    - "cast spell at TARGET"
    - "use spell on TARGET"

    Args:
        text: Player input

    Returns:
        Target string or None

    Examples:
        >>> extract_target_from_input("cast unveil on desk")
        'desk'
        >>> extract_target_from_input("use mnemonic_delving on elena")
        'elena'
    """
    match = re.search(
        r"\b(?:on|at|in|into|within|beyond|through|near|beside|over)\s+(.+)$",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip(" \t\n.,!?;:…\"'«»")
    # Russian prepositions (на / по / со / с / у / к)
    match_ru = re.search(
        r"(?:^|[\s,])(?:на|по|со|с|у|к|в|во|за|под|над)\s+(.+)$",
        text,
        re.IGNORECASE,
    )
    if match_ru:
        return match_ru.group(1).strip(" \t\n.,!?;:…\"'«»")

    return None


def extract_intent_from_input(text: str) -> str | None:
    """Extract search intent from Mnemonic Delving input.

    Simplified approach: detect strong intent verbs + capture everything after.

    Patterns:
    - "to [verb] about X" where verb = find out, learn, discover, see, know, understand
    - "to [verb] X" where X doesn't start with "about"
    - "about X"

    Args:
        text: Player input

    Returns:
        Intent string or None

    Examples:
        >>> extract_intent_from_input("read her mind to find out about cassian")
        'cassian'
        >>> extract_intent_from_input("mnemonic_delving to find out where he was")
        'where he was'
        >>> extract_intent_from_input("to learn elena's secrets")
        "elena's secrets"
        >>> extract_intent_from_input("mnemonic_delving about the crime")
        'the crime'
    """
    patterns = [
        r"to\s+(?:find\s+out|learn|discover|see|know|understand|uncover|reveal)\s+about\s+(.+)$",
        r"to\s+(?:find\s+out|learn|discover|see|know|understand|uncover|reveal)\s+(.+)$",
        r"\babout\s+(.+)$",
        r"(?:чтобы\s+)?(?:узнать|выяснить|понять)\s+(?:о|об|обо|про)?\s*(.+)$",
        r"\b(?:о|об|обо|про|на)\s+(.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


# =============================================================================
# Spell Success Calculation
# =============================================================================


def calculate_specificity_bonus(player_input: str) -> int:
    """Calculate specificity bonus (0%, +10%, or +20%).

    Rewards players for thoughtful spell usage with specific targets and intent.

    Args:
        player_input: Full player input text

    Returns:
        0, 10, or 20 (percentage points)

    Examples:
        >>> calculate_specificity_bonus("Unveil")
        0
        >>> calculate_specificity_bonus("Unveil on desk")
        10  # +10% for target
        >>> calculate_specificity_bonus("Unveil on desk to find letters")
        20  # +10% target + 10% intent
    """
    bonus = 0

    target_pattern = (
        r"\b(?:on|at|in|into|within|beyond|toward|against|around|near|"
        r"across|through|over|along|на|в|во|за|под|над|по|со|с|у|к|через)\s+\w+"
    )
    if re.search(target_pattern, player_input, re.IGNORECASE):
        bonus += 10

    input_lower = player_input.lower()
    if any(phrase in input_lower for phrase in INTENT_PHRASES):
        bonus += 10

    return bonus


def calculate_spell_success(
    spell_id: str,
    player_input: str,
    attempts_in_location: int,
    location_id: str,
) -> bool:
    """Calculate whether spell cast succeeds.

    Base rate 70%, specificity bonus 0-20%, decline -10% per attempt, floor 10%.

    Args:
        spell_id: "unveil", "raise_the_lamp", etc.
        player_input: Full player input text
        attempts_in_location: Number of times THIS spell cast in THIS location
        location_id: Current location (for logging/debugging)

    Returns:
        True if spell succeeds, False if fails

    Examples:
        >>> calculate_spell_success("unveil", "Unveil on desk to find clues", 0, "library")
        # 70 + 10 + 10 - 0 = 90% -> likely True
        >>> calculate_spell_success("unveil", "Unveil", 6, "library")
        # 70 + 0 + 0 - 60 = 10% (floor) -> likely False
    """
    base_rate = 70
    specificity_bonus = calculate_specificity_bonus(player_input)
    decline_penalty = attempts_in_location * 10
    success_rate = base_rate + specificity_bonus - decline_penalty
    success_rate = max(10, success_rate)

    roll = random.random() * 100
    success = roll < success_rate

    logger.info(
        "SPELL ROLL: %s @ %s | base=%d + specificity=%d - decline=%d = %d%% | roll=%.1f | %s",
        spell_id, location_id, base_rate, specificity_bonus, decline_penalty,
        success_rate, roll, "SUCCESS" if success else "FAILURE",
    )

    return success


# =============================================================================
# Mnemonic Delving Success Calculation
# =============================================================================


def calculate_mnemonic_delving_specificity_bonus(player_input: str) -> int:
    """Calculate specificity bonus for Mnemonic Delving.

    Returns 0 or 30:
    - +30% if intent specified ("to find out about X", "about X")
    - No target bonus: target is always obvious (the witness being interrogated)

    Args:
        player_input: Player's text input

    Returns:
        0 or 30 (percentage points)

    Examples:
        >>> calculate_mnemonic_delving_specificity_bonus("mnemonic_delving")
        0
        >>> calculate_mnemonic_delving_specificity_bonus("mnemonic_delving to find out about cassian")
        30
        >>> calculate_mnemonic_delving_specificity_bonus("mnemonic_delving about the crime")
        30
    """
    intent = extract_intent_from_input(player_input)
    return 30 if intent else 0


def calculate_mnemonic_delving_success(
    player_input: str,
    attempts_on_witness: int,
    witness_id: str,
) -> tuple[bool, int, int, int, float]:
    """Calculate Mnemonic Delving success rate.

    Base rate: 30% (risky spell, lower than safe 70%)
    Specificity bonus: +30% if intent specified (no target - always witness)
    Decline penalty: -10% per attempt on this witness
    Floor: 10% minimum

    Args:
        player_input: Player's text input
        attempts_on_witness: Spell cast count on this witness
        witness_id: Witness ID (for logging)

    Returns:
        Tuple of (success, success_rate, specificity_bonus, decline_penalty, roll)
    """
    base_rate = 30
    specificity_bonus = calculate_mnemonic_delving_specificity_bonus(player_input)
    decline_penalty = attempts_on_witness * 10
    success_rate = base_rate + specificity_bonus - decline_penalty
    success_rate = max(10, success_rate)

    roll = random.random() * 100
    success = roll < success_rate

    return success, success_rate, specificity_bonus, decline_penalty, roll


def _phrase_words_match_span(phrase: str, span: str, text_lower: str) -> bool:
    """Require each phrase token to appear in input/span (with typo tolerance)."""
    span_words = span.split()
    for word in phrase.split():
        if word in text_lower or word in span:
            continue
        if len(word) < 4:
            if word not in span_words:
                return False
            continue
        if any(fuzz.ratio(word, sw) > 75 for sw in span_words):
            continue
        return False
    return True


# =============================================================================
# Intent Validation (Phase 5.7)
# =============================================================================


def _explicit_spell_phrases(spell_id: str) -> list[str]:
    """Return display formulas and legacy names that explicitly invoke a rite."""
    spell = SPELL_DEFINITIONS.get(spell_id, {})
    phrases: list[str] = [
        str(spell.get("formula_en", "")),
        str(spell.get("formula_ru", "")),
        str(spell.get("example_en", "")),
        str(spell.get("example_ru", "")),
        str(spell.get("name", "")),
        spell_id,
        spell_id.replace("_", " "),
    ]
    for field in ("legacy_names_en", "legacy_names_ru"):
        phrases.extend(str(value) for value in spell.get(field, []))
    return list(dict.fromkeys(phrase.lower() for phrase in phrases if phrase.strip()))


def _is_valid_spell_cast(
    text: str, spell_name: str, spell_id: str, matched_word: str | None = None
) -> bool:
    """Check if spell match represents actual cast intent (not just mention).

    Phase 5.7: Improved spell detection to reduce false positives.

    Requires EITHER:
    1. Action verb present ("cast", "use", "casting", etc.)
    2. Explicit formula or legacy name at sentence start

    AND excludes questions (ends with "?").

    Args:
        text: Player input text
        spell_name: Canonical spell name (e.g., "unveil")
        spell_id: Spell ID (e.g., "unveil")
        matched_word: The actual word matched (for typos, e.g., "revelo")

    Returns:
        True if valid spell cast intent, False if just mention
    """
    text_lower = text.lower().strip()

    # Rule 0: Exclude questions - never cast intent
    if text_lower.endswith("?"):
        return False

    # Rule 1: Action verb present
    action_verbs = [
        "cast",
        "casting",
        "use",
        "try",
        "perform",
        "spell",
        "execute",
        "do",
        "invoke",
        "channel",
        # Russian
        "применить",
        "применю",
        "использую",
        "использовать",
        "колдую",
        "читать",
        "прочитать",
        "наложить",
        "накладываю",
        "сотворить",
        "творить",
    ]
    intent_phrases = [
        "i want to",
        "i'll",
        "let me",
        "going to",
        "gonna",
        "i will",
        "i'm casting",
        "im casting",
        "i am casting",
        "хочу",
        "давай",
        "сейчас",
        "я применяю",
        "я использую",
        "я заклинаю",
    ]

    explicit_phrases = _explicit_spell_phrases(spell_id)
    explicit_tokens = {
        token
        for phrase in explicit_phrases
        for token in phrase.split()
        if len(token) >= 4
    }

    has_action = any(
        re.search(rf"\b{re.escape(verb)}\b", text_lower) for verb in action_verbs
    ) or any(phrase in text_lower for phrase in intent_phrases)
    has_explicit_name = any(phrase in text_lower for phrase in explicit_phrases)
    has_fuzzy_explicit_name = bool(
        matched_word
        and any(fuzz.ratio(matched_word.lower(), token) > 70 for token in explicit_tokens)
    )

    # Rule 1: Explicit wrapper plus formula/name anywhere in the input.
    if has_action and (has_explicit_name or has_fuzzy_explicit_name):
        return True

    # Rule 2: Explicit formula or legacy name at sentence start.
    cleaned_start = text_lower.lstrip("\"'!.,-; ")

    for phrase in explicit_phrases:
        if cleaned_start.startswith(phrase):
            return True

    # A fuzzy match is allowed only when the matched token starts the message
    # and is close to an explicit formula/name token. Generic semantic phrases
    # ("repair this", "show hidden") do not invoke rites by themselves.
    if matched_word and cleaned_start.startswith(matched_word.lower()):
        if has_fuzzy_explicit_name:
            return True

    return False


# =============================================================================
# Main Spell Detection
# =============================================================================


def detect_spell_with_fuzzy(text: str) -> tuple[str | None, str | None]:
    """Single-stage spell detection using fuzzy matching + semantic phrases.

    Detects ANY of the 7 rites with typo tolerance and explicit invocation language.
    Performance: 1-2ms per call (acceptable overhead vs 800ms LLM call)

    Phase 5.7: Added intent validation to reduce false positives.
    Now requires an action verb or explicit formula/name at sentence start.

    Priority order:
    1. Exact match formulas and legacy names first
    2. Fuzzy match formula/name (70% threshold for typos)
    3. Exact match spell ID in text
    4. Explicit alias substring match

    Args:
        text: Player input text

    Returns:
        (spell_id, target) or (None, None) if no spell detected

    Examples:
        >>> detect_spell_with_fuzzy("use mnemonic_delving on elena")
        ('mnemonic_delving', 'elena')

        >>> detect_spell_with_fuzzy("cast unveil on desk")
        ('unveil', 'desk')

        >>> detect_spell_with_fuzzy("Unveil!")
        ('unveil', None)

        >>> detect_spell_with_fuzzy("Do you know unveil?")
        (None, None)  # Question - no cast intent

        >>> detect_spell_with_fuzzy("I used unveil earlier")
        (None, None)  # Past tense mention - no cast intent
    """
    text_lower = text.lower().strip()

    # Early exit: Questions never indicate spell casting
    if text_lower.endswith("?"):
        return None, None

    # Order spells with multi-word names first to avoid partial matches
    spell_order = [
        "sense_presence",
        "identify_substance",
        "echo_reading",
        "mnemonic_delving",
        "unveil",
        "raise_the_lamp",
        "mend",
    ]

    # Priority 1: Exact match multi-word spell names (before fuzzy)
    for spell_id in spell_order:
        spell_def = SPELL_DEFINITIONS.get(spell_id)
        if not spell_def:
            continue

        spell_name = spell_def["name"].lower()

        if spell_name in text_lower:
            if _is_valid_spell_cast(text, spell_name, spell_id):
                target = extract_target_from_input(text)
                return spell_id, target

        if spell_id.replace("_", " ") in text_lower:
            if _is_valid_spell_cast(text, spell_name, spell_id):
                target = extract_target_from_input(text)
                return spell_id, target

    # Priority 2: Fuzzy match spell name (handles typos)
    for spell_id in spell_order:
        spell_def = SPELL_DEFINITIONS.get(spell_id)
        if not spell_def:
            continue

        spell_name = spell_def["name"].lower()

        words = text_lower.split()
        for word in words:
            if word.startswith(("reveal", "repair")) and len(word) <= 7:
                continue  # common partial words fuzz-close to unveil/mend; skip to avoid false positives on "reveal something"
            matched = False
            if fuzz.ratio(word, spell_name) > 70:
                matched = True
            else:
                # Also fuzzy words vs semantic phrases (supports "homnum" -> sense_presence)
                phrases = SPELL_SEMANTIC_PHRASES.get(spell_id, [])
                for phrase in phrases:
                    if len(phrase) >= 3 and fuzz.ratio(word, phrase) > 70:
                        matched = True
                        break
            if matched:
                if _is_valid_spell_cast(text, spell_name, spell_id, matched_word=word):
                    target = extract_target_from_input(text)
                    return spell_id, target

    # Priority 3: Semantic phrase match (exact substring)
    for spell_id in spell_order:
        spell_def = SPELL_DEFINITIONS.get(spell_id)
        if not spell_def:
            continue
        spell_name = spell_def["name"].lower()

        phrases = SPELL_SEMANTIC_PHRASES.get(spell_id, [])
        for phrase in phrases:
            if phrase in text_lower:
                if _is_valid_spell_cast(text, spell_name, spell_id):
                    target = extract_target_from_input(text)
                    return spell_id, target

    # Priority 3.5: Fuzzy phrase match (catches typos like "reed her minde")
    for spell_id in spell_order:
        spell_def = SPELL_DEFINITIONS.get(spell_id)
        if not spell_def:
            continue
        spell_name = spell_def["name"].lower()

        phrases = SPELL_SEMANTIC_PHRASES.get(spell_id, [])
        for phrase in phrases:
            if len(phrase) > 4:
                score = fuzz.partial_ratio(phrase, text_lower)
                if score <= 65:
                    continue
                align = fuzz.partial_ratio_alignment(phrase, text_lower)
                span = text_lower[align.dest_start : align.dest_end]
                if fuzz.ratio(phrase, span) <= 65:
                    continue
                if not _phrase_words_match_span(phrase, span, text_lower):
                    continue
                if _is_valid_spell_cast(text, spell_name, spell_id):
                    target = extract_target_from_input(text)
                    return spell_id, target

    return None, None


def detect_focused_mnemonic_delving(text: str) -> tuple[bool, str | None]:
    """Detect if Mnemonic Delving has specific search intent.

    Focused: "read her mind to find out about cassian"
    Unfocused: "use mnemonic_delving on her"

    Args:
        text: Player input

    Returns:
        (is_focused, search_target)

    Examples:
        >>> detect_focused_mnemonic_delving("read her mind to find out about cassian")
        (True, 'cassian')
        >>> detect_focused_mnemonic_delving("use mnemonic_delving on elena")
        (False, None)
    """
    intent = extract_intent_from_input(text)
    if intent:
        return True, intent
    else:
        return False, None


def parse_spell_from_input(player_input: str) -> tuple[str | None, str | None]:
    """Parse spell name and target from player input.

    Delegates to detect_spell_with_fuzzy (unified source of truth) to ensure
    identical behavior for is_spell + target extraction across routes and
    narrator (fuzzy + semantic + intent validation). Supports typos like
    "revelo", "homnum", "I'm casting" etc.

    Args:
        player_input: Raw player input text

    Returns:
        Tuple of (spell_id, target) or (None, None) if no spell detected
    """
    return detect_spell_with_fuzzy(player_input)


def _normalize_spell_name(spell_raw: str) -> str | None:
    """Normalize spell name to spell ID.

    Args:
        spell_raw: Raw spell name from input (e.g., "echo reading", "unveil")

    Returns:
        Spell ID or None if not found
    """
    spell_normalized = spell_raw.lower().replace(" ", "_")
    if spell_normalized in SPELL_DEFINITIONS:
        return spell_normalized

    for spell_id, spell_def in SPELL_DEFINITIONS.items():
        if spell_def["name"].lower() == spell_raw.lower():
            return spell_id
        if spell_raw.lower() in spell_def["name"].lower():
            return spell_id

    return None


def is_spell_input(player_input: str) -> bool:
    """Check if player input contains a spell cast.

    Delegates to detect_spell_with_fuzzy (unified source of truth).

    Args:
        player_input: Raw player input text

    Returns:
        True if input contains spell casting, False otherwise
    """
    spell_id, _ = detect_spell_with_fuzzy(player_input)
    return spell_id is not None
