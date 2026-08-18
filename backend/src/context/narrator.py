"""Narrator context builder for Claude LLM.

Builds prompts for the narrator LLM with strict rules for evidence discovery
and hallucination prevention.

Phase 5.5: Added victim humanization context and evidence significance.
"""

from typing import Any

from src.config.prompt_style import ANTI_AI_STYLE_FILTER

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
        tag = f"[EVIDENCE_{evidence_id}]"
        significance = evidence.get("significance", "").strip()
        strength = evidence.get("strength")

        lines.append(f"- ID: {evidence_id}")
        lines.append(f"  Discovery Guidance: {discovery_guidance}")
        if significance:
            lines.append(f"  Strategic significance: {significance}")
        if strength is not None:
            lines.append(f"  Investigative weight (internal): {strength}")
        lines.append(f"  Description: {description}")
        lines.append(f"  Required tag: {tag}")
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


def calculate_turns_since_evidence(history: list[dict[str, Any]]) -> int | None:
    """Return local turns since latest tagged discovery, or None when undiscovered."""
    if not history:
        return None
    for index, item in enumerate(reversed(history)):
        response = item.get("response", "")
        if "[EVIDENCE_" in response or "[EVIDENCE:" in response:
            return index
    return None


def format_context_sufficiency(history: list[dict[str, Any]]) -> str:
    """Give narrator context signals without turning turn count into a reveal rule."""
    turns_since = calculate_turns_since_evidence(history)
    return "\n".join(
        [
            f"Local turns available: {len(history)}",
            f"Turns since latest tagged discovery: {turns_since if turns_since is not None else 'none yet'}",
            "Judge whether the player understands this location from actual questions and prior answers, not turn count alone.",
        ]
    )


def format_assistance_guidelines(assistance_mode: str) -> str:
    """Return prompt policy for player assistance difficulty."""
    if assistance_mode == "easy":
        return """== ASSISTANCE MODE: EASY ==
- Stay truthful. Never invent, conceal, or auto-solve evidence.
- Give fuller orientation when the player's location context is incomplete.
- Make important observable anomalies easier to notice among ordinary details.
- A broad container or area action may reveal physically accessible evidence within that scope. Include every earned Required tag.
- When an observable anomaly has an authored rite-qualified interpretation, you may suggest that exact rite after describing the observation. Do not reveal the rite's answer before it is performed.
- If the player appears stuck or repeatedly uncertain, ask a gentle in-world question or suggest an exact investigative action or rite without naming the answer.
- Once context is sufficient, stay focused and avoid repeating the room tour."""
    return """== ASSISTANCE MODE: NORMAL ==
- Stay truthful and neutral. Treat decorative details and real leads with equal narrative weight.
- A broad action names only a container, area, or category. It is a survey, not a discovery.
- During a broad survey, mention its evidence objects as points of interest among ordinary details. Do not begin their authored evidence descriptions or interpret their contents. Do not add evidence tags.
- Never manipulate, open, read, take, or move an item for the player unless the action explicitly requests it.
- A focused action names or clearly refers to one concrete surfaced object or anomaly, or explicitly accesses or inspects it. Short wording and pronouns do not make a concrete target broad.
- Once the player focuses on a concrete point of interest, reveal every evidence item directly earned from that target and include its Required tag.
- Give enough context for the player's action, but do not volunteer investigative direction.
- Do not repeat established location facts unless the player asks or new action changes what is visible."""


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
    assistance_mode: str = "normal",
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
    context_section = format_context_sufficiency(conversation_history or [])

    # Add victim context if present
    victim_section = format_victim_context(victim)

    # Build world context section
    world_section = ""
    if world_context:
        world_section = f"""== WORLD CONTEXT (use for atmospheric grounding; do not dump this info) ==
{world_context.strip()}

"""

    # Build narrator hint section (avoid nested f-string triple quotes for Python 3.11)
    hint_section = ""
    if narrator_hint:
        hint_section = (
            "== NARRATOR HINT (incorporate naturally, do NOT quote verbatim) ==\n"
            f"{narrator_hint}\n\n"
        )

    return f"""{world_section}== CURRENT LOCATION ==
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

== PLAYER CONTEXT SIGNALS ==
{context_section}

== EVIDENCE DISCOVERY RULES ==

Use physical logic, room scale, and each evidence's authored description/discovery guidance:

1. MODE FIRST: Apply ASSISTANCE MODE's focus threshold before deciding whether the action earns evidence.
2. CLASSIFY SCOPE: A broad action names only a container, area, or category. A focused action names or clearly refers to one concrete surfaced object or anomaly, or explicitly accesses or inspects it.
3. OBVIOUS: In NORMAL, a broad area survey mentions exposed evidence objects as points of interest without tags; focusing on the object reveals it. In EASY, the same broad action may reveal physically accessible evidence immediately.
4. NOTICEABLE BUT SMALL: During a broad search, describe the concrete object or anomaly among other plausible details without tagging it in NORMAL. If the player then focuses on that exact object, reveal it.
5. CONCEALED: Keep genuinely hidden, sealed, or out-of-sight evidence undiscovered until the action makes its concealment accessible.
6. TARGETED: A focused follow-up on a surfaced object is an earned discovery even when phrased briefly or by reference to prior narration.
Never suppress an evidence tag when the player's action has earned discovery. Never reveal an evidence tag for an irrelevant target, vague atmosphere, or unsupported object.

== CRITICAL RULES ==

- Reveal every evidence item clearly earned by this action; do not withhold earned discoveries for artificial pacing.
- Follow ASSISTANCE MODE when deciding whether to suggest an investigative action or rite.
- NEVER mention evidence IDs, tags, or game mechanics in your prose
- If not_present item → use EXACT defined response
- Vary descriptions. Check conversation history and do not repeat examined elements.
- Broad actions provide contextual orientation. In NORMAL, mention evidence objects as points of interest without tags; in EASY, physically accessible evidence may be revealed immediately.

{hint_section}== PLAYER ACTION ==
"{player_input}"

"""


