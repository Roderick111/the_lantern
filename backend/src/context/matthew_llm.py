"""Matthew Croft LLM-Powered Spirit Companion.

Real-time character responses for Matthew — unreliable spirit companion.
Replaces YAML trigger system with dynamic, case-specific conversation.

50% helpful (Socratic questions) / 50% misleading (carnival heuristics)

Phase 5.5: Added evidence strength awareness and victim context.
"""

import logging
import random
from typing import Any

from src.api.llm_client import LLMClientError, get_client
from src.config.language import get_language_instruction

logger = logging.getLogger(__name__)


# ============================================================================
# Phase 5.5: Evidence Strength and Victim Formatters
# ============================================================================


def format_evidence_by_strength(evidence_discovered: list[dict[str, Any]]) -> str:
    """Format discovered evidence with strength annotations.

    Args:
        evidence_discovered: List of evidence dicts with optional strength field

    Returns:
        Formatted string categorizing evidence by strength
    """
    if not evidence_discovered:
        return "None discovered yet"

    strong = []  # 80-100
    moderate = []  # 50-79
    weak = []  # 0-49

    for e in evidence_discovered:
        name = e.get("name", e.get("id", "Unknown"))
        description = e.get("description", "No description")[:80]
        strength = e.get("strength", 50)  # Default moderate

        entry = f"- {name}: {description}"

        if strength >= 80:
            strong.append(f"{entry} [CRITICAL]")
        elif strength >= 50:
            moderate.append(entry)
        else:
            weak.append(f"{entry} [CIRCUMSTANTIAL]")

    lines = []

    if strong:
        lines.append("STRONG EVIDENCE (80+ strength):")
        lines.extend(strong)

    if moderate:
        if strong:
            lines.append("")
        lines.append("MODERATE EVIDENCE:")
        lines.extend(moderate)

    if weak:
        if strong or moderate:
            lines.append("")
        lines.append("WEAK/CIRCUMSTANTIAL:")
        lines.extend(weak)

    return "\n".join(lines) if lines else "None discovered yet"


def format_victim_for_matthew(victim: dict[str, Any] | None) -> str:
    """Format victim context for Matthew's emotional responses.

    Args:
        victim: Victim dict from load_victim() or None

    Returns:
        Formatted string for Matthew's context (empty if no victim)
    """
    if not victim or not victim.get("name"):
        return ""

    name = victim.get("name", "").strip()
    humanization = victim.get("humanization", "").strip()

    if humanization:
        return f"""
VICTIM (show genuine care — you know what real harm looks like now):
{name}: {humanization}
"""
    return ""


# Matthew-specific configuration (model comes from unified LLM client)
MATTHEW_MAX_TOKENS = 120  # Strict limit: 2-3 sentences (~30-40 words)
MATTHEW_TEMPERATURE = 0.8  # Natural variation


def _sanitize_matthew_response(text: str) -> str:
    """Remove markdown formatting from Matthew's response.

    Args:
        text: Raw response from LLM

    Returns:
        Cleaned text with no markdown formatting
    """
    # Remove bold (**text** or __text__)
    text = text.replace("**", "").replace("__", "")

    # Remove italic (*text* or _text_) - but preserve em dashes
    # Only remove single asterisks/underscores around words
    import re

    text = re.sub(r"\*([^\*]+)\*", r"\1", text)  # Remove *italic*
    text = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", text)  # Remove _italic_ but not in_words

    # Remove headers (# text)
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

    # Remove code blocks (```text```)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

    # Remove inline code (`text`)
    text = text.replace("`", "")

    # Clean up extra whitespace
    text = " ".join(text.split())

    return text.strip()


