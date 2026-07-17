"""Investigation orchestration — setup, prompts, and post-LLM processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.api.helpers import (
    calculate_spell_outcome,
    check_spell_already_discovered,
    extract_new_evidence,
    find_witness_for_mnemonic_delving,
    load_localized_case_or_404,
    load_slot_state,
    process_spell_flags,
    resolve_location,
)
from src.api.schemas import InvestigateRequest
from src.case_store.loader import get_case_setting, list_locations
from src.context.narrator import (
    build_narrator_or_spell_prompt,
    build_narrator_prompt,
    build_system_prompt,
)
from src.context.spell_llm import SAFE_INVESTIGATION_SPELLS
from src.location.parser import LocationCommandParser
from src.state.player_state import PlayerState
from src.telemetry.logger import log_event
from src.utils.evidence import check_already_discovered, find_not_present_response


def detect_location_command(
    player_input: str,
    locations: list[dict[str, Any]],
    current_location: str,
) -> tuple[str | None, str | None, bool]:
    """Detect natural-language movement using precomputed location list."""
    location_ids = [loc["id"] for loc in locations]
    name_to_id = {loc["name"]: loc["id"] for loc in locations if loc.get("name")}
    parser = LocationCommandParser(location_ids, name_to_id=name_to_id)
    new_location = parser.parse(player_input)

    if new_location and new_location != current_location:
        name_map = {loc["id"]: loc["name"] for loc in locations}
        return new_location, name_map.get(new_location, new_location), False

    has_intent = parser.has_navigation_intent(player_input)
    return None, None, has_intent


def build_evidence_names(
    evidence_ids: list[str],
    hidden_evidence: list[dict[str, Any]],
) -> dict[str, str]:
    """Map evidence IDs to display names from case data."""
    if not evidence_ids:
        return {}
    name_map = {e.get("id", ""): e.get("name", "") for e in hidden_evidence}
    return {eid: name_map.get(eid, eid) for eid in evidence_ids}


@dataclass
class InvestigationContext:
    """Result of setup_investigation — all data needed for an investigation."""

    case_data: dict[str, Any]
    locations: list[dict[str, Any]]
    target_location_id: str
    location: dict[str, Any]
    state: PlayerState
    location_desc: str
    hidden_evidence: list[dict[str, Any]]
    not_present: list[dict[str, Any]]
    surface_elements: list[dict[str, Any]]
    discovered_ids: list[str]
    world_context: str | None
    case_setting: str


def setup_investigation(body: InvestigateRequest, player_id: str) -> InvestigationContext:
    """Common setup for all investigation endpoints."""
    # Load the save first so its locale selects the authored case view.
    state = load_slot_state(body.case_id, player_id, body.slot)
    language = getattr(state, "language", "en") if state else "en"
    case_data = load_localized_case_or_404(body.case_id, language)
    locations = list_locations(case_data)

    target_location_id, location = resolve_location(
        body,
        case_data,
        slot=body.slot,
        existing_state=state,
        locations=locations,
    )
    body.location_id = target_location_id

    if state is None:
        state = PlayerState(case_id=body.case_id, current_location=body.location_id)

    if state.current_location != body.location_id:
        state.current_location = body.location_id

    case_section = case_data.get("case", case_data)

    return InvestigationContext(
        case_data=case_data,
        locations=locations,
        target_location_id=target_location_id,
        location=location,
        state=state,
        location_desc=location.get("description", ""),
        hidden_evidence=location.get("hidden_evidence", []),
        not_present=location.get("not_present", []),
        surface_elements=location.get("surface_elements", []),
        discovered_ids=state.discovered_evidence,
        world_context=case_section.get("world_context"),
        case_setting=get_case_setting(case_data),
    )


def build_narrator_hints(
    body: InvestigateRequest,
    ctx: InvestigationContext,
    has_nav_intent: bool,
    is_spell: bool,
    spell_id: str | None,
) -> str | None:
    """Build narrator hint for soft short-circuit cases."""
    if has_nav_intent and not is_spell:
        return (
            "The player seems to be trying to leave this location or go somewhere. "
            "Do NOT narrate travel or describe arriving at a different place. "
            "Briefly acknowledge their intent in character — perhaps the path is "
            "unclear, or suggest they decide where to go. Stay in the current location. "
            "Keep it to 1-2 sentences."
        )

    if is_spell:
        already = check_spell_already_discovered(
            spell_id,
            body.player_input,
            ctx.hidden_evidence,
            ctx.discovered_ids,
        )
        if already:
            return (
                "The player is re-performing a rite on evidence they already discovered. "
                "Acknowledge briefly that they already found this. Do NOT reveal any new evidence."
            )
    elif check_already_discovered(body.player_input, ctx.hidden_evidence, ctx.discovered_ids):
        return (
            "The player is re-examining something they already discovered. "
            "Acknowledge briefly that they've already examined this. Do NOT reveal any new evidence."
        )

    not_present_response = find_not_present_response(body.player_input, ctx.not_present)
    if not_present_response:
        return (
            f"The item the player is looking for does not exist here. "
            f"Convey this naturally: {not_present_response}"
        )

    return None


def resolve_spell_mechanics(
    body: InvestigateRequest,
    ctx: InvestigationContext,
    spell_id: str | None,
    target: str | None,
) -> tuple[str | None, dict[str, Any] | None]:
    """Calculate spell outcome and witness context for mnemonic_delving."""
    if not spell_id:
        return None, None

    spell_outcome: str | None = None
    witness_context: dict[str, Any] | None = None

    if spell_id.lower() in SAFE_INVESTIGATION_SPELLS:
        spell_outcome = calculate_spell_outcome(spell_id, body.player_input, ctx.state)
    if spell_id.lower() == "mnemonic_delving":
        witness_context = find_witness_for_mnemonic_delving(target, ctx.case_data)

    return spell_outcome, witness_context


def build_investigation_prompt(
    body: InvestigateRequest,
    ctx: InvestigationContext,
    is_spell: bool,
    spell_id: str | None,
    target: str | None = None,
    spell_outcome: str | None = None,
    witness_context: dict[str, Any] | None = None,
    narrator_hint: str | None = None,
) -> tuple[str, str]:
    """Build prompt and system prompt for investigation."""
    if is_spell:
        prompt, system_prompt, _ = build_narrator_or_spell_prompt(
            location_desc=ctx.location_desc,
            hidden_evidence=ctx.hidden_evidence,
            discovered_ids=ctx.discovered_ids,
            not_present=ctx.not_present,
            player_input=body.player_input,
            surface_elements=ctx.surface_elements,
            conversation_history=ctx.state.get_narrator_history_as_dicts(
                location_id=ctx.target_location_id,
            ),
            spell_contexts=ctx.location.get("spell_contexts"),
            witness_context=witness_context,
            spell_outcome=spell_outcome,
            verbosity=ctx.state.narrator_verbosity,
            world_context=ctx.world_context,
            case_setting=ctx.case_setting,
            narrator_hint=narrator_hint,
            language=ctx.state.language,
            spell_id=spell_id,
            target=target,
        )
    else:
        prompt = build_narrator_prompt(
            location_desc=ctx.location_desc,
            hidden_evidence=ctx.hidden_evidence,
            discovered_ids=ctx.discovered_ids,
            not_present=ctx.not_present,
            player_input=body.player_input,
            surface_elements=ctx.surface_elements,
            conversation_history=ctx.state.get_narrator_history_as_dicts(
                location_id=ctx.target_location_id,
            ),
            verbosity=ctx.state.narrator_verbosity,
            world_context=ctx.world_context,
            case_setting=ctx.case_setting,
            narrator_hint=narrator_hint,
        )
        system_prompt = build_system_prompt(
            ctx.state.narrator_verbosity,
            case_setting=ctx.case_setting,
            language=ctx.state.language,
        )

    return prompt, system_prompt


async def process_investigation_response(
    response: str,
    body: InvestigateRequest,
    ctx: InvestigationContext,
    is_spell: bool,
    spell_id: str | None,
    target: str | None,
    player_id: str,
) -> tuple[list[str], dict[str, str]]:
    """Post-LLM: evidence extraction, spell flags, logging."""
    new_evidence = extract_new_evidence(response, ctx.discovered_ids, ctx.state)
    if is_spell:
        process_spell_flags(response, spell_id, target, ctx.case_data, ctx.state)

    evidence_names = build_evidence_names(new_evidence, ctx.hidden_evidence)

    await log_event(
        "investigate_action",
        player_id,
        body.case_id,
        {
            "location": ctx.target_location_id,
            "input": body.player_input[:100],
            "is_spell": is_spell,
            "spell_id": spell_id,
        },
    )
    if new_evidence:
        await log_event(
            "evidence_discovered",
            player_id,
            body.case_id,
            {"evidence_ids": new_evidence, "location": ctx.target_location_id},
        )

    return new_evidence, evidence_names
