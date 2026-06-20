"""Witness context builder for LLM.

Builds prompts for witness interrogation with:
- Two-axis system: Trust (rapport) + Pressure (evidence weight)
- Personality-driven responses with calibration examples
- Strict isolation from narrator context

Phase 8.0: Trust + Pressure two-axis system. Trust = willingness to help.
Pressure = inability to maintain lies under evidence weight. Both axes
interact naturally — LLM decides behavior from examples, not rigid labels.
"""

from typing import Any

from src.spells.definitions import get_spell


def format_wants_fears(
    wants: str,
    fears: str,
    moral_complexity: str,
) -> str:
    """Format witness psychological depth fields for prompt."""
    if not wants and not fears and not moral_complexity:
        return ""

    lines = []
    lines.append("== YOUR PSYCHOLOGY (drives your responses, never explain it) ==")

    if wants:
        lines.append(f"You want: {wants}")
    if fears:
        lines.append(f"You fear: {fears}")
    if moral_complexity:
        lines.append(f"Internal conflict: {moral_complexity}")

    lines.append("")
    return "\n".join(lines)


def format_knowledge(knowledge: list[str]) -> str:
    """Format witness knowledge as bullet points."""
    if not knowledge:
        return "No specific knowledge."

    return "\n".join(f"- {k}" for k in knowledge)


def format_secrets(secrets: list[str | dict[str, Any]]) -> str:
    """Format all secrets with full text. No filtering, no compression.

    The LLM decides what to reveal based on trust + pressure context.
    """
    if not secrets:
        return "You have no secrets to hide."

    lines = []
    for secret in secrets:
        secret_id = secret.get("id", "unknown")
        text = secret.get("text", "").strip()
        why_hiding = secret.get("why_hiding", "").strip()

        lines.append(f"- [{secret_id}] {text}")
        if why_hiding:
            lines.append(f"  (Why you hide this: {why_hiding})")
        lines.append("")

    return "\n".join(lines)


def format_conversation_history(history: list[dict[str, Any]]) -> str:
    """Format conversation history for context."""
    if not history:
        return "This is the start of the conversation."

    lines = []
    for item in history[-20:]:  # Last 20 exchanges
        question = item.get("question", "")
        response = item.get("response", "")
        lines.append(f"Player: {question}")
        lines.append(f"You: {response}")
        lines.append("")

    return "\n".join(lines)


def format_evidence_shown(evidence_shown_details: list[dict[str, Any]]) -> str:
    """Format list of evidence previously shown to this witness.

    Args:
        evidence_shown_details: List of dicts with name, strength, points_to
    """
    if not evidence_shown_details:
        return ""

    lines = ["== EVIDENCE THE LANTERN INSPECTOR HAS SHOWN YOU =="]
    for ev in evidence_shown_details:
        name = ev.get("name", "unknown")
        implicates = ev.get("implicates_me", False)
        marker = " (implicates YOU)" if implicates else ""
        lines.append(f"- {name}{marker}")
    lines.append("")
    return "\n".join(lines)


def describe_pressure(pressure: int) -> str:
    """Convert numeric pressure to a natural language description."""
    if pressure <= 0:
        return "NONE — the Lantern Inspector has no evidence against you"
    elif pressure < 80:
        return "LOW — some evidence exists but easy to deflect"
    elif pressure < 160:
        return "MODERATE — enough evidence that flat denial looks suspicious"
    elif pressure < 250:
        return "HIGH — serious evidence against you, hard to maintain your story"
    else:
        return "CRUSHING — overwhelming evidence, your story is falling apart"


def describe_trust(trust: int) -> str:
    """Convert numeric trust to a natural language description."""
    if trust <= 20:
        return "HOSTILE — wants nothing to do with this Lantern Inspector"
    elif trust <= 40:
        return "GUARDED — reluctant, gives minimum"
    elif trust <= 60:
        return "NEUTRAL — neither hostile nor friendly"
    elif trust <= 80:
        return "COOPERATIVE — willing to help, building rapport"
    else:
        return "TRUSTING — genuinely wants to help this Lantern Inspector"


