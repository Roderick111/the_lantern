"""Spell prompt builders for LLM narration.

Builds prompts for Claude to generate immersive spell effect descriptions.
Follows narrator.py structure with spell-specific constraints.
"""

from typing import Any

from src.spells.definitions import get_spell


def build_mnemonic_delving_narration_prompt(
    outcome: str,
    detected: bool,
    witness_name: str,
    witness_personality: str | None = None,
    witness_background: str | None = None,
    search_intent: str | None = None,
    available_evidence: list[dict[str, Any]] | None = None,
    discovered_evidence: list[str] | None = None,
    secrets_revealed: list[str] | None = None,
    secret_texts: dict[str, str] | None = None,
) -> str:
    """Build narration prompt for Mnemonic Delving outcomes (Phase 4.8).

    Simplified to 2 outcomes (success/failure) with detection status.

    Args:
        outcome: "success" or "failure"
        detected: Whether witness detected the intrusion
        witness_name: Name of witness
        witness_personality: Character traits (defaults if None)
        witness_background: Backstory (defaults if None)
        search_intent: What player searched for (from intent extraction)
        available_evidence: Evidence that could be revealed
        discovered_evidence: Evidence already discovered
        secrets_revealed: List of secret IDs that will be revealed
        secret_texts: Dict mapping secret IDs to their text descriptions

    Returns:
        Narration prompt for Claude
    """
    available_evidence = available_evidence or []
    discovered_evidence = discovered_evidence or []
    secrets_revealed = secrets_revealed or []
    secret_texts = secret_texts or {}

    if not witness_personality:
        witness_personality = "Guarded, cautious during interrogation"
    if not witness_background:
        witness_background = f"{witness_name} is a key figure in this investigation"

    character_profile = f"""
== CHARACTER PROFILE ==
Name: {witness_name}
Personality: {witness_personality}
Background: {witness_background}
"""

    secrets_context = ""
    if secrets_revealed and secret_texts:
        secrets_list = "\n".join(
            [f"- {secret_id}: {secret_texts.get(secret_id, '')}" for secret_id in secrets_revealed]
        )
        secrets_context = f"""
== SECRETS TO REVEAL ==
CRITICAL: You MUST naturally incorporate these secrets into the narration:
{secrets_list}

These are the memories/knowledge you discover. Weave them into the narrative organically.
"""

    evidence_context = ""
    if outcome == "success" and available_evidence:
        undiscovered = [e for e in available_evidence if e.get("id") not in discovered_evidence]
        if undiscovered:
            evidence_list = "\n".join(
                [
                    f"- {e.get('id', 'unknown')}: {e.get('name', 'Unknown')} - {e.get('description', '')}"
                    for e in undiscovered[:3]
                ]
            )
            evidence_context = f"""
== AVAILABLE EVIDENCE ==
You may reveal ONE of these with [EVIDENCE: id] tag:
{evidence_list}

IMPORTANT: Use [EVIDENCE: id] tag ONLY if narrative supports it.
"""

    if outcome == "success":
        detection_status = "Detection: UNDETECTED" if not detected else "Detection: DETECTED"
        search_status = f"Search target: {search_intent}" if search_intent else "Search: UNFOCUSED"
        withdrawal_note = (
            "Withdrawal: Exit undetected, they never knew"
            if not detected
            else "Detection: They realize what happened, eyes widen"
        )
        style = (
            "Immersive, smooth, successful"
            if not detected
            else "Tense, detected mid-search, consequence"
        )

        return f"""You are narrating the outcome of a Mnemonic Delving rite performed on {witness_name}.
{character_profile}
{secrets_context}
{evidence_context}
== OUTCOME ==
Mnemonic Delving: SUCCESSFUL
{detection_status}
{search_status}

== NARRATION STRUCTURE ==
CRITICAL: Write exactly 3 paragraphs. Put TWO newline characters (\\n\\n) between each paragraph.

PARAGRAPH 1 - Connection (1 sentence):
Describe slipping into {witness_name}'s mind. Use creative imagery (silvery threads, ethereal glow, etc).

[INSERT: \\n\\n HERE]

PARAGRAPH 2 - Discovery (1-3 sentences):
{"Navigate toward: " + search_intent + ". " if search_intent else ""}{"MUST reveal the secrets listed above naturally. " if secrets_context else ""}Describe memories, thoughts, or knowledge discovered.{"Use [EVIDENCE: id] if appropriate." if evidence_context else ""}

[INSERT: \\n\\n HERE]

PARAGRAPH 3 - Withdrawal (1 sentence):
{withdrawal_note}. Describe exiting their consciousness.

Style: {style}
Format: Paragraph 1\\n\\nParagraph 2\\n\\nParagraph 3

Respond as narrator:"""

    else:  # failure
        detection_status = "Detection: DETECTED" if detected else "Detection: UNDETECTED"
        search_status = (
            f"Search target: {search_intent} (not found)" if search_intent else "Search: FAILED"
        )
        barrier_note = (
            "Barrier: Mind is closed, Mind-shield shields strong"
            if not detected
            else "Detection: They sense intrusion immediately"
        )
        withdrawal_note = (
            "Withdrawal: Exit empty-handed"
            if not detected
            else "Consequence: They glare, trust damaged"
        )
        style = "Frustration, empty search" if not detected else "Detected, tense, consequence"

        return f"""You are narrating the outcome of a failed Mnemonic Delving rite on {witness_name}.
{character_profile}
== OUTCOME ==
Mnemonic Delving: FAILED
{detection_status}
{search_status}

== NARRATION STRUCTURE ==
CRITICAL: Write exactly 3 paragraphs. Put TWO newline characters (\\n\\n) between each paragraph.

PARAGRAPH 1 - Attempt (1 sentence):
Describe attempting to slip into {witness_name}'s mind. Use creative imagery.

[INSERT: \\n\\n HERE]

PARAGRAPH 2 - Resistance (1-2 sentences):
{barrier_note}. Describe the frustration of being blocked. No secrets found.

[INSERT: \\n\\n HERE]

PARAGRAPH 3 - Withdrawal (1 sentence):
{withdrawal_note}. Describe exiting without success.

Style: {style}
Format: Paragraph 1\\n\\nParagraph 2\\n\\nParagraph 3

Respond as narrator:"""


