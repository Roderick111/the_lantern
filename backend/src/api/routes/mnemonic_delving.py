"""Mnemonic Delving spell handler for witness interrogation."""

import logging
import random
from typing import Any

from src.api.dependencies import UserLLMConfig
from src.api.helpers import (
    detect_keyword_match,
    detect_secret_by_consecutive_words,
    save_slot_state,
)
from src.api.llm_client import LLMClientError as ClaudeClientError
from src.api.llm_client import get_client
from src.api.schemas import InterrogateRequest, InterrogateResponse
from src.context.spell_llm import (
    build_mnemonic_delving_narration_prompt,
    build_spell_system_prompt,
    calculate_mnemonic_delving_success,
    extract_intent_from_input,
)
from src.state.player_state import PlayerState
from src.utils.evidence import extract_evidence_from_response

logger = logging.getLogger(__name__)


async def handle_programmatic_mnemonic_delving(
    body: InterrogateRequest,
    witness: dict[str, Any],
    state: PlayerState,
    witness_state: Any,
    llm_config: UserLLMConfig | None = None,
    slot: str = "autosave",
    player_id: str = "default",
) -> InterrogateResponse:
    """Handle Mnemonic Delving with formula-based outcomes."""
    witness_name = witness.get("name", "the witness")
    witness_id = witness.get("id", "unknown")
    witness_personality = witness.get("personality")
    witness_background = witness.get("background")

    search_intent = extract_intent_from_input(body.question)
    attempts = witness_state.spell_attempts.get("mnemonic_delving", 0)

    success, success_rate, specificity_bonus, decline_penalty, success_roll = (
        calculate_mnemonic_delving_success(
            player_input=body.question,
            attempts_on_witness=attempts,
            witness_id=witness_id,
        )
    )

    # Detection chance (Mind-shield-based)
    base_detection = 20
    mind_shield_raw = witness.get("mind_shield_skill", 0)
    mind_shield_skill = 0 if isinstance(mind_shield_raw, str) else int(mind_shield_raw)
    skill_bonus = (mind_shield_skill / 100) * 30
    detection_chance = base_detection + skill_bonus

    repeat_penalty = 0
    if witness_state.mnemonic_delving_detected:
        repeat_penalty = 20
        detection_chance += repeat_penalty

    detection_chance = min(95, detection_chance)
    detection_roll = random.random() * 100
    detected = detection_roll < detection_chance

    outcome = "success" if success else "failure"

    # Trust penalty
    trust_delta = 0
    if detected:
        trust_delta = -random.choice([5, 10, 15, 20])
        witness_state.mnemonic_delving_detected = True
        witness_state.adjust_trust(trust_delta)
    elif not success:
        trust_delta = -random.choice([5, 10])
        witness_state.adjust_trust(trust_delta)

    witness_state.spell_attempts["mnemonic_delving"] = attempts + 1

    logger.info(
        f"Mnemonic Delving: {witness_name} | Input: '{body.question}' | "
        f"Attempt #{attempts + 1} | "
        f"Success: {success_rate}% (30+{specificity_bonus}-{decline_penalty}) | "
        f"roll={success_roll:.1f} | {'SUCCESS' if success else 'FAILURE'} | "
        f"Detection: {detection_chance:.0f}% | roll={detection_roll:.1f} | "
        f"{'DETECTED' if detected else 'UNDETECTED'} | Trust: {trust_delta:+d}"
    )

    # Check for secrets revealed
    secrets_revealed: list[str] = []
    secret_texts: dict[str, str] = {}
    discovered_ids = list(state.discovered_evidence)

    if success and search_intent:
        secrets = witness.get("secrets", [])
        for secret in secrets:
            secret_id = secret.get("id", "")
            secret_text = secret.get("text", "")
            secret_keywords = secret.get("keywords", [])

            if secret_id and secret_id not in witness_state.secrets_revealed:
                keyword_match = detect_keyword_match(search_intent, secret_keywords)
                consecutive_match = detect_secret_by_consecutive_words(
                    search_intent, secret_text, window_size=5
                )
                if keyword_match or consecutive_match:
                    witness_state.reveal_secret(secret_id)
                    secrets_revealed.append(secret_id)
                    secret_texts[secret_id] = secret_text.strip()

    # Build narration prompt
    narration_prompt = build_mnemonic_delving_narration_prompt(
        outcome=outcome,
        detected=detected,
        witness_name=witness_name,
        witness_personality=witness_personality,
        witness_background=witness_background,
        search_intent=search_intent,
        available_evidence=[],
        discovered_evidence=discovered_ids,
        secrets_revealed=secrets_revealed,
        secret_texts=secret_texts,
    )

    try:
        client = get_client()
        system_prompt = build_spell_system_prompt()
        _key = llm_config.api_key if llm_config else None
        _model = llm_config.model if llm_config else None
        narrator_text = await client.get_response(
            narration_prompt,
            system=system_prompt,
            max_tokens=200,
            api_key=_key,
            model=_model,
        )
    except ClaudeClientError:
        if detected:
            narrator_text = (
                f"{witness_name}'s eyes widen. They sensed your intrusion. Trust damaged."
            )
        else:
            narrator_text = (
                f"You attempt to slip into {witness_name}'s mind, "
                "but their thoughts remain closed to you."
            )

    response_evidence = extract_evidence_from_response(narrator_text)
    for eid in response_evidence:
        if eid not in discovered_ids:
            state.add_evidence(eid)

    witness_state.add_conversation(
        question=f"[Mnemonic Delving: {search_intent or 'unfocused'}]",
        response=narrator_text,
        trust_delta=trust_delta,
    )

    state.update_witness_state(witness_state)
    save_slot_state(state, player_id, slot)

    return InterrogateResponse(
        response=narrator_text,
        trust=witness_state.trust,
        trust_delta=trust_delta,
        secrets_revealed=secrets_revealed,
        secret_texts=secret_texts,
        updated_state=state.model_dump(mode="json"),
    )