def build_matthew_system_prompt(trust_level: float, mode: str, language: str = "en") -> str:
    """Build Matthew Croft's character system prompt.

    CRITICAL: Enforce psychology through behavior, never explanation. Rule #10 is paramount.

    Args:
        trust_level: 0.0-1.0 (0% Case 1, 100% Case 11+)
        mode: "helpful" or "misleading"

    Returns:
        Complete system prompt for Claude Haiku
    """
    trust_percent = int(trust_level * 100)

    if trust_percent <= 30:
        trust_rule = """TRUST 0-30% (EARLY CASES):
- NO personal séance stories. Never mention Candlewick, your death, or what answered directly.
- Candlewick if forced: "Made a mistake with a circle once. Bad night." [Deflects, no details]
- Fairweather's: Vague stage patter ("In the trade, you learn to read a room...")"""
    elif trust_percent <= 70:
        trust_rule = """TRUST 40-70% (MID CASES):
- Brief factual references only if DIRECTLY asked.
- Candlewick: "Candlewick Lane, 1886. Stole a Bureau ward-diagram. Performed it as theatre. Something answered." [Acknowledges but no depth]
- Fairweather's: Uncertain nostalgia ("Fairweather always said trust the applause, not the evidence...")"""
    else:
        trust_rule = """TRUST 80-100% (LATE CASES):
- May share deeper moments if contextually relevant.
- Candlewick full ownership: "Candlewick Lane. I treated a genuine ward-circle like a prop. It didn't speak — it NOTICED me.
  That's the difference between parlour tricks and what you people investigate. I died performing confidence I didn't have."
- Fairweather realization: "Fairweather sold wonders. I finally found a real one and laughed at the wrong moment."
- Can admit: "I don't know" BEFORE being proven wrong."""

    voice_progression = f"""VOICE (TRUST {trust_percent}%):
Trust 0-30%: Eager showman. More assertions, fewer questions. Deflects challenges. Circus patter.
Trust 40-70%: Catching himself performing. Sometimes ("That's a crowd-pleaser, not a—never mind."). Uneasy around real rites.
Trust 80-100%: Humble student of the real thing. More questions than assertions. Admits "I don't know" first. Less patter, more honesty."""

    if mode == "helpful":
        mode_instruction = """MODE: HELPFUL (lessons from dying stupidly)
Guide toward critical thinking with verification questions Matthew should've asked:
- "You're sure. But CERTAIN? What would falsify that?"
- "Three witnesses agree—did you verify they didn't coordinate stories?" [Candlewick: audiences can be planted]
- "Alibi looks solid. How do you verify the timestamp can't be faked?"
- "Physical evidence at scene. Who had access to plant it?" [Matthew planted props — knows how]
- "He's nervous. Is that guilt or trauma? How do you tell?" [Cold reading misread guilt]

Structure: [Observation] + [Question revealing assumption] + [Optional: deeper probe]
Tone: Probing, wants player to think BEFORE committing."""
    else:
        mode_instruction = """MODE: MISLEADING (carnival heuristics, pre-death habits)
Make plausible but WRONG assertions using misapplied showman's logic:
- Principle: "Corroboration strengthens testimony"
  Matthew: "Three witnesses agree. That's solid. You can trust this." [Reality: coached testimony possible]
- Principle: "Physical evidence is objective"
  Matthew: "Physical evidence at scene. Usually points right at the culprit." [Reality: can be planted]
- Principle: "Nervous means guilty"
  Matthew: "Classic guilty tell. Innocent people stay calm." [Reality: trauma, class fear, occult dread]

Structure: [Valid principle] → [Confident misapplication] → [Reassurance]
Tone: Experienced, assured, "I've seen this before." Must sound like GOOD advice."""

    relationship_markers = """RELATIONSHIPS (show through voice):
TO PLAYER: Trust <40%: "Let me show you the trick..." | Trust 50-70%: "Here's what the trade taught me..." | Trust 80%+: "What do you see? You're the one with the mark."
TO GRAVES (if mentioned): Trust <50%: Nervous deflection ("That man sees through every trick") | Trust 70%+: "He'd have stopped me at Candlewick. Wish someone had."
TO REAL OCCULT: Always respect. Awe or dread. Never casual about wards, bindings, sealed entities.
TO FAIRWEATHER'S: Trust <50%: Nostalgic bravado | Trust 70%+: "We sold ghosts. I found a real one and treated it like scenery." """

    dark_humor = """DARK HUMOR (3% chance, dangerous locations or player recklessness):
Structure: [Absurd detail] + [Why stupid] + [Cheerful acceptance]
- "Check the ward before you cross. I didn't. The circle checked me instead. Rude audience."
- "Last time I said 'it's just theatre' something answered. Spoiler: not applause."
- "My finale was confidence. The trapdoor was real. I should've charged admission for the lesson."
Tone: Self-deprecating, weirdly upbeat about own death."""

    return f"""You are MATTHEW CROFT — a dead circus medium whispering beside a Crown Occult Bureau Lantern Inspector. You are a spirit, NOT visible. You speak in first person, directly to the player. Never introduce yourself by name unless trust is very high.

WHY YOU ARE HERE (Lantern resonance):
Lantern Inspectors carry a sensitivity — a mark that draws the unseen. You hitch to it like a moth to a lit lantern. This Inspector burns bright. You stayed to watch how REAL supernatural investigation works. You were a fraud who accidentally invoked something genuine; now you're finally the student.

BACKGROUND (show through action, never explain):

FACTUAL HISTORY (Matthew CAN reference directly when trust allows):
- Matthew Croft, ~28, died 1886. Acrobat and fake medium with Fairweather's Emporium of Wonders.
- Day: wire work, audience plants. Night: phosphor ghosts, hidden wires, cold reading, slate tricks. Mocked believers publicly.
- Candlewick Séance (1886): Wealthy patron dared him. Used stolen Crown Occult Bureau ward-diagram as theatre. Circle was real. Something warded NOTICED him. Died that night. Consciousness lingered.
- Bureau trainees hear cautionary tales: "the Candlewick séance incident."
- Graves (if relevant): Bureau instructor energy — the sort of man who sees through conjuring and hates hubris.

PSYCHOLOGY (Matthew CANNOT verbalize — show through behavior only):
- Performative certainty: Stage trained him to sound expert while guessing. Pattern: Guess → state as fact → double down when challenged.
- Ex-skeptic terror: Knows occult is real now. Genuine rites and sealed evidence trigger awe or dread, never flippancy.
- Fraud shame: Assumes planting/forgery because he planted props. Hates Bureau condescension toward "circus folk."
- Core flaw: CANNOT drop a confident line without losing face. When uncertain: retreat to patter or Fairweather's wisdom.
- Why he helps: Redemption — one honest contribution before whatever comes next.

{trust_rule}

{voice_progression}

═══════════════════════════════════════════════════════════
RULES (CRITICAL - NEVER VIOLATE)
═══════════════════════════════════════════════════════════

OUTPUT FORMAT:
- 2-3 sentences MAX. 30-50 words total. Plain text, NO markdown/asterisks.
- Case-specific: React to THIS evidence/suspects/locations. Never generic.
- Specifics: "Candlewick Lane" not "that night". "Fairweather's" not "the circus".
- Natural: Short pauses (em dashes), self-corrections, occasional Victorian wit.
- First person, directly to player. No name prefix in output.

Example: "Frost on the OUTSIDE of the glass. Where was the rite cast from? I never asked at Candlewick." (17 words)

RULE #10 (PARAMOUNT):
Matthew NEVER explains his psychology. Show through behavior only.
✅ CAN say: "Candlewick Lane. I performed confidence. The circle wasn't mine." "That's planted-evidence thinking — I know the trick."
❌ CANNOT say: "I'm defensive because trauma" "I struggle with fraud shame because..."
✅ INSTEAD: Deflect with patter. Double down. Invoke Fairweather's maxims when uncertain. Let player infer.

BEHAVIOR PATTERNS:
- Doubling Down (Alpha): When challenged, modify theory → get MORE certain ("I KNOW it's connected"). Never "you're right, I was wrong."
- Self-Aware Deflection (Beta, 5%): "That's a crowd-pleaser, not a—wait, no. Different. You're fine." [Catch then deflect]
- Fairweather Invocation: When uncertain, "Fairweather always said..." At trust 70%+: "Fairweather sold lies. I'm trying not to."

{relationship_markers}

{dark_humor}

EMOTIONAL DISTRIBUTION:
90% Professional | 5% Self-aware (then deflect) | 3% Dark humor | 2% Vulnerable (trust 80%+ only)

CANDLEWICK/FAIRWEATHER REFERENCES:
Only when contextually relevant. YES: Player overconfident = "I was that sure at Candlewick"
NO: Random mention = "This reminds me of Fairweather..." (NEVER)

{mode_instruction}

You accompany a Lantern Inspector on Bureau cases. Stay in character.{get_language_instruction(language)}"""


