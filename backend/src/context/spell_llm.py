"""Spell LLM context builder for spell effect narration.

Re-export hub for backward compatibility. Actual implementations live in:
- spell_detection.py: Spell detection, fuzzy matching, success calculation
- spell_prompts.py: Prompt building for spell narration

A2 Spell Detector Unification: detect_spell_with_fuzzy is source of truth.
Legacy is_spell_input/parse_spell_from_input delegate to it (see spell_detection).
Routes + narrator + witnesses all use unified fuzzy path.
"""

__all__ = [
    "INTENT_PHRASES",
    "SAFE_INVESTIGATION_SPELLS",
    "SPELL_SEMANTIC_PHRASES",
    "_build_spell_outcome_section",
    "_build_unknown_spell_prompt",
    "_format_revealable_evidence",
    "_is_valid_spell_cast",
    "_normalize_spell_name",
    "build_mnemonic_delving_narration_prompt",
    "build_spell_effect_prompt",
    "calculate_mnemonic_delving_specificity_bonus",
    "calculate_mnemonic_delving_success",
    "calculate_specificity_bonus",
    "calculate_spell_success",
    "detect_focused_mnemonic_delving",
    "detect_spell_with_fuzzy",
    "extract_intent_from_input",
    "extract_target_from_input",
    "is_spell_input",
    "normalize_spell_target",
    "parse_spell_from_input",
]

# Re-export everything from spell_detection
from src.context.spell_detection import (  # noqa: F401
    INTENT_PHRASES,
    SAFE_INVESTIGATION_SPELLS,
    SPELL_SEMANTIC_PHRASES,
    _is_valid_spell_cast,
    _normalize_spell_name,
    calculate_mnemonic_delving_specificity_bonus,
    calculate_mnemonic_delving_success,
    calculate_specificity_bonus,
    calculate_spell_success,
    detect_focused_mnemonic_delving,
    detect_spell_with_fuzzy,
    extract_intent_from_input,
    extract_target_from_input,
    is_spell_input,
    normalize_spell_target,
    parse_spell_from_input,
)

# Re-export everything from spell_prompts
from src.context.spell_prompts import (  # noqa: F401
    _build_spell_outcome_section,
    _build_unknown_spell_prompt,
    _format_revealable_evidence,
    build_mnemonic_delving_narration_prompt,
    build_spell_effect_prompt,
)
