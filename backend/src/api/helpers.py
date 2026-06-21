"""Shared helpers for route handlers.

Contains secret detection, investigation helpers, and state loading utilities.
"""

import asyncio
import logging
import re
import threading
from collections.abc import AsyncIterator
from typing import Any

from fastapi import HTTPException

from src.api.schemas import InvestigateRequest, InvestigateResponse
from src.case_store.loader import (
    get_first_location_id,
    get_location,
    list_locations,
    load_case,
    load_witnesses,
)
from src.context.spell_llm import calculate_spell_success
from src.state.persistence import load_player_state, save_player_state
from src.state.player_state import PlayerState
from src.utils.evidence import (
    check_already_discovered,
    extract_evidence_from_response,
    extract_flags_from_response,
)

# Shared SSE response headers for all streaming endpoints
SSE_HEADERS = {
    "X-Accel-Buffering": "no",
    "Cache-Control": "no-cache, no-store",
    "Connection": "keep-alive",
}

# SSE keepalive comment (browsers ignore these, but they keep the connection alive)
SSE_KEEPALIVE = ": keepalive\n\n"
_KEEPALIVE_INTERVAL = 15  # seconds


async def stream_with_keepalive(
    source: AsyncIterator[str],
) -> AsyncIterator[str]:
    """Wrap an async LLM chunk stream with periodic keepalive comments.

    Yields SSE comments every 15s of silence to prevent mobile
    browsers and proxies from dropping the connection.
    """
    aiter = source.__aiter__()
    while True:
        try:
            chunk = await asyncio.wait_for(
                aiter.__anext__(),
                timeout=_KEEPALIVE_INTERVAL,
            )
            yield chunk
        except TimeoutError:
            yield SSE_KEEPALIVE
        except StopAsyncIteration:
            return


logger = logging.getLogger(__name__)


# ============================================
# Secret Detection
# ============================================

_STOPWORDS = {
    "i",
    "me",
    "my",
    "myself",
    "we",
    "our",
    "ours",
    "ourselves",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
    "he",
    "him",
    "his",
    "himself",
    "she",
    "her",
    "hers",
    "herself",
    "it",
    "its",
    "itself",
    "they",
    "them",
    "their",
    "theirs",
    "themselves",
    "what",
    "which",
    "who",
    "whom",
    "this",
    "that",
    "these",
    "those",
    "am",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "having",
    "do",
    "does",
    "did",
    "doing",
    "a",
    "an",
    "the",
    "and",
    "but",
    "if",
    "or",
    "because",
    "as",
    "until",
    "while",
    "of",
    "at",
    "by",
    "for",
    "with",
    "about",
    "against",
    "between",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "to",
    "from",
    "up",
    "down",
    "in",
    "out",
    "on",
    "off",
    "over",
    "under",
    "again",
    "further",
    "then",
    "once",
}

DENIAL_PATTERNS = [
    "i didn't",
    "i did not",
    "i never",
    "i wasn't",
    "i was not",
    "not true",
    "that's not",
    "that is not",
    "absolutely not",
    "certainly not",
    "of course not",
    "don't know",
    "do not know",
    "no idea",
    "wouldn't tell",
    "can't tell",
    "cannot tell",
    "refuse to",
    "won't say",
    "will not say",
    "none of your",
    "mind your own",
    "how dare you",
    "preposterous",
    "ridiculous",
    "nonsense",
    "false",
    "untrue",
    "deny",
    "denied",
]

# Threshold for unified scorer (0.70 rejects 4/5 window matches = 0.68)
REVEAL_THRESHOLD = 0.70