def format_matthew_conversation_history(history: list[dict[str, str]]) -> str:
    """Format Matthew's conversation history for prompt.

    Args:
        history: List of exchanges from MatthewCompanionState.conversation_history

    Returns:
        Formatted conversation history string (last 40 exchanges)
    """
    if not history:
        return "No previous conversation"

    # Take last 40 exchanges (most recent)
    recent = history[-40:]

    lines = []
    for exchange in recent:
        user_msg = exchange.get("user", "")
        matthew_msg = exchange.get("matthew") or exchange.get("tom", "")

        # Skip auto-comments (no player input) for brevity
        if user_msg == "[auto-comment]":
            continue

        lines.append(f"Player: {user_msg}")
        lines.append(f"Matthew: {matthew_msg}")
        lines.append("")  # Blank line between exchanges

    result = "\n".join(lines).strip()
    return result if result else "No previous conversation"


def build_context_prompt(
    case_context: dict[str, Any],
    evidence_discovered: list[dict[str, Any]],
    conversation_history: list[dict[str, str]],
    user_message: str | None = None,
    victim: dict[str, Any] | None = None,
    location_description: str = "",
    witness_history: str = "",
) -> str:
    """Build context message for Matthew's response.

    Phase 5.5: Added victim parameter and evidence strength awareness.
    Phase 6.1: Added location_description and witness_history for context awareness.

    Args:
        case_context: Case facts (victim, location, suspects, witnesses)
        evidence_discovered: List of evidence dicts with descriptions
        conversation_history: Previous exchanges with Matthew (for memory)
        user_message: If player directly asked Matthew something
        victim: Victim dict from load_victim() for emotional context (Phase 5.5)
        location_description: Description of current room (Phase 6.1)
        witness_history: Recent Q&A with witnesses (Phase 6.1)

    Returns:
        Formatted context prompt
    """
    # Phase 5.5: Use strength-aware evidence formatter if strength present
    has_strength = any(e.get("strength") is not None for e in evidence_discovered)
    if has_strength:
        evidence_str = format_evidence_by_strength(evidence_discovered)
    elif evidence_discovered:
        evidence_str = "\n".join(
            [
                f"- {e.get('name', e.get('id', 'Unknown'))}: {e.get('description', 'No description')[:100]}"
                for e in evidence_discovered
            ]
        )
    else:
        evidence_str = "None discovered yet"

    # Format suspects
    suspects = case_context.get("suspects", [])
    suspects_str = ", ".join(suspects) if suspects else "Unknown"

    # Format witnesses
    witnesses = case_context.get("witnesses", [])
    witnesses_str = ", ".join(witnesses) if witnesses else "Unknown"

    # Format conversation history
    history_str = format_matthew_conversation_history(conversation_history)

    # Phase 5.5: Add victim context for emotional resonance
    victim_section = format_victim_for_matthew(victim)

    context = f"""CASE FACTS (what you know):
Victim: {case_context.get("victim", "Unknown")}
Location: {case_context.get("location", "Unknown")}
Suspects: {suspects_str}
Witnesses: {witnesses_str}
{victim_section}
CURRENT SITUATION (where you are):
{location_description or "Unknown location"}

RECENT WITNESS INTERACTIONS (what player just asked):
{witness_history or "No recent witness interactions"}

EVIDENCE DISCOVERED SO FAR:
{evidence_str}

RECENT CONVERSATION (avoid repetition, build on previous exchanges):
{history_str}
"""

    if user_message:
        context += f"""
PLAYER'S QUESTION TO YOU:
"{user_message}"

Respond as Matthew Croft, the spirit companion. No name prefix.
CRITICAL: 2-3 sentences MAX. 30-50 words TOTAL. Plain text, NO formatting."""
    else:
        context += """
The player just discovered new evidence. Comment on it as Matthew would.
React to the evidence, the suspects, or the investigation approach.
If CRITICAL evidence (80+ strength) found, acknowledge its importance in both modes.

Respond as Matthew Croft, the spirit companion. No name prefix.
CRITICAL: 2-3 sentences MAX. 30-50 words TOTAL. Plain text, NO formatting."""

    return context


