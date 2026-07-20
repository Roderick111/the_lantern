"""Tests for spell definitions module."""

from src.spells.definitions import (
    SPELL_DEFINITIONS,
    get_spell,
    is_restricted_spell,
    list_all_spells,
    list_safe_spells,
)


class TestSpellDefinitions:
    """Tests for SPELL_DEFINITIONS constant."""

    def test_has_seven_spells(self) -> None:
        """SPELL_DEFINITIONS contains exactly 7 rites."""
        assert len(SPELL_DEFINITIONS) == 7

    def test_has_unveil(self) -> None:
        """Contains Unveil spell."""
        assert "unveil" in SPELL_DEFINITIONS
        spell = SPELL_DEFINITIONS["unveil"]
        assert spell["name"] == "Unveil"
        assert spell["safety_level"] == "safe"
        assert spell["category"] == "detection"

    def test_has_sense_presence(self) -> None:
        """Contains Sense Presence spell."""
        assert "sense_presence" in SPELL_DEFINITIONS
        spell = SPELL_DEFINITIONS["sense_presence"]
        assert spell["name"] == "Sense Presence"
        assert spell["safety_level"] == "safe"
        assert spell["category"] == "detection"

    def test_has_identify_substance(self) -> None:
        """Contains Identify Substance spell."""
        assert "identify_substance" in SPELL_DEFINITIONS
        spell = SPELL_DEFINITIONS["identify_substance"]
        assert spell["name"] == "Identify Substance"
        assert spell["safety_level"] == "safe"
        assert spell["category"] == "analysis"

    def test_has_raise_the_lamp(self) -> None:
        """Contains Raise the Lamp spell."""
        assert "raise_the_lamp" in SPELL_DEFINITIONS
        spell = SPELL_DEFINITIONS["raise_the_lamp"]
        assert spell["name"] == "Raise the Lamp"
        assert spell["safety_level"] == "safe"
        assert spell["category"] == "detection"

    def test_has_echo_reading(self) -> None:
        """Contains Echo Reading spell."""
        assert "echo_reading" in SPELL_DEFINITIONS
        spell = SPELL_DEFINITIONS["echo_reading"]
        assert spell["name"] == "Echo Reading"
        assert spell["safety_level"] == "safe"
        assert spell["category"] == "analysis"

    def test_has_mend(self) -> None:
        """Contains Mend spell."""
        assert "mend" in SPELL_DEFINITIONS
        spell = SPELL_DEFINITIONS["mend"]
        assert spell["name"] == "Mend"
        assert spell["safety_level"] == "safe"
        assert spell["category"] == "restoration"

    def test_has_mnemonic_delving(self) -> None:
        """Contains Mnemonic Delving spell (restricted)."""
        assert "mnemonic_delving" in SPELL_DEFINITIONS
        spell = SPELL_DEFINITIONS["mnemonic_delving"]
        assert spell["name"] == "Mnemonic Delving"
        assert spell["safety_level"] == "restricted"
        assert spell["category"] == "mental"

    def test_all_spells_have_required_fields(self) -> None:
        """All spells have required fields."""
        required_fields = [
            "name",
            "description",
            "formula_en",
            "formula_ru",
            "description_en",
            "description_ru",
            "example_en",
            "example_ru",
            "legacy_names_en",
            "legacy_names_ru",
            "safety_level",
            "category",
        ]

        for spell_id, spell in SPELL_DEFINITIONS.items():
            for field in required_fields:
                assert field in spell, f"Spell {spell_id} missing field {field}"
                assert spell[field], f"Spell {spell_id} has empty {field}"

    def test_safety_levels_valid(self) -> None:
        """All spells have valid safety levels."""
        valid_levels = {"safe", "restricted"}

        for spell_id, spell in SPELL_DEFINITIONS.items():
            assert spell["safety_level"] in valid_levels, (
                f"Spell {spell_id} has invalid safety_level: {spell['safety_level']}"
            )

    def test_categories_valid(self) -> None:
        """All spells have valid categories."""
        valid_categories = {"detection", "analysis", "restoration", "mental"}

        for spell_id, spell in SPELL_DEFINITIONS.items():
            assert spell["category"] in valid_categories, (
                f"Spell {spell_id} has invalid category: {spell['category']}"
            )


class TestGetSpell:
    """Tests for get_spell function."""

    def test_get_existing_spell(self) -> None:
        """Get existing spell returns spell dict."""
        spell = get_spell("unveil")
        assert spell is not None
        assert spell["name"] == "Unveil"

    def test_get_nonexistent_spell(self) -> None:
        """Get nonexistent spell returns None."""
        spell = get_spell("expelliarmus")
        assert spell is None

    def test_case_insensitive(self) -> None:
        """Get spell is case insensitive."""
        spell_lower = get_spell("unveil")
        spell_upper = get_spell("UNVEIL")
        spell_mixed = get_spell("UnVeil")

        assert spell_lower is not None
        assert spell_upper is not None
        assert spell_mixed is not None
        assert spell_lower["name"] == spell_upper["name"] == spell_mixed["name"]

    def test_get_restricted_spell(self) -> None:
        """Get restricted spell returns correct data."""
        spell = get_spell("mnemonic_delving")
        assert spell is not None
        assert spell["safety_level"] == "restricted"


class TestIsRestrictedSpell:
    """Tests for is_restricted_spell function."""

    def test_mnemonic_delving_is_restricted(self) -> None:
        """Mnemonic Delving is restricted."""
        assert is_restricted_spell("mnemonic_delving") is True

    def test_unveil_not_restricted(self) -> None:
        """Unveil is not restricted."""
        assert is_restricted_spell("unveil") is False

    def test_all_safe_spells_not_restricted(self) -> None:
        """All safe spells are not restricted."""
        safe_spells = [
            "unveil",
            "sense_presence",
            "identify_substance",
            "raise_the_lamp",
            "echo_reading",
            "mend",
        ]

        for spell_id in safe_spells:
            assert is_restricted_spell(spell_id) is False, f"{spell_id} should not be restricted"

    def test_unknown_spell_not_restricted(self) -> None:
        """Unknown spell returns False (not restricted)."""
        assert is_restricted_spell("unknown_spell") is False


class TestListSpells:
    """Tests for list spell functions."""

    def test_list_safe_spells(self) -> None:
        """List safe spells returns 6 spells."""
        safe = list_safe_spells()
        assert len(safe) == 6
        assert "mnemonic_delving" not in safe
        assert "unveil" in safe

    def test_list_all_spells(self) -> None:
        """List all spells returns 7 rites."""
        all_spells = list_all_spells()
        assert len(all_spells) == 7
        assert "mnemonic_delving" in all_spells
        assert "unveil" in all_spells
