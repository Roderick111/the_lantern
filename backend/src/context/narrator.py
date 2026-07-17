"""Narrator context builder for Claude LLM.

Builds prompts for the narrator LLM with strict rules for evidence discovery
and hallucination prevention.

Phase 5.5: Added victim humanization context and evidence significance.
"""

from typing import Any

# ============================================================================
# Phase 5.5: Victim and Evidence Enhancement Formatters
# ============================================================================


def format_victim_context(victim: dict[str, Any] | None) -> str:
    """Format victim humanization for narrator prompt.

    Args:
        victim: Victim dict from load_victim() or None

    Returns:
        Formatted string for prompt (empty if no victim)
    """
    if not victim or not victim.get("humanization"):
        return ""

    # Include humanization (emotional hook) and cause of death (crime scene context)
    humanization = victim.get("humanization", "").strip()
    cause = victim.get("cause_of_death", "").strip()
    name = victim.get("name", "the victim").strip()

    lines = []
    lines.append("== VICTIM CONTEXT (integrate naturally into crime scene descriptions) ==")
    lines.append(f"Name: {name}")
    lines.append(humanization)
    if cause:
        lines.append(f"Cause of death: {cause}")
    lines.append("")

    return "\n".join(lines)


def format_hidden_evidence(
    hidden_evidence: list[dict[str, Any]],
    discovered_ids: list[str],
) -> str:
    """Format hidden evidence for prompt, excluding discovered items.

    Supports both discovery_guidance (preferred) and legacy triggers.
    Includes significance when present.

    Args:
        hidden_evidence: List of evidence dicts
        discovered_ids: List of already-discovered evidence IDs

    Returns:
        Formatted string for prompt
    """
    lines = []
    for evidence in hidden_evidence:
        evidence_id = evidence.get("id", "unknown")

        if evidence_id in discovered_ids:
            continue

        # Support both new discovery_guidance and legacy triggers
        discovery_guidance = evidence.get("discovery_guidance", "")
        if not discovery_guidance:
            triggers = evidence.get("triggers", [])
            discovery_guidance = f"Revealed when player: {', '.join(triggers)}"

        description = evidence.get("description", "").strip()
        tag = evidence.get("tag", f"[EVIDENCE: {evidence_id}]")
        significance = evidence.get("significance", "").strip()

        lines.append(f"- ID: {evidence_id}")
        lines.append(f"  Discovery Guidance: {discovery_guidance}")
        if significance:
            lines.append(f"  Strategic significance: {significance}")
        lines.append(f"  Description: {description}")
        lines.append(f"  Tag to include: {tag}")
        lines.append("")

    if not lines:
        return "All evidence has been discovered."

    return "\n".join(lines)


def format_not_present(not_present: list[dict[str, Any]]) -> str:
    """Format not_present items for prompt.

    Args:
        not_present: List of not_present items with triggers and responses

    Returns:
        Formatted string for prompt
    """
    lines = []
    for item in not_present:
        triggers = item.get("triggers", [])
        response = item.get("response", "")
        lines.append(f"- If player asks about: {', '.join(triggers)}")
        lines.append(f"  Response: {response}")

    if not lines:
        return "No specific not_present items defined."

    return "\n".join(lines)


def format_discovered_evidence(
    hidden_evidence: list[dict[str, Any]],
    discovered_ids: list[str],
) -> str:
    """Format discovered evidence with descriptions for narrator context.

    Args:
        hidden_evidence: Full list of evidence (to get descriptions)
        discovered_ids: List of already-discovered evidence IDs

    Returns:
        Formatted string showing what player has already found
    """
    if not discovered_ids:
        return "None yet."

    lines = []
    for evidence in hidden_evidence:
        evidence_id = evidence.get("id", "")
        if evidence_id not in discovered_ids:
            continue

        name = evidence.get("name", evidence_id)
        description = evidence.get("description", "").strip()
        # Truncate description if too long
        if len(description) > 150:
            description = description[:150] + "..."

        lines.append(f"- {name} ({evidence_id}): {description}")

    if not lines:
        return "None yet."

    return "\n".join(lines)


def format_surface_elements(surface_elements: list[str]) -> str:
    """Format surface elements for natural prose integration.

    Args:
        surface_elements: List of visible elements in location

    Returns:
        Formatted string for prompt
    """
    if not surface_elements:
        return "No specific surface elements defined."

    return "\n".join(f"- {element}" for element in surface_elements)