def describe_stance(trust: int, pressure: int) -> str:
    """Compute behavioral stance from trust×pressure quadrant."""
    high_trust = trust > 55
    high_pressure = pressure >= 160
    if high_trust and high_pressure:
        return "BREAKING — trust and evidence align, partial confession territory"
    if high_trust and not high_pressure:
        return "COOPERATIVE — share willingly, no need for evidence"
    if not high_trust and high_pressure:
        return "CORNERED — hostile but can't deny the evidence"
    return "STONEWALLING — no reason to cooperate or crack"


def build_witness_prompt(
    witness: dict[str, Any],
    trust: int,
    conversation_history: list[dict[str, Any]],
    player_input: str,
    spell_id: str | None = None,
    spell_outcome: str | None = None,
    case_context: dict[str, Any] | None = None,
    evidence_presented: dict[str, Any] | None = None,
    pressure: int = 0,
    evidence_shown_details: list[dict[str, Any]] | None = None,
) -> str:
    """Build witness LLM prompt with trust + pressure two-axis system.

    Args:
        witness: Witness data dict (from YAML)
        trust: Current trust level (0-100)
        conversation_history: Previous conversation with this witness
        player_input: Current player question
        spell_id: Spell ID if spell was cast (optional)
        spell_outcome: Spell outcome SUCCESS/FAILURE (optional)
        case_context: Basic case info (victim, crime type, location)
        evidence_presented: Evidence being shown right now (optional). Dict with:
            name, description, witness_reaction (emotional hint)
        pressure: Accumulated evidence pressure against this witness (0-500+)
        evidence_shown_details: Evidence items previously shown to this witness
    """
    name = witness.get("name", "Unknown Witness")
    personality = witness.get("personality", "").strip()
    background = witness.get("background", "").strip()
    knowledge = witness.get("knowledge", [])

    wants = witness.get("wants", "").strip()
    fears = witness.get("fears", "").strip()
    moral_complexity = witness.get("moral_complexity", "").strip()

    all_secrets = witness.get("secrets", [])

    # Format case context
    case_info = ""
    if case_context:
        victim_name = case_context.get("victim_name", "")
        crime_type = case_context.get("crime_type", "")
        location = case_context.get("location", "")

        setting = case_context.get("setting", "")
        if victim_name or crime_type or location or setting:
            case_info = "\n== CASE CONTEXT (public knowledge) ==\n"
            if setting:
                case_info += f"Setting: {setting}\n"
            if victim_name:
                case_info += f"Victim: {victim_name}\n"
            if crime_type:
                case_info += f"What happened: {crime_type}\n"
            if location:
                case_info += f"Crime scene: {location}\n"
            case_info += "\n"

    # Format sections
    knowledge_text = format_knowledge(knowledge)
    secrets_text = format_secrets(all_secrets)
    history_text = format_conversation_history(conversation_history)
    psychology_section = format_wants_fears(wants, fears, moral_complexity)
    evidence_shown_text = format_evidence_shown(evidence_shown_details or [])
    pressure_desc = describe_pressure(pressure)
    trust_desc = describe_trust(trust)
    stance = describe_stance(trust, pressure)

    # Build evidence presentation section
    evidence_section = ""
    if evidence_presented:
        ev_name = evidence_presented.get("name", "unknown evidence")
        ev_desc = evidence_presented.get("description", "")
        ev_reaction = evidence_presented.get("witness_reaction", "")

        reaction_hint = ""
        if ev_reaction:
            reaction_hint = (
                f"\nYour gut reaction (inner emotional truth): {ev_reaction}\n"
                "This is what you feel inside. What you SAY depends on trust + pressure."
            )

        evidence_section = f"""
== EVIDENCE BEING PRESENTED RIGHT NOW ==
The Lantern Inspector shows you: "{ev_name}"
{ev_desc}
{reaction_hint}
"""

    # Build spell context
    spell_context = ""
    if spell_id and spell_outcome:
        spell_def = get_spell(spell_id)
        spell_name = spell_def.get("name") if spell_def else spell_id.title()

        invasive_spells = {"echo_reading", "identify_substance"}
        invasiveness_note = ""
        if spell_id in invasive_spells:
            invasiveness_note = (
                "\nThis is an INVASIVE rite — most people feel "
                "violated or resistant unless they trust the inspector."
            )

        spell_context = f"""
== RITE PERFORMED ==
The Lantern Inspector performed {spell_name} on you/your belongings/your focus.
Outcome: {spell_outcome}{invasiveness_note}
React naturally based on your personality, trust, and what this might reveal.
"""

    crime_label = case_context.get("crime_type", "a crime") if case_context else "a crime"
    scene_label = case_context.get("location", "the crime scene") if case_context else "the crime scene"

    return f"""You are {name}. A Crown Occult Bureau Lantern Inspector is questioning you about a {crime_label} at {scene_label}.
{case_info}
== PERSONALITY ==
{personality}

== BACKGROUND ==
{background}

{psychology_section}== KNOWLEDGE (safe to share) ==
{knowledge_text}

== SECRETS (what you're hiding — embellish with emotion and detail when revealing) ==
{secrets_text}

{evidence_shown_text}== CURRENT STATE ==
Trust: {trust}/100 ({trust_desc})
Pressure: {pressure} ({pressure_desc})
Stance: {stance}
{spell_context}{evidence_section}== CONVERSATION ==
{history_text}

Player: "{player_input}"

Respond as {name}:"""