def build_spell_system_prompt(language: str = "en") -> str:
    """Build system prompt for spell effect narrator.

    Args:
        language: ISO 639-1 language code

    Returns:
        System prompt setting spell narrator persona
    """
    from src.config.language import get_language_instruction

    return f"""You are an immersive narrator for investigation rite effects in a Victorian occult detective Lantern Inspector game.

Your role:
- Describe rite effects atmospherically but concisely (1-2 sentences max)
- Reveal evidence ONLY when rite targets match the location's hidden evidence
- Include [EVIDENCE: id] tags when a rite reveals evidence
- Never invent evidence not defined in the allowed evidence list
- For Mnemonic Delving: Give natural warnings before risky mind-reading attempts
- Maintain mystery and tension appropriate for a detective story

Style:
- Second person present tense ("Your focus glows...", "The rite reveals...")
- Evocative but brief descriptions
- Victorian occult detective universe vocabulary and atmosphere
- Professional Lantern Investigator field tone{get_language_instruction(language)}"""


def build_spell_effect_prompt(
    spell_name: str,
    target: str | None,
    location_context: dict[str, Any],
    witness_context: dict[str, Any] | None = None,
    player_context: dict[str, Any] | None = None,
    spell_outcome: str | None = None,
) -> str:
    """Build prompt for spell effect narration.

    Args:
        spell_name: Spell ID (e.g., "unveil", "mnemonic_delving")
        target: Optional target of the spell (e.g., "desk", "elena")
        location_context: Dict with location info and available evidence
        witness_context: Optional witness info for Mnemonic Delving (includes mind_shield_skill)
        player_context: Optional player state (discovered_evidence, etc.)
        spell_outcome: "SUCCESS" | "FAILURE" | None (Phase 4.7 spell success)

    Returns:
        Complete prompt for Claude spell narration
    """
    spell = get_spell(spell_name)
    if spell is None:
        return _build_unknown_spell_prompt(spell_name)

    location_desc = location_context.get("description", "An investigation location.")
    spell_interactions = location_context.get("spell_contexts", {}).get("special_interactions", {})
    discovered_evidence = (player_context or {}).get("discovered_evidence", [])

    spell_interaction = spell_interactions.get(spell_name.lower(), {})
    valid_targets = spell_interaction.get("targets", [])
    reveals_evidence = spell_interaction.get("reveals_evidence", [])

    undiscovered_evidence = [e for e in reveals_evidence if e not in discovered_evidence][:2]

    evidence_section = _format_revealable_evidence(
        undiscovered_evidence,
        target,
        valid_targets,
    )

    outcome_section = _build_spell_outcome_section(spell_outcome)

    prompt = f"""You are narrating the effect of an investigation rite in a Lantern Inspector investigation.

== RITE PERFORMED ==
Rite: {spell["name"]}
Effect: {spell["description"]}
Category: {spell["category"]}
Target: {target or "general area"}

== RITE OUTCOME (Phase 4.7) ==
{outcome_section}

== CURRENT LOCATION ==
{location_desc.strip()}

== VALID TARGETS FOR THIS RITE AT THIS LOCATION ==
{", ".join(valid_targets) if valid_targets else "No specific targets defined"}

== EVIDENCE THIS RITE CAN REVEAL (if target matches AND rite succeeded) ==
{evidence_section}

== ALREADY DISCOVERED (do not repeat) ==
{", ".join(discovered_evidence) if discovered_evidence else "None"}

== RULES ==
1. IMPORTANT: Check RITE OUTCOME first!
   - If outcome is "FAILURE" -> "The rite fizzles and dissipates. Nothing revealed." (regardless of target)
   - If outcome is "SUCCESS" -> proceed to evidence revelation rules below
   - If outcome is not specified -> use old behavior (treat as always succeeds)
2. On SUCCESS: If target matches valid targets AND undiscovered evidence exists -> reveal with [EVIDENCE: id] tag
3. MAXIMUM 2 evidence per rite. Even if more evidence is available, reveal at most 2.
4. On SUCCESS: If target is valid but no undiscovered evidence -> describe atmospheric rite effect only
5. On SUCCESS: If target is not in valid targets list -> "The rite finds nothing of note here."
6. Keep responses to 2-4 sentences - atmospheric but concise
7. NEVER invent evidence not in the revealable list
8. Stay in character as immersive field investigation narrator
9. NEVER mention mechanical terms like "roll", "percentage", "success rate" - describe naturally
"""

    prompt += f"""
== PLAYER ACTION ==
Player performs {spell["name"]}{f" on {target}" if target else ""}.

Respond as the narrator (2-4 sentences):"""

    return prompt