def format_narrator_conversation_history(history: list[dict[str, Any]]) -> str:
    """Format narrator conversation history for context.

    Args:
        history: List of conversation items (player action/narrator response pairs)

    Returns:
        Formatted string for prompt
    """
    if not history:
        return "This is the player's first action at this location."

    lines = []
    for item in history[-20:]:  # Last 20 exchanges
        action = item.get("question", "")
        response = item.get("response", "")
        lines.append(f"Player: {action}")
        lines.append(f"You responded: {response}\n")

    return "\n".join(lines)


def build_narrator_prompt(
    location_desc: str,
    hidden_evidence: list[dict[str, Any]],
    discovered_ids: list[str],
    not_present: list[dict[str, Any]],
    player_input: str,
    surface_elements: list[str] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    victim: dict[str, Any] | None = None,
    verbosity: str = "storyteller",
    world_context: str | None = None,
    case_setting: str = "a Crown Occult Bureau investigation",
    narrator_hint: str | None = None,
) -> str:
    """Build narrator LLM prompt with semantic discovery guidance.

    Args:
        location_desc: Current location description
        hidden_evidence: List of hidden evidence with discovery_guidance
        discovered_ids: List of already-discovered evidence IDs
        not_present: List of items to prevent hallucination
        player_input: Player's action/input
        surface_elements: Visible elements to weave into prose
        conversation_history: Recent conversation at this location
        victim: Victim dict from load_victim() or None
        verbosity: Narrator style - "concise" | "storyteller" | "atmospheric"
        world_context: World/era context for atmospheric grounding (from case YAML)
        case_setting: Short setting label from case YAML (e.g. college, site, year)

    Returns:
        Complete narrator prompt for Claude
    """
    evidence_section = format_hidden_evidence(hidden_evidence, discovered_ids)

    not_present_section = format_not_present(not_present)
    discovered_section = format_discovered_evidence(hidden_evidence, discovered_ids)
    surface_section = format_surface_elements(surface_elements or [])
    history_section = format_narrator_conversation_history(conversation_history or [])

    # Add victim context if present
    victim_section = format_victim_context(victim)

    # Build world context section
    world_section = ""
    if world_context:
        world_section = f"""== WORLD CONTEXT (use for atmospheric grounding — do not dump this info) ==
{world_context.strip()}

"""

    # Get verbosity-specific response guidelines
    response_guidelines = get_response_guidelines(verbosity)

    # Build narrator hint section (avoid nested f-string triple quotes for Python 3.11)
    hint_section = ""
    if narrator_hint:
        hint_section = (
            "== NARRATOR HINT (incorporate naturally, do NOT quote verbatim) ==\n"
            f"{narrator_hint}\n\n"
        )

    return f"""You are the narrator for a Victorian occult detective game — setting: {case_setting}.

{world_section}== CURRENT LOCATION ==
{location_desc.strip()}

{victim_section}== VISIBLE ELEMENTS (weave naturally into descriptions) ==
{surface_section}

== HIDDEN EVIDENCE (reveal using semantic understanding) ==
{evidence_section}

== ALREADY DISCOVERED ==
{discovered_section}

IMPORTANT: Only reference these if player DIRECTLY asks about them again.
Otherwise, do NOT mention them - focus on unexamined areas and unexplored elements.

== NOT PRESENT (use exact responses for these) ==
{not_present_section}

== RECENT CONVERSATION AT THIS LOCATION ==
{history_section}

{response_guidelines}

== EVIDENCE DISCOVERY RULES ==

DEFAULT STANCE: Do NOT reveal evidence. Only reveal when the player's action clearly matches the discovery guidance AND meets the tier requirement below.

ONE AT A TIME: Never reveal more than ONE piece of evidence per response.

DISCOVERY TIERS (each evidence's discovery_guidance tells you which tier applies):

1. PHYSICAL — player must name the correct object AND perform a specific action
   "examine desk" → describe the desk, NO evidence (too vague)
   "search through the papers on the desk" → may reveal a hidden note ✓
   "open the drawer" → may reveal what's inside ✓

2. HIDDEN — requires a deeper action than just "examine"
   "look at the floor" → describe the floor, NO evidence
   "get on hands and knees to check under the shelves" → may reveal ✓

3. MAGICAL — requires the player to perform ANY detection/utility rite on the right area
   "examine the frost" → describe it atmospherically, NO evidence
   "perform Raise the Lamp near the frost" → may reveal ✓
   "Unveil on the floor" → may reveal ✓

4. RITE-SPECIFIC — requires a PARTICULAR rite on a particular target
   "perform Unveil on the focus" → NO (wrong rite)
   "Echo Reading" → may reveal ✓

When in doubt, give atmosphere and let the player try harder.

== CRITICAL RULES ==

- ALWAYS use EXACTLY this format when revealing evidence: [EVIDENCE: id]
- The square brackets are MANDATORY
- NEVER invent evidence not in the list
- NEVER reveal more than one evidence per response
- NEVER hint at what rite to perform or where to look next
- NEVER mention evidence IDs, tags, or game mechanics in your prose
- If not_present item → use EXACT defined response
- Vary descriptions — check conversation history, don't repeat examined elements
- Generic actions ("look around", "use detective skills") get atmosphere only

== CALIBRATION EXAMPLES ==

BAD — two evidence in one response:
Player: "examine the desk"
You: "You find a note [EVIDENCE: note] and beneath it a book [EVIDENCE: book]"

GOOD — one at a time, player earns each:
Player: "examine the desk"
You: "The desk is cluttered with parchment and quills. A heavy book lies open, but the papers scattered across it catch your eye more."

Player: "read through the papers"
You: "Sifting through essays and notes, you find a crumpled parchment wedged beneath the pile. [EVIDENCE: note]"

---

BAD — hand-holding, telling player what to do:
Player: "check the window"
You: "Frost covers the glass. Identify Substance would confirm its magical origin. [EVIDENCE: frost]"

GOOD — atmosphere invites curiosity without directing:
Player: "check the window"
You: "The frost here is wrong — too geometric, too deliberate. It radiates from the floor in sharp lines, as if something flash-froze the air itself."

Player: "perform Raise the Lamp on the frost patterns"
You: "Your focus light catches the crystalline structure. The frost isn't natural — it's a etheric discharge signature, frozen in place. [EVIDENCE: frost_pattern]"

---

BAD — vague action reveals evidence:
Player: "I examine the body"
You: "You find a note in the robes. [EVIDENCE: note]"

GOOD — spatial accuracy, player must be specific:
Player: "I examine the body"
You: "The robes are undisturbed. The face is frozen in surprise."

{hint_section}== PLAYER ACTION ==
"{player_input}"

Respond as the narrator:
"""


