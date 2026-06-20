"""Spell system for Lantern Inspector investigations.

Provides spell definitions and metadata for the rite system.
"""

from src.spells.definitions import SPELL_DEFINITIONS, get_spell, is_restricted_spell

__all__ = ["SPELL_DEFINITIONS", "get_spell", "is_restricted_spell"]
