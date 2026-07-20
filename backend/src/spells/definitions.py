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
        "formula_en": "Veil, dissolve",
        "formula_ru": "Скрытое, явись",
        "description_en": "Reveals hidden writing, concealments, and a thing's true form.",
        "description_ru": "Проявляет скрытые записи, маскировку и подлинный вид вещей.",
        "example_en": "Veil, dissolve over this desk.",
        "example_ru": "Скрытое, явись на этом столе.",
        "legacy_names_en": ["Unveil", "Hidden things, reveal yourselves"],
        "legacy_names_ru": ["снять покров", "открыть скрытое"],
        "description": "What's hidden wants to stay hidden. This charm convinces it otherwise—invisible ink bleeds into view, concealment cantrips flicker and fade, disguised objects remember their true form.",
        "safety_level": "safe",
        "category": "detection",
    },
    "sense_presence": {
        "name": "Sense Presence",
        "formula_en": "Presence, answer",
        "formula_ru": "Присутствие, отзовись",
        "description_en": "Detects someone nearby, even through walls or concealment.",
        "description_ru": "Обнаруживает присутствие рядом, даже за стеной или под маскировкой.",
        "example_en": "Presence, answer beyond this wall.",
        "example_ru": "Присутствие, отзовись за этой стеной.",
        "legacy_names_en": ["Sense Presence", "homenum unveil", "homenum", "Presence, make yourself known"],
        "legacy_names_ru": ["ощутить присутствие", "почувствовать присутствие"],
        "description": "The air shivers when someone's near. This charm reads that shiver—even through walls, even under cloaks meant to deceive. Useful when you suspect you're not alone.",
        "safety_level": "safe",
        "category": "detection",
    },
    "identify_substance": {
        "name": "Identify Substance",
        "formula_en": "Essence, speak",
        "formula_ru": "Суть, откройся",
        "description_en": "Reveals the nature of a potion, poison, cursed object, or magical residue.",
        "description_ru": "Раскрывает природу зелья, яда, проклятой вещи или магического следа.",
        "example_en": "Essence, speak in this vial.",
        "example_ru": "Суть, откройся в этом флаконе.",
        "legacy_names_en": ["Identify Substance", "specialis unveil", "specialis", "Essence, declare yourself"],
        "legacy_names_ru": ["опознать вещество", "опознать зелье"],
        "description": "Alchemist's gift to investigators. Whisper this over a suspect potion and watch its secrets unravel—enchantments glow, poisons betray themselves, cursed objects confess their nature.",
        "safety_level": "safe",
        "category": "analysis",
    },
    "raise_the_lamp": {
        "name": "Raise the Lamp",
        "formula_en": "Trace, gleam",
        "formula_ru": "Свет, укажи след",
        "description_en": "Draws blood, burns, and things hiding in shadow into view.",
        "description_ru": "Выводит на свет кровь, ожоги и то, что прячется в тени.",
        "example_en": "Trace, gleam in the alcove.",
        "example_ru": "Свет, укажи след в нише.",
        "legacy_names_en": ["Raise the Lamp", "Light, show the trace"],
        "legacy_names_ru": ["поднять лампу", "осветить"],
        "description": "Light reveals what darkness protects. More than mere illumination—lamplight clings to bloodstains, traces the ghost of fire, shows you the things that hide between shadow and sight.",
        "safety_level": "safe",
        "category": "detection",
    },
    "echo_reading": {
        "name": "Echo Reading",
        "formula_en": "Echo, speak",
        "formula_ru": "Отзвук чар, явись",
        "description_en": "Reveals the last magical traces stored in a focus held in hand.",
        "description_ru": "Показывает последние чары, оставшиеся на фокусе в руке.",
        "example_en": "Echo, speak on Elena's focus.",
        "example_ru": "Отзвук чар, явись на фокусе Елены.",
        "legacy_names_en": ["Echo Reading"],
        "legacy_names_ru": ["чтение эха", "прочитать отзвук"],
        "description": "Every focus remembers. Force it to speak and ghostly echoes rise—the last spells it cast, shadows of magic long finished. The focus must be in your hand for it to confess.",
        "safety_level": "safe",
        "category": "analysis",
    },
    "mend": {
        "name": "Mend",
        "formula_en": "Shards, unite",
        "formula_ru": "Разбитое, сойдись",
        "description_en": "Restores a broken object and leaves clues about how it broke.",
        "description_ru": "Восстанавливает разбитую вещь и оставляет следы того, как она сломалась.",
        "example_en": "Shards, unite.",
        "example_ru": "Разбитое стекло, сойдись.",
        "legacy_names_en": ["Mend", "Broken thing, be whole"],
        "legacy_names_ru": ["починить", "восстановить"],
        "description": "Shattered things yearn to be whole. As the pieces float back together, watch closely—the way glass breaks tells you how it was broken. Violence leaves patterns.",
        "safety_level": "safe",
        "category": "restoration",
    },
    "mnemonic_delving": {
        "name": "Mnemonic Delving",
        "formula_en": "Memory, open",
        "formula_ru": "Чужая память, отворись",
        "description_en": "Enters another person's memory. Intrusion can be noticed and carries consequences.",
        "description_ru": "Позволяет войти в чужую память. Вторжение могут заметить, и оно имеет последствия.",
        "example_en": "Memory, open on Elena's recollection of the archive.",
        "example_ru": "Чужая память, отворись на воспоминание Елены о библиотеке.",
        "legacy_names_en": ["Mnemonic Delving", "legulemancy"],
        "legacy_names_ru": ["погружение в память", "войти в память", "заглянуть в память"],
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