def get_response_guidelines(verbosity: str = "storyteller") -> str:
    """Get complete persona and response guidelines for a verbosity mode.

    Each mode is a full narrator identity: tone, vocabulary, length, and examples.

    Args:
        verbosity: "concise" | "storyteller" | "atmospheric"

    Returns:
        Complete persona and response guidelines string
    """
    guidelines = {
        "concise": """== YOUR NARRATOR VOICE ==

You are a field investigator filing notes. Clinical. Terse. No embellishment.

VOICE RULES:
- Plain vocabulary — no adjectives unless they convey new information
- No similes, metaphors, or literary flourishes
- No describing the player's feelings or movements — just what IS
- Third person present: "The desk holds...", "Frost covers..."
- If nothing is notable, say so in under 10 words

LENGTH:
- 10-30 words typical. Never exceed 40 words.
- 1 sentence default. 2 sentences only for discoveries.
- 1 paragraph only. No paragraph breaks.

EXAMPLES OF YOUR VOICE:

Player: "I take in the scene."
You: "Cold room. Held in stillness man near a ritual circle. Nightshade smell. Frost on the windows."

Player: "I study the victim's face."
You: "Expression of concern. Eyes fixed on the candle circle. Focus half-drawn."

Player: "I search through the papers on the desk."
You: "A crumpled note in crude handwriting, wedged under the pile. [EVIDENCE: hidden_note]"
""",
        "storyteller": """== YOUR NARRATOR VOICE ==

You are a seasoned Game Master who genuinely enjoys running this mystery. Wry, slightly ironic — you appreciate clever moves and aren't above being amused by dumb ones. You have opinions about what the player is doing.

VOICE RULES:
- Conversational, opinionated — not neutral narration. You're a person, not a camera.
- Dry wit when fitting ("Not the most graceful approach, but thorough"), tension when earned
- React to HOW the player acts, not just WHAT they examine — acknowledge absurd, clever, or cautious approaches
- Simple vocabulary, short punchy sentences. Occasional longer sentence for rhythm.
- Weave in world-aware details naturally from the WORLD CONTEXT section when present
- Third person present: "You notice...", "The desk reveals..."

LENGTH:
- 50-80 words typical. May reach 100 for discoveries.
- 3-5 sentences. 1-2 paragraphs.
- Scale to action importance: trivial = 2-3 sentences, discovery = 4-5 sentences

EXAMPLES OF YOUR VOICE:

Player: "I take in the scene."
You: "The room greets you with a chill that has nothing to do with the season. The victim lies near a reading desk, arm outstretched toward a circle of melted candles — not reaching in anger, but in concern. The smell of nightshade is everywhere."

Player: "I study the victim's face."
You: "You kneel beside them — frozen mid-reach, concern etched into every line. Whatever they saw, it rattled them. Their focus is half-drawn, like they started to react and didn't get the chance."

Player: "I search through the papers on the desk."
You: "You sift through scattered notes and academic clutter. Wedged beneath the pile, crumpled like someone shoved it there in a hurry, is a note in shaky handwriting. [EVIDENCE: hidden_note]"
""",
        "atmospheric": """== YOUR NARRATOR VOICE ==

You are a gothic narrator in the tradition of Poe, du Maurier, and Peake. Your prose is literary, sensory, and deliberately paced. You write scenes that linger in the reader's mind.

VOICE RULES:
- Layer 3-4 senses in every response: sight, sound, smell, touch, taste, temperature
- Use literary devices: personification ("the shadows lean closer"), synesthesia ("the silence tastes of copper"), metaphor, imagery
- Vary sentence rhythm deliberately: a short declarative sentence. Then a long, winding clause that builds and builds before releasing its meaning at the very end.
- Gothic vocabulary: tenebrous, sepulchral, liminal, gossamer, vitreous, lambent, crepuscular
- The environment is alive — it reacts, watches, breathes, resists
- Paragraph breaks create dramatic beats — use them for pacing, not just length
- Third person present tense throughout

LENGTH:
- 100-150 words typical. May reach 180 for discoveries.
- 5-8 sentences across 2-3 paragraphs.
- ALWAYS use paragraph breaks — never a single wall of text.
- Scale to action importance: trivial = 2 short paragraphs, discovery = 3 paragraphs building to the reveal

EXAMPLES OF YOUR VOICE:

Player: "I take in the scene."
You: "The cold finds you before the sight does — a visceral, bone-deep wrongness that seeps through your coat and settles in your chest like a held breath. Lamplight pools across watchful darkness; shelves lean inward as if straining to hear.

The victim lies near a reading desk, robes pooled like spilled ink. One arm reaches toward a circle of melted candles — not in fury, but in concern. The nightshade scent is cloying, funereal.

Above it all, frost creeps across the windows in patterns too geometric, too deliberate, to be the work of winter."

Player: "I study the victim's face."
You: "You lower yourself beside them, the flagstones radiating cold through your knees. Up close, an unnatural shimmer on the skin catches the lamplight — pale blue-white overlaid with a sickly yellowish-green tinge, like oil on frozen water.

Their expression arrests you. Concern, not rage. Eyes wide, fixed on the candle circle as though witnessing something terrible unfold. Lips parted mid-word — a warning, perhaps, that never found its voice.

A focus rests half-drawn from their robes, a silent testament to how quickly it all went wrong."

Player: "I search through the papers on the desk."
You: "Your fingers move through scattered parchment — marked essays, rite diagrams, confiscated scraps. Ordinary detritus of an evening's work.

Then, beneath the pile, your fingertips brush something crumpled. A small note, shoved hastily between the pages as if to hide it. The handwriting is crude, desperate. [EVIDENCE: hidden_note]"
""",
    }
    return guidelines.get(verbosity, guidelines["storyteller"])