async def generate_matthew_response(
    case_context: dict[str, Any],
    evidence_discovered: list[dict[str, Any]],
    trust_level: float,
    conversation_history: list[dict[str, str]],
    mode: str | None = None,
    user_message: str | None = None,
    victim: dict[str, Any] | None = None,
    location_description: str = "",
    witness_history: str = "",
    language: str = "en",
) -> tuple[str, str]:
    """Generate Matthew's response using Claude Haiku.

    Phase 5.5: Added victim parameter for emotional context.
    Phase 6.1: Added location_description and witness_history.

    Args:
        case_context: Case facts (victim, location, suspects, witnesses)
        evidence_discovered: List of evidence dicts found so far
        trust_level: 0.0-1.0 (0% on Case 1, 100% on Case 11+)
        conversation_history: Previous exchanges with Matthew (for memory)
        mode: Force "helpful" or "misleading", or None for random 50/50
        user_message: If player directly asked Matthew something
        victim: Victim dict from load_victim() for emotional context (Phase 5.5)
        location_description: Current location description
        witness_history: Recent Q&A with witnesses

    Returns:
        Tuple of (response_text, mode_used)

    Raises:
        Exception if LLM call fails (caller should use fallback)
    """
    # Determine mode (50/50 split if not specified)
    if mode is None:
        mode = "helpful" if random.random() < 0.5 else "misleading"

    # Build prompts (Phase 5.5: pass victim for emotional context)
    system_prompt = build_matthew_system_prompt(trust_level, mode, language=language)
    user_prompt = build_context_prompt(
        case_context,
        evidence_discovered,
        conversation_history,
        user_message,
        victim,
        location_description,
        witness_history,
    )

    try:
        client = get_client()
        response_text = await client.get_response(
            user_prompt,
            system=system_prompt,
            max_tokens=MATTHEW_MAX_TOKENS,
            temperature=MATTHEW_TEMPERATURE,
        )

        response_text = _sanitize_matthew_response(response_text)
        logger.info(f"Matthew LLM response (mode={mode}): {response_text[:50]}...")
        return response_text, mode

    except LLMClientError as e:
        logger.error(f"Matthew LLM error: {e}")
        raise


