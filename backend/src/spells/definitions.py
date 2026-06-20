"""Spell definitions for Lantern Inspector investigations.

Central spell metadata for the rite system. KISS principle - simple dict,
no Pydantic classes needed.

7 rites total:
- 6 safe investigation rites (Unveil, Sense Presence, Identify Substance,
  Raise the Lamp, Echo Reading, Mend)
- 1 restricted spell (Mnemonic Delving)
"""

from typing import Any

# Spell definitions - central source of truth
SPELL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "unveil": {
        "name": "Unveil",
        "description": "What's hidden wants to stay hidden. This charm convinces it otherwise—invisible ink bleeds into view, concealment cantrips flicker and fade, disguised objects remember their true form.",
        "safety_level": "safe",
        "category": "detection",
    },
    "sense_presence": {
        "name": "Sense Presence",
        "description": "The air shivers when someone's near. This charm reads that shiver—even through walls, even under cloaks meant to deceive. Useful when you suspect you're not alone.",
        "safety_level": "safe",
        "category": "detection",
    },
    "identify_substance": {
        "name": "Identify Substance",
        "description": "Alchemist's gift to investigators. Whisper this over a suspect potion and watch its secrets unravel—enchantments glow, poisons betray themselves, cursed objects confess their nature.",
        "safety_level": "safe",
        "category": "analysis",
    },
    "raise_the_lamp": {
        "name": "Raise the Lamp",
        "description": "Light reveals what darkness protects. More than mere illumination—lamplight clings to bloodstains, traces the ghost of fire, shows you the things that hide between shadow and sight.",
        "safety_level": "safe",
        "category": "detection",
    },
    "echo_reading": {
        "name": "Echo Reading",
        "description": "Every focus remembers. Force it to speak and ghostly echoes rise—the last spells it cast, shadows of magic long finished. The focus must be in your hand for it to confess.",
        "safety_level": "safe",
        "category": "analysis",
    },
    "mend": {
        "name": "Mend",
        "description": "Shattered things yearn to be whole. As the pieces float back together, watch closely—the way glass breaks tells you how it was broken. Violence leaves patterns.",
        "safety_level": "safe",
        "category": "restoration",
    },
    "mnemonic_delving": {
        "name": "Mnemonic Delving",
        "description": "The mind has no lock a skilled Mnemonic Delver cannot pick. Slip past the eyes into memory itself—but tread carefully. Minds resist intrusion, and some remember being violated long after you've withdrawn.",
        "safety_level": "restricted",
        "category": "mental",
    },
}


def get_spell(spell_id: str) -> dict[str, Any] | None:
    """Get spell definition by ID.

    Args:
        spell_id: Spell identifier (lowercase, e.g., "unveil")

    Returns:
        Spell definition dict or None if not found
    """
    return SPELL_DEFINITIONS.get(spell_id.lower())


def is_restricted_spell(spell_id: str) -> bool:
    """Check if spell is restricted (requires authorization).

    Args:
        spell_id: Spell identifier

    Returns:
        True if spell is restricted, False otherwise
    """
    spell = get_spell(spell_id)
    if spell is None:
        return False
    return spell.get("safety_level") == "restricted"


def list_safe_spells() -> list[str]:
    """Get list of safe (non-restricted) spell IDs.

    Returns:
        List of safe spell IDs
    """
    return [
        spell_id
        for spell_id, spell in SPELL_DEFINITIONS.items()
        if spell.get("safety_level") == "safe"
    ]


def list_all_spells() -> list[str]:
    """Get list of all spell IDs.

    Returns:
        List of all spell IDs
    """
    return list(SPELL_DEFINITIONS.keys())