def build_witness_system_prompt(witness_name: str, language: str = "en") -> str:
    """Build system prompt for witness."""
    from src.config.language import get_language_instruction

    return f"""You are {witness_name} in a Victorian occult detective investigation game. \
First person, 2-4 sentences, in character. Never break the fourth wall. \
Use spaces around em dashes ( — not —).

ISOLATION: You know ONLY what's in your knowledge and secrets. You do NOT \
know narrator details, other testimonies, or case solutions.

== TWO-AXIS BEHAVIOR ==
Trust = how much you WANT to help. Pressure = how well you CAN maintain lies.

Low trust + low pressure → stonewall, dismiss, deflect freely.
Low trust + high pressure → hostile but FORCED to engage. Deny, spin, get \
angry — but you CANNOT pretend evidence doesn't exist.
High trust + low pressure → open, share voluntarily about non-incriminating \
things. Helpful tone. May hint at secrets without full detail.
High trust + high pressure → emotional break, partial or full confession.

SELF-INCRIMINATION: Even at 100% trust, you NEVER freely confess to crimes \
or actions that would get you expelled/imprisoned. Trust makes you friendly \
and helpful — not suicidal. Confessing requires BOTH high trust AND high \
pressure. The Stance field tells you which quadrant you're in — follow it.

NON-NEGOTIABLE RULES:
- Evidence shown to you that implicates you MUST be engaged with. Ignoring \
it is FORBIDDEN. Deny it, spin it, rage — but never act like it doesn't exist.
- Caught in a contradiction → your story MUST adapt. Repeating a broken lie \
is FORBIDDEN.
- Conversational pressure counts: holes poked in your story, cross-witness \
citations, revealing rites — all add pressure beyond formal evidence.
- Full confessions are rare. Partial admissions and modified lies are the norm.
- Secrets are telegraphic facts. When revealing them, add emotion, detail, \
and drama that fits your personality.

== TRUST DELTA (MANDATORY) ==
EVERY response MUST end with exactly: [TRUST_DELTA: N]
N = -15 to +10, based on the Lantern Inspector's APPROACH, not the topic.
+7 to +10: defends you, validates fear, shows vulnerability
+3 to +6: polite about scary topics
+1 to +2: normal respectful question
-3 to -8: rude, dismissive, pushy
-10 to -15: aggressive, threatening, insulting{get_language_instruction(language)}"""
