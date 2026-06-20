"""Natural language location command parser.

Phase 5.2: Detect "go to X", "visit X", "head to X" commands in player input.
Uses token-overlap matching with SequenceMatcher typo tolerance and verb stemming.
"""

import re
from difflib import SequenceMatcher


def _stem_verb(word: str) -> str:
    """Strip common verb suffixes to match base forms."""
    if word.endswith("ting") and len(word) > 5:
        # navigating -> navigat, directing -> direct
        base = word[:-3]
        if base.endswith("t"):
            return base  # navigat is close enough for regex
        return base
    if word.endswith("ing") and len(word) > 4:
        base = word[:-3]
        if len(base) > 2 and base[-1] == base[-2]:
            return base[:-1]  # running -> run
        return base
    if word.endswith("ed") and len(word) > 4:
        base = word[:-2]
        if len(base) > 2 and base[-1] == base[-2]:
            return base[:-1]
        return base
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


class LocationCommandParser:
    """Parse natural language location change commands.

    Detects patterns like:
    - "go to dormitory" / "going to dormitory" / "I'm going to the dormitory"
    - "visit the library"
    - "head to great hall" / "heading to great hall"
    - "go to the corridor" (partial -> third_floor_corridor)
    - "directing to the iron lodge room"

    Uses verb stemming + token-overlap scoring with SequenceMatcher typo tolerance.
    """

    # Base navigation verbs (stemmed forms matched at runtime)
    # Include stemmed forms (e.g. "mov" from "moving") alongside base forms
    _NAV_VERB_STEMS = {
        "go", "head", "travel", "walk", "move", "mov", "navigate", "navigat",
        "proceed", "visit", "return", "direct", "advance", "advanc",
        "enter", "approach",
    }

    # Exploration verbs — lower confidence for navigation
    _EXPLORE_VERB_STEMS = {
        "check", "explore", "explor", "investigate", "investigat",
        "examine", "examin", "search",
    }

    # Precompiled regex for extracting target after verb + preposition
    _TARGET_RE = re.compile(
        r"(?:to|toward|towards)\s+(?:the\s+)?(\w+(?:\s+\w+){0,3})",
        re.IGNORECASE,
    )

    # Fallback: verb directly followed by target (no preposition)
    # "visit library", "enter kitchens"
    _DIRECT_TARGET_RE = re.compile(
        r"(?:the\s+)?(\w+(?:\s+\w+){0,3})",
        re.IGNORECASE,
    )

    def __init__(
        self,
        locations: list[str],
        name_to_id: dict[str, str] | None = None,
        fuzzy_threshold: float = 0.75,
    ):
        """Initialize parser with known locations.

        Args:
            locations: Valid location IDs (e.g., ["library", "third_floor_corridor"])
            name_to_id: Display name → ID mapping (e.g., {"Sealed Stacks": "library"})
            fuzzy_threshold: Min SequenceMatcher ratio for token typo tolerance
        """
        self.locations = locations
        self.fuzzy_threshold = fuzzy_threshold

        # Lookup: "great hall" -> "great_hall", "great_hall" -> "great_hall"
        self._location_lookup: dict[str, str] = {}
        for loc in locations:
            self._location_lookup[loc.lower()] = loc
            self._location_lookup[loc.lower().replace("_", " ")] = loc

        # Pre-compute all fuzzy match candidates: (tokens, loc_id)
        self._candidates: list[tuple[list[str], str]] = []
        for loc in locations:
            self._candidates.append((loc.lower().replace("_", " ").split(), loc))

        if name_to_id:
            for name, loc_id in name_to_id.items():
                lower_name = name.lower()
                self._location_lookup[lower_name] = loc_id
                self._candidates.append((lower_name.split(), loc_id))

    def parse(self, input_text: str) -> str | None:
        """Detect location change command in input."""
        if not input_text:
            return None

        lower = input_text.lower().strip()
        words = lower.split()

        # Find navigation verb in input (with stemming)
        verb_pos = None
        for i, w in enumerate(words):
            # Strip possessive/contractions: "i'm" -> "i", but check next word
            clean = re.sub(r"[''`].*$", "", w)
            stem = _stem_verb(clean)
            if stem in self._NAV_VERB_STEMS:
                verb_pos = i
                break
            if stem in self._EXPLORE_VERB_STEMS:
                verb_pos = i
                break

        if verb_pos is None:
            # No verb found — check fallback (location name + command context)
            return self._fallback_match(lower)

        # Extract target: everything after verb + optional preposition/article
        after_verb = " ".join(words[verb_pos + 1:])

        # Try "to/toward the X" pattern first
        m = self._TARGET_RE.search(after_verb)
        if m:
            target = m.group(1).strip()
            loc = self._fuzzy_match(target)
            if loc:
                return loc

        # Try direct target (no preposition): "visit library", "enter kitchens"
        # Also allow explore verbs — "check the corridor" is navigation
        m = self._DIRECT_TARGET_RE.search(after_verb)
        if m:
            target = m.group(1).strip()
            loc = self._fuzzy_match(target)
            if loc:
                return loc

        return None

    def has_navigation_intent(self, input_text: str) -> bool:
        """Check if input expresses navigation intent (even if no location matched).

        Used to generate narrator hints when location detection fails.
        Detects both nav verbs ("go to X") and explore verbs ("check the X").
        """
        if not input_text:
            return False
        lower = input_text.lower()
        words = lower.split()
        for w in words:
            clean = re.sub(r"[''`].*$", "", w)
            stem = _stem_verb(clean)
            if stem in self._NAV_VERB_STEMS:
                if re.search(r"\b(to|toward|towards)\b", lower):
                    return True
            if stem in self._EXPLORE_VERB_STEMS:
                return True
        return False

    def _fallback_match(self, lower_input: str) -> str | None:
        """Match location name in input with navigation context check."""
        for loc_key, loc_id in self._location_lookup.items():
            if loc_key in lower_input:
                if self._is_command_context(lower_input, loc_key):
                    return loc_id
        return None

    def _fuzzy_match(self, target: str) -> str | None:
        """Match target against known locations via token overlap.

        Tokenizes target and each location ID, scores by fraction of
        location tokens matched. Uses SequenceMatcher for typo tolerance.
        """
        target_lower = target.lower().strip()

        # Fast path: exact lookup
        if target_lower in self._location_lookup:
            return self._location_lookup[target_lower]

        target_tokens = target_lower.split()
        best_match: str | None = None
        best_score = 0.0
        best_matched_count = 0

        for loc_tokens, loc_id in self._candidates:
            if not loc_tokens:
                continue

            matched = 0
            for tt in target_tokens:
                for lt in loc_tokens:
                    if tt == lt:
                        matched += 1
                        break
                    if SequenceMatcher(None, tt, lt).ratio() >= self.fuzzy_threshold:
                        matched += 1
                        break

            score = matched / len(loc_tokens)

            if matched > 0 and (
                score > best_score
                or (score == best_score and matched > best_matched_count)
            ):
                best_score = score
                best_match = loc_id
                best_matched_count = matched

        if best_score >= 0.3:
            return best_match

        return None

    def _is_command_context(self, input_text: str, location: str) -> bool:
        """Check if location mention has navigation context before it."""
        all_stems = self._NAV_VERB_STEMS | self._EXPLORE_VERB_STEMS
        loc_index = input_text.find(location)
        if loc_index <= 0:
            return False

        before = input_text[:loc_index]
        for w in before.split():
            clean = re.sub(r"[''`].*$", "", w)
            if _stem_verb(clean) in all_stems:
                return True
            if clean in {"to", "toward", "towards", "back"}:
                return True

        return False
