"""Tests for narrator spell integration."""

import pytest

from src.context.narrator import build_narrator_or_spell_prompt


class TestBuildNarratorOrSpellPrompt:
    """Tests for build_narrator_or_spell_prompt function."""

    @pytest.fixture
    def sample_evidence(self) -> list[dict]:
        """Sample hidden evidence."""
        return [
            {
                "id": "hidden_note",
                "triggers": ["under desk", "search desk"],
                "description": "A crumpled parchment.",
                "tag": "[EVIDENCE: hidden_note]",
            },
        ]

    @pytest.fixture
    def not_present_items(self) -> list[dict]:
        """Sample not_present items."""
        return [
            {
                "triggers": ["secret passage"],
                "response": "No passages here.",
            },
        ]

    @pytest.fixture
    def spell_contexts(self) -> dict:
        """Sample spell contexts."""
        return {
            "available_spells": ["unveil", "raise_the_lamp", "echo_reading"],
            "special_interactions": {
                "unveil": {
                    "targets": ["desk", "shelves"],
                    "reveals_evidence": ["hidden_note"],
                },
            },
        }

    def test_regular_input_returns_narrator_prompt(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
        spell_contexts: dict,
    ) -> None:
        """Regular input returns narrator prompt."""
        prompt, system_prompt, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="examine the desk",
            spell_contexts=spell_contexts,
        )

        assert is_spell is False
        assert "narrator" in system_prompt.lower()
        assert "examine the desk" in prompt

    def test_spell_input_returns_spell_prompt(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
        spell_contexts: dict,
    ) -> None:
        """Spell input returns spell prompt."""
        prompt, system_prompt, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="cast unveil on desk",
            spell_contexts=spell_contexts,
        )

        assert is_spell is True
        assert "Unveil" in prompt
        assert "rite effects" in system_prompt.lower()

    def test_spell_includes_location_context(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
        spell_contexts: dict,
    ) -> None:
        """Spell prompt includes location context."""
        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="A dusty library with towering shelves.",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="cast unveil on desk",
            spell_contexts=spell_contexts,
        )

        assert is_spell is True
        assert "dusty library" in prompt.lower()

    def test_spell_includes_valid_targets(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
        spell_contexts: dict,
    ) -> None:
        """Spell prompt includes valid targets from spell_contexts."""
        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="cast unveil",
            spell_contexts=spell_contexts,
        )

        assert is_spell is True
        assert "desk" in prompt
        assert "shelves" in prompt

    def test_spell_respects_discovered_evidence(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
        spell_contexts: dict,
    ) -> None:
        """Spell prompt respects already discovered evidence."""
        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=sample_evidence,
            discovered_ids=["hidden_note"],
            not_present=not_present_items,
            player_input="cast unveil on desk",
            spell_contexts=spell_contexts,
        )

        assert is_spell is True
        assert "ALREADY DISCOVERED" in prompt or "hidden_note" in prompt

    def test_casting_syntax_detected(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
        spell_contexts: dict,
    ) -> None:
        """'I'm casting' syntax detected as spell."""
        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="I'm casting Raise the Lamp",
            spell_contexts=spell_contexts,
        )

        assert is_spell is True
        assert "Raise the Lamp" in prompt

    def test_unknown_spell_handled(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
        spell_contexts: dict,
    ) -> None:
        """Unknown spell returns appropriate prompt."""
        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="cast expelliarmus",
            spell_contexts=spell_contexts,
        )

        # Unknown spells should not trigger spell mode
        assert is_spell is False

    def test_no_spell_contexts_works(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Works without spell_contexts parameter."""
        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="cast unveil",
        )

        assert is_spell is True
        assert "Unveil" in prompt


class TestSpellDetectionEdgeCases:
    """Edge cases for spell detection in narrator."""

    def test_partial_spell_name_not_detected(self) -> None:
        """Partial spell name in text not detected as spell."""
        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="I want to reveal something",
        )

        assert is_spell is False

    def test_spell_in_question_not_detected(self) -> None:
        """Question about spell not detected as casting."""
        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="What would unveil show me?",
        )

        assert is_spell is False

    def test_cast_without_spell_not_detected(self) -> None:
        """'cast' without valid spell not detected."""
        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="I cast my eyes around the room",
        )

        assert is_spell is False


class TestSpellToEvidenceMapping:
    """Tests for spell to evidence mapping."""

    def test_unveil_maps_to_hidden_note(self) -> None:
        """Unveil at desk can reveal hidden_note."""
        spell_contexts = {
            "special_interactions": {
                "unveil": {
                    "targets": ["desk"],
                    "reveals_evidence": ["hidden_note"],
                },
            },
        }

        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=[{"id": "hidden_note", "triggers": [], "description": "A note"}],
            discovered_ids=[],
            not_present=[],
            player_input="cast unveil on desk",
            spell_contexts=spell_contexts,
        )

        assert is_spell is True
        assert "hidden_note" in prompt

    def test_echo_reading_maps_to_focus_signature(self) -> None:
        """Echo Reading on focus can reveal focus_signature."""
        spell_contexts = {
            "special_interactions": {
                "echo_reading": {
                    "targets": ["focus", "victim_focus"],
                    "reveals_evidence": ["focus_signature"],
                },
            },
        }

        prompt, _, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=[{"id": "focus_signature", "triggers": [], "description": "Last spell"}],
            discovered_ids=[],
            not_present=[],
            player_input="cast echo reading on focus",
            spell_contexts=spell_contexts,
        )

        assert is_spell is True
        assert "focus_signature" in prompt