def _stem(word: str) -> str:
    """Lightweight suffix-strip stemmer. No dependencies."""
    # Order matters: longest suffixes first
    if word.endswith("ying"):
        return word  # "lying", "dying" — don't strip
    if word.endswith("ing") and len(word) > 5:
        # running -> runn -> run (handle double consonant)
        base = word[:-3]
        if len(base) > 2 and base[-1] == base[-2]:
            return base[:-1]
        return base
    if word.endswith("tion") or word.endswith("sion"):
        return word[:-3]  # keep the root
    if word.endswith("ment") and len(word) > 6:
        return word[:-4]
    if word.endswith("ness") and len(word) > 6:
        return word[:-4]
    if word.endswith("ied") and len(word) > 4:
        return word[:-3] + "y"  # carried -> carry
    if word.endswith("ed") and len(word) > 4:
        base = word[:-2]
        if len(base) > 2 and base[-1] == base[-2]:
            return base[:-1]  # stopped -> stop
        return base
    if word.endswith("ly") and len(word) > 4:
        return word[:-2]
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"  # stories -> story
    if word.endswith("es") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _tokenize(text: str) -> list[str]:
    """Extract content words (lowercase, no stopwords, stemmed)."""
    return [_stem(w) for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOPWORDS]


def _keyword_overlap_score(response_tokens: set[str], keywords: list[str]) -> float:
    """Score how well response matches author-defined keywords.

    Each keyword phrase is scored by token overlap. Returns best match.
    """
    if not keywords:
        return 0.0

    best = 0.0
    for keyword in keywords:
        kw_tokens = _tokenize(keyword)
        if not kw_tokens:
            continue
        matched = sum(1 for t in kw_tokens if t in response_tokens)
        best = max(best, matched / len(kw_tokens))

    return best


def _content_overlap_score(
    response_tokens: list[str],
    secret_text: str,
    window_size: int = 5,
) -> float:
    """Score how much response reproduces secret text content.

    Sliding window: fraction of best window's tokens found in secret.
    Returns 0.0 if secret has fewer content words than window_size.
    """
    secret_tokens = set(_tokenize(secret_text))
    if len(secret_tokens) < window_size:
        return 0.0

    best = 0.0
    for i in range(len(response_tokens) - window_size + 1):
        window = response_tokens[i : i + window_size]
        matched = sum(1 for w in window if w in secret_tokens)
        best = max(best, matched / window_size)

    return best


def _denial_penalty(text_lower: str) -> float:
    """0.0 if response contains denial patterns, 1.0 if clean."""
    for denial in DENIAL_PATTERNS:
        if denial in text_lower:
            return 0.0
    return 1.0


def _evasion_penalty(text_lower: str, response_tokens: list[str]) -> float:
    """Detect question-echoing evasion. 0.0 if evasion, 1.0 if clean.

    Triggers when content words appear ONLY inside question sentences
    (ending with '?') and there's no affirmative framing.
    """
    # If no question marks, no evasion
    if "?" not in text_lower:
        return 1.0

    # Check if ALL content tokens appear only in question sentences
    # Split by '?' — everything before a '?' is a question clause
    raw_parts = text_lower.split("?")
    # Last part (after final '?') is non-question
    non_question_text = raw_parts[-1] if raw_parts else ""

    nq_tokens = set(_tokenize(non_question_text))

    # If content words exist outside questions → not evasion
    if nq_tokens - _STOPWORDS:
        # Check for affirmative framing in non-question part
        affirmatives = {"yes", "fine", "admit", "confess", "true", "right", "okay"}
        if nq_tokens & affirmatives:
            return 1.0
        # Has non-question content, probably not pure evasion
        return 1.0

    # All content is in questions — likely evasion
    return 0.0


def score_secret_revelation(
    response_text: str,
    keywords: list[str],
    secret_text: str,
) -> float:
    """Unified 0.0–1.0 score for how strongly response reveals a secret.

    Combines keyword overlap and content overlap, then applies
    denial and evasion penalties.
    """
    text_lower = response_text.lower()
    response_tokens = _tokenize(response_text)
    response_token_set = set(response_tokens)

    kw_score = _keyword_overlap_score(response_token_set, keywords)
    text_score = _content_overlap_score(response_tokens, secret_text)

    # Keyword is stronger signal, content overlap slightly discounted
    raw = max(kw_score, text_score * 0.85)

    # Apply filters — these reduce score toward 0
    raw *= _denial_penalty(text_lower)
    raw *= _evasion_penalty(text_lower, response_tokens)

    return raw