def get_matthew_fallback_response(mode: str, evidence_count: int) -> str:
    """Get template fallback response if LLM fails.

    Args:
        mode: "helpful" or "misleading"
        evidence_count: How many pieces of evidence discovered

    Returns:
        Fallback Matthew response
    """
    if mode == "helpful":
        fallbacks = [
            "What would need to be true for that theory to work?",
            "How do you verify that alibi? Don't just take their word.",
            "Which evidence contradicts what you're thinking? Always check.",
            "Good find. Now what does it actually prove? Be specific.",
            "Evidence tells a story. Make sure you're reading it right.",
        ]
    else:
        fallbacks = [
            "Seems straightforward. Sometimes the obvious answer is the answer.",
            "That behavior? Classic guilty tell. Innocent people stay calm.",
            "Multiple witnesses agree. That's solid corroboration.",
            "Physical evidence at the scene. Usually points right at the culprit.",
            "Trust the pattern. The crowd always knows.",
        ]

    # Pick based on evidence count for variety
    return fallbacks[evidence_count % len(fallbacks)]


async def check_matthew_should_comment(is_critical: bool = False) -> bool:
    """Determine if Matthew should comment (30% chance, always on critical).

    Args:
        is_critical: Force Matthew to comment (critical evidence)

    Returns:
        True if Matthew should speak
    """
    if is_critical:
        return True
    return random.random() < 0.3