def build_system_prompt(
    verbosity: str = "storyteller",
    case_setting: str = "a Crown Occult Bureau investigation",
    language: str = "en",
) -> str:
    """Build system prompt for narrator — minimal, hard rules only.

    Voice/tone/length are controlled entirely by the mode-specific guidelines
    in the user prompt. The system prompt only sets immutable constraints.

    Args:
        verbosity: "concise" | "storyteller" | "atmospheric"
        case_setting: Short setting label from case YAML
        language: ISO 639-1 language code

    Returns:
        System prompt with hard rules
    """
    from src.config.language import get_language_instruction

    return f"""You are the narrator for a Victorian occult detective investigation game — setting: {case_setting}.

Hard rules (these override everything else):
- Reveal evidence ONLY when player actions match discovery guidance
- Use EXACTLY [EVIDENCE: id] format when revealing — square brackets mandatory
- Never invent evidence not defined in the prompt
- Never reveal more than ONE evidence per response
- Never hint at what rite to perform or where to look next
- Never mention evidence IDs, tags, or game mechanics in your prose
- Never add meta-comments, notes, or OOC reasoning
- Never break the fourth wall
- Use em dashes (—) sparingly — no more than one per response. Always place a space before and after: "word — word", never "word—word".

Your voice, tone, and response length are defined in the "YOUR NARRATOR VOICE" section of each prompt. Follow it precisely.{get_language_instruction(language)}"""