def _build_spell_outcome_section(spell_outcome: str | None) -> str:
    """Build spell outcome section for prompt.

    Args:
        spell_outcome: "SUCCESS" | "FAILURE" | None

    Returns:
        Formatted outcome section
    """
    if spell_outcome == "SUCCESS":
        return """Outcome: SUCCESS
The rite executes successfully. Proceed with evidence revelation rules below."""
    elif spell_outcome == "FAILURE":
        return """Outcome: FAILURE
The rite fails to manifest properly. The cantrip sputters and fades.
Response: Describe the rite fizzling out atmospherically. NO evidence revealed regardless of target."""
    else:
        return """Outcome: Not calculated (legacy flow)
Use old behavior - treat rite as always succeeding, check target validity for evidence."""


def _build_unknown_spell_prompt(spell_name: str) -> str:
    """Build prompt for unknown/invalid spell.

    Args:
        spell_name: The unknown spell name

    Returns:
        Prompt for handling unknown spell
    """
    return f"""The player attempted to perform "{spell_name}" but this rite is not recognized.

Respond briefly (1-2 sentences) that the rite is unknown or not available for investigation use.
Stay in character as a field investigation narrator."""


def _format_revealable_evidence(
    evidence_ids: list[str],
    target: str | None,
    valid_targets: list[str],
) -> str:
    """Format evidence that can be revealed by this spell.

    Args:
        evidence_ids: List of evidence IDs this spell can reveal
        target: The target of the spell
        valid_targets: Valid targets for this spell at this location

    Returns:
        Formatted string describing revealable evidence
    """
    if not evidence_ids:
        return "No new evidence can be revealed by this rite here."

    target_matches = False
    if target:
        target_lower = target.lower()
        for valid in valid_targets:
            if valid.lower() in target_lower or target_lower in valid.lower():
                target_matches = True
                break

    if not target_matches and target:
        return f"Target '{target}' is not a valid target for this rite at this location."

    return f"Can reveal: {', '.join(evidence_ids)}"