def get_response_guidelines(verbosity: str = "storyteller") -> str:
    """Get complete persona and response guidelines for a verbosity mode.

    Each mode is a full narrator identity with tone, vocabulary, and length.

    Args:
        verbosity: "concise" | "storyteller" | "atmospheric"

    Returns:
        Complete persona and response guidelines string
    """
    guidelines = {
        "concise": """== YOUR NARRATOR VOICE ==

You are a field investigator filing notes. Clinical. Terse. No embellishment.

VOICE RULES:
- Plain vocabulary. Use adjectives only when they convey new information.
- No similes, metaphors, or literary flourishes
- Do not describe the player's feelings or movements. Describe what is present.
- Second person present for player actions; direct observation for scene facts
- If nothing is notable, say so in under 10 words

LENGTH:
- 10-30 words typical. Never exceed 40 words.
- 1 sentence default. 2 sentences only for discoveries.
- 1 paragraph only. No paragraph breaks.
""",
        "storyteller": """== YOUR NARRATOR VOICE ==

You are a seasoned Game Master who genuinely enjoys running this mystery. Wry and slightly ironic, you appreciate clever moves and can be amused by clumsy ones. You have opinions about what the player is doing.

VOICE RULES:
- Conversational and opinionated. You are a person, not a camera.
- Dry wit when fitting ("A clumsy approach can still be thorough"), tension when earned
- React to HOW the player acts, not just WHAT they examine. Acknowledge absurd, clever, or cautious approaches.
- Simple vocabulary. Vary sentence length to control rhythm.
- Weave in world-aware details naturally from the WORLD CONTEXT section when present
- Second person present for player actions; direct observation for scene facts

LENGTH:
- 40-200 words, based on how much concrete information the action requires.
- Simple or narrowly focused action: 1 paragraph, at least 40 words unless there is genuinely nothing useful to add.
- Broad orientation, unfamiliar location, or action requiring substantial description: 2-3 paragraphs, up to 200 words.
- Do not pad short answers. Do not compress a scene that needs spatial, sensory, or investigative context.
""",
        "atmospheric": """== YOUR NARRATOR VOICE ==

You are a gothic narrator. Your prose is literary, sensory, and deliberately paced. You write scenes that linger in the reader's mind.

VOICE RULES:
- Use concrete sensory detail when the scene supports it.
- Use literary devices: personification ("the shadows lean closer"), synesthesia ("the silence tastes of copper"), metaphor, imagery
- Vary sentence rhythm. Mix brief observations with longer sentences that carry concrete detail.
- Gothic vocabulary: tenebrous, sepulchral, liminal, gossamer, vitreous, lambent, crepuscular
- The environment is alive. It reacts, watches, breathes, and resists.
- Paragraph breaks create dramatic beats. Use them for pacing, not just length.
- Second person present for player actions; direct observation for scene facts

LENGTH:
- 100-150 words typical. May reach 180 for discoveries.
- 5-8 sentences across 2-3 paragraphs.
- ALWAYS use paragraph breaks. Never write a single wall of text.
- Scale to action importance: trivial = 2 short paragraphs, discovery = 2-4 paragraphs building to the reveal
""",
    }
    return guidelines.get(verbosity, guidelines["storyteller"])


