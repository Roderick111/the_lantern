"""Spell prompt builders for LLM narration.

Builds prompts for Claude to generate immersive spell effect descriptions.
Follows narrator.py structure with spell-specific constraints.
"""

from typing import Any

from src.context.spell_detection import normalize_spell_target
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
                    f"- ID: {e.get('id', 'unknown')}\n"
                    f"  Name: {e.get('name', 'Unknown')}\n"
                    f"  Description: {e.get('description', '')}\n"
                    f"  Required tag: [EVIDENCE_{e.get('id', 'unknown')}]"
                    for e in undiscovered[:3]
                ]
            )
            evidence_context = f"""
== CANDIDATE EVIDENCE ==
{evidence_list}
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

== REQUIRED CONTENT ==
- Describe entering {witness_name}'s mind.
- {"Navigate toward: " + search_intent + "." if search_intent else "Show an unfocused search."}
- {"Naturally reveal every listed secret." if secrets_context else "Do not invent memories or secrets."}
- {withdrawal_note}. Describe leaving their consciousness.
- Tone signal: {style}."""

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

== REQUIRED CONTENT ==
- Describe attempting to enter {witness_name}'s mind.
- {barrier_note}.
- {withdrawal_note}. Describe leaving empty-handed. Reveal no secrets.
- Tone signal: {style}."""


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
    evidence_by_id = {
        str(e.get("id")): e
        for e in location_context.get("hidden_evidence", [])
        if e.get("id")
    }

    evidence_section = _format_revealable_evidence(
        undiscovered_evidence,
        target,
        valid_targets,
        evidence_by_id,
        spell_outcome,
    )

    outcome_section = _build_spell_outcome_section(spell_outcome)
    target_status = "VALID" if _target_matches(target, valid_targets) else "INVALID"
    world_context = str(location_context.get("world_context") or "None")
    surface_elements = str(location_context.get("surface_elements") or "None")
    conversation_history = str(location_context.get("conversation_history") or "None")
    context_signal = str(location_context.get("context_signal") or "None")
    narrator_hint = str(location_context.get("narrator_hint") or "None")

    return f"""== RITE ==
Rite: {spell["name"]}
Effect: {spell["description"]}
Category: {spell["category"]}
Target: {target or "general area"}
Target status: {target_status}
Outcome: {outcome_section}

== WORLD CONTEXT ==
{world_context}

== CURRENT LOCATION ==
{location_desc.strip()}

== VISIBLE ELEMENTS ==
{surface_elements}

== VALID TARGETS ==
{", ".join(valid_targets) if valid_targets else "No specific targets defined"}

== CANDIDATE EVIDENCE ==
{evidence_section}

== ALREADY DISCOVERED ==
{", ".join(discovered_evidence) if discovered_evidence else "None"}

== RECENT CONVERSATION ==
{conversation_history}

== PLAYER CONTEXT SIGNALS ==
{context_signal}

== NARRATOR HINT ==
{narrator_hint}

== PLAYER ACTION ==
Player performs {spell["name"]}{f" on {target}" if target else ""}."""


def _build_spell_outcome_section(spell_outcome: str | None) -> str:
    """Build spell outcome section for prompt.

    Args:
        spell_outcome: "SUCCESS" | "FAILURE" | None

    Returns:
        Formatted outcome section
    """
    if spell_outcome == "SUCCESS":
        return "SUCCESS"
    elif spell_outcome == "FAILURE":
        return "FAILURE"
    else:
        return "NOT_CALCULATED"


def _build_unknown_spell_prompt(spell_name: str) -> str:
    """Build prompt for unknown/invalid spell.

    Args:
        spell_name: The unknown spell name

    Returns:
        Prompt for handling unknown spell
    """
    return f"""== UNKNOWN RITE ==
Attempted rite: {spell_name}
Status: not recognized or unavailable for investigation use."""


def _target_matches(target: str | None, valid_targets: list[str]) -> bool:
    """Return whether target is valid using canonicalized spell vocabulary."""
    if not target:
        return True
    canonical_target = normalize_spell_target(target)
    if not canonical_target:
        return False
    target_lower = canonical_target.lower()
    return any(
        valid.lower() in target_lower or target_lower in valid.lower()
        for valid in valid_targets
    )


def _format_revealable_evidence(
    evidence_ids: list[str],
    target: str | None,
    valid_targets: list[str],
    evidence_by_id: dict[str, dict[str, Any]] | None = None,
    spell_outcome: str | None = None,
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

    if not _target_matches(target, valid_targets):
        return "None"

    lines: list[str] = []
    if spell_outcome == "FAILURE":
        return "None"
    for evidence_id in evidence_ids:
        evidence = (evidence_by_id or {}).get(evidence_id, {})
        description = str(evidence.get("description", "")).strip()
        guidance = str(evidence.get("discovery_guidance", "")).strip()
        if not guidance and evidence.get("triggers"):
            guidance = f"Player action references: {', '.join(str(t) for t in evidence['triggers'])}"
        lines.append(f"- ID: {evidence_id}")
        if description:
            lines.append(f"  Description: {description}")
        if guidance:
            lines.append(f"  Discovery guidance: {guidance}")
        lines.append(f"  Required tag: [EVIDENCE_{evidence_id}]")
    return "\n".join(lines) if lines else "None"