# ── Legacy API (preserved for call sites) ──


def is_affirmative_mention(keyword: str, text: str, lookback_chars: int = 40) -> bool:
    """Check if keyword appears affirmatively. Delegates to unified scorer."""
    return score_secret_revelation(text, [keyword], "") >= REVEAL_THRESHOLD


def detect_keyword_match(response: str, keywords: list[str]) -> bool:
    """Check if response affirmatively mentions any keywords."""
    if not keywords:
        return False
    return score_secret_revelation(response, keywords, "") >= REVEAL_THRESHOLD


def detect_secret_by_consecutive_words(
    response_text: str,
    secret_text: str,
    window_size: int = 5,
) -> bool:
    """Check if response reproduces secret text content."""
    return score_secret_revelation(response_text, [], secret_text) >= REVEAL_THRESHOLD


def detect_secrets_in_response(
    response_text: str,
    witness: dict[str, Any],
    witness_state: Any,
) -> tuple[list[str], dict[str, str]]:
    """Detect secrets revealed in a witness response.

    Returns:
        Tuple of (secrets_revealed IDs, secret_texts mapping)
    """
    secrets_revealed: list[str] = []
    all_secrets = witness.get("secrets", [])

    for secret in all_secrets:
        secret_id = secret.get("id", "")
        if secret_id and secret_id not in witness_state.secrets_revealed:
            secret_text = secret.get("text", "")
            secret_keywords = secret.get("keywords", [])

            score = score_secret_revelation(
                response_text,
                secret_keywords,
                secret_text,
            )
            if score >= REVEAL_THRESHOLD:
                witness_state.reveal_secret(secret_id)
                secrets_revealed.append(secret_id)

    secret_texts: dict[str, str] = {}
    for secret in all_secrets:
        secret_id = secret.get("id", "")
        if secret_id in secrets_revealed:
            secret_texts[secret_id] = secret.get("text", "").strip()

    return secrets_revealed, secret_texts


# ============================================
# State Loading Helpers — bounded LRU cache + SQLite persistence
# ============================================

_STATE_CACHE_MAX = 256
_CacheKey = tuple[str, str, str]
_state_cache: dict[_CacheKey, PlayerState] = {}
_cache_lock = threading.Lock()


def _cache_key(case_id: str, player_id: str, slot: str) -> _CacheKey:
    return (player_id, case_id, "autosave" if slot == "default" else slot)


def _cache_put(key: _CacheKey, state: PlayerState) -> None:
    """Insert into bounded LRU cache, evicting oldest if full."""
    with _cache_lock:
        _state_cache.pop(key, None)
        if len(_state_cache) >= _STATE_CACHE_MAX:
            oldest = next(iter(_state_cache))
            del _state_cache[oldest]
        _state_cache[key] = state


def load_slot_state(
    case_id: str,
    player_id: str,
    slot: str = "autosave",
) -> PlayerState | None:
    """Load player state — deep-copied from cache, or fresh from SQLite."""
    key = _cache_key(case_id, player_id, slot)
    with _cache_lock:
        cached = _state_cache.get(key)
        if cached is not None:
            _state_cache.pop(key)
            _state_cache[key] = cached
            return cached.model_copy(deep=True)

    state = load_player_state(case_id, player_id, slot)
    if state is not None:
        _cache_put(key, state)
        return state.model_copy(deep=True)
    return None


def clear_state_cache() -> None:
    """Clear all in-memory cached player states (for tests and admin tooling)."""
    with _cache_lock:
        _state_cache.clear()


def state_delta(state: PlayerState) -> dict[str, Any]:
    """Lightweight state slice for SSE done payloads (avoids full model_dump)."""
    return {
        "case_id": state.case_id,
        "current_location": state.current_location,
        "discovered_evidence": list(state.discovered_evidence),
        "visited_locations": list(state.visited_locations),
        "save_revision": state.save_revision,
    }