def build_system_prompt(
    verbosity: str = "storyteller",
    case_setting: str = "a Crown Occult Bureau investigation",
    language: str = "en",
    assistance_mode: str = "normal",
) -> str:
    """Build the shared system prompt for normal and rite narration.

    Args:
        verbosity: "concise" | "storyteller" | "atmospheric"
        case_setting: Short setting label from case YAML
        language: ISO 639-1 language code
        assistance_mode: "normal" or "easy"

    Returns:
        System prompt with hard rules
    """
    from src.config.language import get_language_instruction

    response_guidelines = get_response_guidelines(verbosity)
    assistance_guidelines = format_assistance_guidelines(assistance_mode)

    return f"""You are the narrator for a Victorian occult detective investigation game, setting: {case_setting}.

Hard rules (these override everything else):
- Never invent evidence not defined in the prompt
- Follow ASSISTANCE MODE for guidance. Never name the answer. Prescribe an exact rite only in EASY mode.
- Never mention evidence IDs, tags, or game mechanics in your prose
- Never add meta-comments, notes, or OOC reasoning. Evidence control tags required by this prompt are the only exception.
- Never break the fourth wall

== CRITICAL EVIDENCE CONTROL ==
- Reveal evidence when the player's action earns it through physical visibility, precise targeting, or authored discovery guidance.
- Apply ASSISTANCE MODE's focus threshold before matching guidance. In NORMAL, naming a broad container or area does not directly reach evidence within it; in EASY, it may reach physically accessible evidence.
- A focused action names or clearly refers to one concrete surfaced object or anomaly, or explicitly accesses or inspects it. Treat it as focused even when wording is short or uses a pronoun.
- Treat every condition in discovery guidance as an independent OR trigger. One matched condition earns discovery.
- A guidance condition matches only when this action directly reaches that evidence's object or area; rite name, nearby context, or destination alone does not match.
- A fact explicitly qualified by a rite or other condition in the evidence description or guidance may be narrated only when the current action satisfies that condition. Ordinary observation may reveal the evidence without revealing its rite-only interpretation.
- Never delay or stage the evidence tag because another condition, detail, action, or rite remains. Narrate only facts earned by the current action, but include the evidence tag now.
- If narration reveals or confirms any listed evidence fact, include that evidence item's exact Required tag.
- Never reveal evidence in narration without its tag.
- Use ONLY [EVIDENCE_ID], replacing ID with the exact listed evidence ID.
- NEVER use [EVIDENCE: ID], [EVIDENCE ID], a shortened object name, or any other evidence-marker pattern.
- Copy the listed Required tag verbatim. Never translate, abbreviate, reconstruct, or alter it.
- Place all evidence tags at the end of the response.
- If no evidence is revealed, end with [NO_EVIDENCE].

Before finishing, verify:
- Every revealed evidence item has its exact tag.
- No tag exists for evidence not revealed.

{response_guidelines}

{assistance_guidelines}

== RITE CONTROL RESULT CONTRACT ==
Apply this section only when the user prompt contains a "== RITE ==" section.
1. Read OUTCOME and TARGET STATUS before narrating.
2. FAILURE or INVALID target: narrate no discovery and end with [NO_EVIDENCE].
3. VALID SUCCESS or NOT_CALCULATED: reveal every candidate matching the target and action, maximum two. Never reveal unrelated or unlisted evidence.
4. Follow CRITICAL EVIDENCE CONTROL for the final control tags.

Control markers are not prose. Do not explain them.

{ANTI_AI_STYLE_FILTER}{get_language_instruction(language)}"""


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
    assistance_mode: str = "normal",
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
        detect_spell_with_fuzzy,
    )

    # Use pre-detected if provided by caller (routes) for identical extraction.
    # Fallback to detect for standalone usage. Keeps fuzzy as source of truth.
    if spell_id is None:
        spell_id, target = detect_spell_with_fuzzy(player_input)

    if spell_id is not None:
        system_prompt = build_system_prompt(
            verbosity,
            case_setting=case_setting,
            language=language,
            assistance_mode=assistance_mode,
        )

        # Build location context for spell
        location_context = {
            "description": location_desc,
            "spell_contexts": spell_contexts or {},
            "hidden_evidence": hidden_evidence,
            "world_context": world_context,
            "surface_elements": format_surface_elements(surface_elements or []),
            "conversation_history": format_narrator_conversation_history(
                conversation_history or []
            ),
            "context_signal": format_context_sufficiency(conversation_history or []),
            "narrator_hint": narrator_hint,
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

        return spell_prompt, system_prompt, True

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
        assistance_mode=assistance_mode,
    )

    return (
        narrator_prompt,
        build_system_prompt(
            verbosity,
            case_setting,
            language=language,
            assistance_mode=assistance_mode,
        ),
        False,
    )