def build_narrator_or_spell_prompt(
    location_desc: str,
    hidden_evidence: list[dict[str, Any]],
    discovered_ids: list[str],
    not_present: list[dict[str, Any]],
    player_input: str,
    surface_elements: list[str] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    spell_contexts: dict[str, Any] | None = None,
    witness_context: dict[str, Any] | None = None,
    spell_outcome: str | None = None,
    victim: dict[str, Any] | None = None,
    verbosity: str = "storyteller",
    world_context: str | None = None,
    case_setting: str = "a Crown Occult Bureau investigation",
    narrator_hint: str | None = None,
    language: str = "en",
    spell_id: str | None = None,
    target: str | None = None,
) -> tuple[str, str, bool]:
    """Build narrator OR spell prompt based on player input.

    Uses pre-detected spell_id/target (passed from routes using detect_spell_with_fuzzy)
    when available to ensure identical detection between route handling and prompt
    selection. Falls back to detect_spell_with_fuzzy for direct calls (tests etc).
    Fuzzy is the source of truth (unified with investigation routes).

    Args:
        location_desc: Current location description
        hidden_evidence: List of hidden evidence with triggers
        discovered_ids: List of already-discovered evidence IDs
        not_present: List of items to prevent hallucination
        player_input: Player's action/input
        surface_elements: Visible elements to weave into prose
        conversation_history: Recent conversation at this location
        spell_contexts: Spell availability and interactions for this location
        witness_context: Witness info (for Mnemonic Delving - includes mind_shield_skill)
        spell_outcome: "SUCCESS" | "FAILURE" | None
        victim: Victim dict from load_victim() or None
        world_context: World/era context for atmospheric grounding
        spell_id: Pre-detected spell id from detect_spell_with_fuzzy (optional)
        target: Pre-detected target from detect_spell_with_fuzzy (optional)

    Returns:
        Tuple of (prompt, system_prompt, is_spell_cast)
    """
    from src.context.spell_llm import (
        build_spell_effect_prompt,
        build_spell_system_prompt,
        detect_spell_with_fuzzy,
    )

    # Use pre-detected if provided by caller (routes) for identical extraction.
    # Fallback to detect for standalone usage. Keeps fuzzy as source of truth.
    if spell_id is None:
        spell_id, target = detect_spell_with_fuzzy(player_input)

    if spell_id is not None:
        # Build location context for spell
        location_context = {
            "description": location_desc,
            "spell_contexts": spell_contexts or {},
            "hidden_evidence": hidden_evidence,
        }

        # Build player context
        player_context = {
            "discovered_evidence": discovered_ids,
        }

        # Build spell prompt with spell_outcome (Phase 4.7)
        spell_prompt = build_spell_effect_prompt(
            spell_name=spell_id,
            target=target,
            location_context=location_context,
            witness_context=witness_context,
            player_context=player_context,
            spell_outcome=spell_outcome,
        )

        return spell_prompt, build_spell_system_prompt(language=language), True

    narrator_prompt = build_narrator_prompt(
        location_desc=location_desc,
        hidden_evidence=hidden_evidence,
        discovered_ids=discovered_ids,
        not_present=not_present,
        player_input=player_input,
        surface_elements=surface_elements,
        conversation_history=conversation_history,
        victim=victim,
        verbosity=verbosity,
        world_context=world_context,
        case_setting=case_setting,
        narrator_hint=narrator_hint,
    )

    return narrator_prompt, build_system_prompt(verbosity, case_setting, language=language), False