def save_slot_state(
    state: PlayerState,
    player_id: str,
    slot: str = "autosave",
) -> None:
    """Save player state — persist to SQLite, then update cache."""
    key = _cache_key(state.case_id, player_id, slot)
    save_player_state(state.case_id, player_id, state, slot)
    _cache_put(key, state.model_copy(deep=True))


def invalidate_state_cache(
    case_id: str,
    player_id: str,
    slot: str = "autosave",
) -> None:
    """Remove a specific entry from the state cache."""
    key = _cache_key(case_id, player_id, slot)
    with _cache_lock:
        _state_cache.pop(key, None)


def load_case_or_404(case_id: str) -> dict[str, Any]:
    """Load case data or raise 404."""
    try:
        return load_case(case_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


def load_or_create_state(
    case_id: str,
    player_id: str,
    case_data: dict[str, Any],
    slot: str = "autosave",
) -> PlayerState:
    """Load existing player state or create new one (uses cache)."""
    state = load_slot_state(case_id, player_id, slot)
    if state is None:
        first_location = get_first_location_id(case_data)
        state = PlayerState(case_id=case_id, current_location=first_location)
    return state


def build_case_context(case_data: dict[str, Any]) -> dict[str, Any]:
    """Build case context dict for LLM prompts."""
    case_section = case_data.get("case", case_data)

    victim = case_section.get("victim", {})
    victim_str = victim.get("name", "Unknown victim")
    if victim.get("status"):
        victim_str += f" ({victim['status']})"

    metadata = case_section.get("metadata", {})
    location = metadata.get("location", "Unknown location")

    suspects_list = case_section.get("suspects", [])
    suspects = [s.get("name", s.get("id", "Unknown")) for s in suspects_list]

    witnesses_list = case_section.get("witnesses", [])
    witnesses = [w.get("name", w.get("id", "Unknown")) for w in witnesses_list]

    return {
        "victim": victim_str,
        "location": location,
        "suspects": suspects,
        "witnesses": witnesses,
    }


def get_witness_history_summary(state: PlayerState) -> str:
    """Aggregate recent witness conversation history (last 5 interactions)."""
    all_exchanges = []

    for witness_id, w_state in state.witness_states.items():
        for interaction in w_state.conversation_history:
            all_exchanges.append(
                {
                    "witness": witness_id,
                    "question": interaction.question,
                    "response": interaction.response,
                    "timestamp": interaction.timestamp,
                }
            )

    all_exchanges.sort(key=lambda x: x["timestamp"])
    recent = all_exchanges[-5:]

    if not recent:
        return ""

    lines = []
    for ex in recent:
        lines.append(f"Player: {ex['question']}")
        lines.append(f"Witness ({ex['witness']}): {ex['response']}")
        lines.append("")

    return "\n".join(lines).strip()


# ============================================
# Investigation Helpers
# ============================================


def resolve_location(
    request: InvestigateRequest,
    case_data: dict[str, Any],
    slot: str = "autosave",
    existing_state: PlayerState | None = None,
    player_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Resolve and validate target location for investigation.

    Args:
        existing_state: Pre-loaded state to avoid redundant DB call.
    """
    target_location_id = request.location_id
    all_locations = list_locations(case_data)
    location_ids = [loc["id"] for loc in all_locations]

    if not target_location_id or target_location_id == "library":
        if target_location_id == "library" and "library" in location_ids:
            pass
        else:
            state = existing_state or load_player_state(request.case_id, player_id or getattr(request, "player_id", "default"), slot)
            if state and state.current_location:
                target_location_id = state.current_location
            elif location_ids:
                target_location_id = location_ids[0]
            else:
                raise HTTPException(status_code=500, detail="Case has no locations")

    if target_location_id not in location_ids:
        logger.warning(
            f"Invalid location '{target_location_id}' requested. "
            f"Falling back to default: {location_ids[0]}"
        )
        target_location_id = location_ids[0]

    try:
        location = get_location(case_data, target_location_id)
        return target_location_id, location
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Location not found: {target_location_id}")


def save_conversation_and_return(
    state: PlayerState,
    player_id: str,
    player_input: str,
    narrator_response: str,
    location_id: str,
    new_evidence: list[str],
    already_discovered: bool,
    slot: str = "autosave",
    evidence_names: dict[str, str] | None = None,
    location_changed: str | None = None,
) -> InvestigateResponse:
    """Save conversation to state and return investigation response."""
    state.add_conversation_message("player", player_input, location_id=location_id)
    state.add_conversation_message("narrator", narrator_response, location_id=location_id)
    state.add_narrator_conversation(player_input, narrator_response, location_id=location_id)
    save_slot_state(state, player_id, slot)
    return InvestigateResponse(
        narrator_response=narrator_response,
        new_evidence=new_evidence,
        evidence_names=evidence_names or {},
        already_discovered=already_discovered,
        location_changed=location_changed,
        updated_state=state.model_dump(mode="json"),
    )


def check_spell_already_discovered(
    spell_id: str | None,
    player_input: str,
    hidden_evidence: list[dict[str, Any]],
    discovered_ids: list[str],
) -> str | None:
    """Check if spell targets already-discovered evidence."""
    if not spell_id:
        return None
    if not check_already_discovered(player_input, hidden_evidence, discovered_ids):
        return None

    from backend.src.spells.definitions import get_spell

    spell_def = get_spell(spell_id)
    spell_name = spell_def.get("name") if spell_def else "the rite"
    return (
        f"You perform {spell_name}, but it reveals nothing new. "
        "The evidence has already given up its secrets."
    )


def calculate_spell_outcome(
    spell_id: str,
    player_input: str,
    state: PlayerState,
) -> str:
    """Calculate spell success/failure and update attempt counter."""
    spell_key = spell_id.lower()
    location_key = state.current_location
    attempts = state.spell_attempts_by_location.get(location_key, {}).get(spell_key, 0)

    success = calculate_spell_success(
        spell_id=spell_key,
        player_input=player_input,
        attempts_in_location=attempts,
        location_id=location_key,
    )
    spell_outcome = "SUCCESS" if success else "FAILURE"

    logger.info(
        f"Spell Cast: {spell_id} | Input: '{player_input}' | "
        f"Attempt #{attempts + 1} @ {location_key} | Outcome: {spell_outcome}"
    )

    if location_key not in state.spell_attempts_by_location:
        state.spell_attempts_by_location[location_key] = {}
    state.spell_attempts_by_location[location_key][spell_key] = attempts + 1

    return spell_outcome


def find_witness_for_mnemonic_delving(
    target: str | None,
    case_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Find witness data for Mnemonic Delving spell target."""
    if not target:
        return None
    for _, witness_data in case_data.get("witnesses", {}).items():
        witness_name = witness_data.get("name", "")
        if target.lower() in witness_name.lower():
            return witness_data
    return None


def process_spell_flags(
    narrator_response: str,
    spell_id: str | None,
    target: str | None,
    case_data: dict[str, Any],
    state: PlayerState,
) -> None:
    """Process spell outcome flags from narrator response."""
    flags = extract_flags_from_response(narrator_response)

    if "relationship_damaged" in flags and spell_id and target:
        for witness_id, witness_data in load_witnesses(case_data).items():
            witness_name = witness_data.get("name", "")
            if target.lower() in witness_name.lower():
                base_trust = witness_data.get("base_trust", 50)
                witness_state = state.get_witness_state(witness_id, base_trust)
                witness_state.adjust_trust(-15)
                state.update_witness_state(witness_state)
                break

    if "mental_strain" in flags:
        pass  # Future: player morale/health penalty


def extract_new_evidence(
    narrator_response: str,
    discovered_ids: list[str],
    state: PlayerState,
) -> list[str]:
    """Extract newly discovered evidence from LLM response [EVIDENCE: id] tags."""
    new_evidence: list[str] = []

    response_evidence = extract_evidence_from_response(narrator_response)
    for eid in response_evidence:
        if eid not in discovered_ids and eid not in new_evidence:
            state.add_evidence(eid)
            new_evidence.append(eid)

    return new_evidence
