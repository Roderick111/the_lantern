"""Tests for narrator prompt builder."""

import pytest

from src.context.narrator import (
    build_narrator_prompt,
    build_system_prompt,
    format_hidden_evidence,
    format_not_present,
    format_surface_elements,
)


class TestFormatHiddenEvidence:
    """Tests for format_hidden_evidence function."""

    @pytest.fixture
    def sample_evidence(self) -> list[dict]:
        """Sample hidden evidence."""
        return [
            {
                "id": "hidden_note",
                "triggers": ["under desk", "search desk"],
                "description": "A crumpled parchment hidden under the desk.",
                "tag": "[EVIDENCE: hidden_note]",
            },
            {
                "id": "focus_signature",
                "triggers": ["examine focus", "echo reading"],
                "description": "The last spell cast was Stupefy.",
                "tag": "[EVIDENCE: focus_signature]",
            },
        ]

    def test_format_all_evidence(self, sample_evidence: list[dict]) -> None:
        """Format all undiscovered evidence."""
        result = format_hidden_evidence(sample_evidence, discovered_ids=[])

        assert "hidden_note" in result
        assert "focus_signature" in result
        assert "under desk" in result
        assert "[EVIDENCE: hidden_note]" in result

    def test_excludes_discovered(self, sample_evidence: list[dict]) -> None:
        """Exclude already discovered evidence."""
        result = format_hidden_evidence(
            sample_evidence,
            discovered_ids=["hidden_note"],
        )

        assert "hidden_note" not in result
        assert "focus_signature" in result

    def test_all_discovered(self, sample_evidence: list[dict]) -> None:
        """All evidence discovered."""
        result = format_hidden_evidence(
            sample_evidence,
            discovered_ids=["hidden_note", "focus_signature"],
        )

        assert result == "All evidence has been discovered."


class TestFormatNotPresent:
    """Tests for format_not_present function."""

    @pytest.fixture
    def not_present_items(self) -> list[dict]:
        """Sample not_present items."""
        return [
            {
                "triggers": ["secret passage", "hidden door"],
                "response": "The walls are solid stone.",
            },
            {
                "triggers": ["blood", "blood stains"],
                "response": "No blood visible.",
            },
        ]

    def test_format_not_present(self, not_present_items: list[dict]) -> None:
        """Format not_present items."""
        result = format_not_present(not_present_items)

        assert "secret passage" in result
        assert "hidden door" in result
        assert "The walls are solid stone." in result
        assert "blood" in result

    def test_empty_not_present(self) -> None:
        """Empty not_present list."""
        result = format_not_present([])

        assert "No specific not_present items defined." in result


class TestFormatSurfaceElements:
    """Tests for format_surface_elements function."""

    def test_format_surface_elements(self) -> None:
        """Format surface elements list."""
        elements = [
            "Oak desk with scattered papers",
            "Dark arts books on shelves",
            "Frost-covered window",
        ]
        result = format_surface_elements(elements)

        assert "Oak desk with scattered papers" in result
        assert "Dark arts books on shelves" in result
        assert "Frost-covered window" in result

    def test_empty_surface_elements(self) -> None:
        """Empty surface elements list."""
        result = format_surface_elements([])

        assert "No specific surface elements defined." in result


class TestBuildNarratorPrompt:
    """Tests for build_narrator_prompt function."""

    @pytest.fixture
    def sample_evidence(self) -> list[dict]:
        """Sample hidden evidence."""
        return [
            {
                "id": "hidden_note",
                "triggers": ["under desk"],
                "description": "A hidden note.",
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

    def test_includes_location(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt includes location description."""
        prompt = build_narrator_prompt(
            location_desc="The dusty library stretches before you.",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="look around",
        )

        assert "The dusty library stretches before you." in prompt

    def test_includes_case_setting(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt includes parameterized case setting, not a hardcoded site."""
        prompt = build_narrator_prompt(
            location_desc="A candlelit vault.",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="look around",
            case_setting="Ironwright Vaults, winter 1888",
        )

        assert "Ironwright Vaults, winter 1888" in prompt
        assert "Blackwood Collegiate" not in prompt

    def test_includes_player_input(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt includes player input."""
        prompt = build_narrator_prompt(
            location_desc="Library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="I search under the desk",
        )

        assert '"I search under the desk"' in prompt

    def test_includes_evidence_tag_instruction(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt includes EVIDENCE tag instruction."""
        prompt = build_narrator_prompt(
            location_desc="Library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="test",
        )

        assert "[EVIDENCE:" in prompt
        assert "ALWAYS use EXACTLY this format when revealing evidence: [EVIDENCE: id]" in prompt

    def test_includes_response_length_rule(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt enforces response length guidelines."""
        prompt = build_narrator_prompt(
            location_desc="Library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="test",
        )

        assert "LENGTH:" in prompt
        assert "YOUR NARRATOR VOICE" in prompt

    def test_shows_discovered_evidence(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt shows already discovered evidence."""
        prompt = build_narrator_prompt(
            location_desc="Library",
            hidden_evidence=sample_evidence,
            discovered_ids=["hidden_note"],
            not_present=not_present_items,
            player_input="test",
        )

        assert "ALREADY DISCOVERED" in prompt
        assert "hidden_note" in prompt

    def test_shows_none_discovered(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt shows 'None' when no evidence discovered."""
        prompt = build_narrator_prompt(
            location_desc="Library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="test",
        )

        assert "ALREADY DISCOVERED" in prompt
        # Check for "None" in the discovered section
        lines = prompt.split("\n")
        discovered_section = False
        for line in lines:
            if "ALREADY DISCOVERED" in line:
                discovered_section = True
            elif discovered_section and line.strip():
                assert "None" in line
                break

    def test_includes_not_present(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt includes not_present items."""
        prompt = build_narrator_prompt(
            location_desc="Library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="test",
        )

        assert "NOT PRESENT" in prompt
        assert "secret passage" in prompt
        assert "No passages here." in prompt

    def test_includes_rules(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt includes narrator rules."""
        prompt = build_narrator_prompt(
            location_desc="Library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="test",
        )

        assert "== CRITICAL RULES ==" in prompt
        assert "NEVER invent evidence" in prompt

    def test_includes_surface_elements(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt includes surface elements for prose integration."""
        surface_elements = [
            "Oak desk with scattered papers",
            "Dark arts books on shelves",
        ]
        prompt = build_narrator_prompt(
            location_desc="Library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="test",
            surface_elements=surface_elements,
        )

        assert "VISIBLE ELEMENTS" in prompt
        assert "Oak desk with scattered papers" in prompt
        assert "Dark arts books on shelves" in prompt
        assert "weave naturally into descriptions" in prompt

    def test_surface_elements_optional(
        self,
        sample_evidence: list[dict],
        not_present_items: list[dict],
    ) -> None:
        """Prompt works without surface_elements (backward compatibility)."""
        prompt = build_narrator_prompt(
            location_desc="Library",
            hidden_evidence=sample_evidence,
            discovered_ids=[],
            not_present=not_present_items,
            player_input="test",
        )

        # Should still have the section but with empty message
        assert "VISIBLE ELEMENTS" in prompt
        assert "No specific surface elements defined." in prompt


class TestBuildSystemPrompt:
    """Tests for build_system_prompt function."""

    def test_system_prompt_has_role(self) -> None:
        """System prompt defines narrator role."""
        prompt = build_system_prompt()

        assert "narrator" in prompt.lower()
        assert "Victorian occult detective" in prompt

    def test_system_prompt_has_hard_rules(self) -> None:
        """System prompt includes hard rules for evidence handling."""
        prompt = build_system_prompt(case_setting="Candlewick Lane, 1886")

        assert "EVIDENCE" in prompt
        assert "Never invent" in prompt
        assert "rite to perform" in prompt
        assert "Candlewick Lane, 1886" in prompt

    def test_system_prompt_no_hallucination(self) -> None:
        """System prompt prevents hallucination."""
        prompt = build_system_prompt()

        assert "Never invent" in prompt


class TestFormatNarratorConversationHistory:
    """Tests for format_narrator_conversation_history function."""

    def test_format_empty_history(self) -> None:
        """Empty history returns first action message."""
        from src.context.narrator import format_narrator_conversation_history

        result = format_narrator_conversation_history([])
        assert result == "This is the player's first action at this location."

    def test_format_single_exchange(self) -> None:
        """Single exchange formatted correctly."""
        from src.context.narrator import format_narrator_conversation_history

        history = [{"question": "examine desk", "response": "The desk is dusty."}]
        result = format_narrator_conversation_history(history)

        assert "Player: examine desk" in result
        assert "You responded: The desk is dusty." in result

    def test_format_multiple_exchanges(self) -> None:
        """Multiple exchanges formatted in order."""
        from src.context.narrator import format_narrator_conversation_history

        history = [
            {"question": "look around", "response": "The room is dark."},
            {"question": "check window", "response": "The window is frosted."},
        ]
        result = format_narrator_conversation_history(history)

        lines = result.split("\n")
        assert "Player: look around" in lines[0]
        assert "Player: check window" in result

    def test_format_limits_to_20_exchanges(self) -> None:
        """Only last 20 exchanges are formatted."""
        from src.context.narrator import format_narrator_conversation_history

        history = [{"question": f"action {i}", "response": f"response {i}"} for i in range(25)]
        result = format_narrator_conversation_history(history)

        # Should only have actions 5-24 (last 20)
        assert "action 0" not in result
        assert "action 4" not in result
        assert "action 5" in result
        assert "action 24" in result

    def test_format_handles_missing_keys(self) -> None:
        """Handles missing keys gracefully."""
        from src.context.narrator import format_narrator_conversation_history

        history = [
            {"question": "test", "response": "response"},
            {},  # Missing both keys
        ]
        result = format_narrator_conversation_history(history)

        assert "Player: test" in result
        assert "Player: " in result  # Empty question still formatted


class TestBuildNarratorPromptWithHistory:
    """Tests for build_narrator_prompt with conversation_history parameter."""

    def test_includes_conversation_history_section(self) -> None:
        """Prompt includes conversation history section."""
        from src.context.narrator import build_narrator_prompt

        history = [{"question": "examine desk", "response": "The desk is dusty."}]
        prompt = build_narrator_prompt(
            location_desc="A dark room",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="check window",
            conversation_history=history,
        )

        assert "RECENT CONVERSATION AT THIS LOCATION" in prompt
        assert "Player: examine desk" in prompt
        assert "You responded: The desk is dusty." in prompt

    def test_history_none_shows_first_action(self) -> None:
        """None history shows first action message."""
        from src.context.narrator import build_narrator_prompt

        prompt = build_narrator_prompt(
            location_desc="A dark room",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="look around",
            conversation_history=None,
        )

        assert "This is the player's first action at this location" in prompt

    def test_includes_no_repeat_instruction(self) -> None:
        """Prompt includes instruction not to repeat descriptions."""
        from src.context.narrator import build_narrator_prompt

        prompt = build_narrator_prompt(
            location_desc="A dark room",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="look around",
        )

        assert "Vary descriptions" in prompt or "don't repeat" in prompt or "check conversation history" in prompt.lower()


# =============================================================================
# Phase 4.7: Spell Outcome Integration Tests
# =============================================================================


class TestBuildNarratorOrSpellPromptWithSpellOutcome:
    """Tests for build_narrator_or_spell_prompt with spell_outcome parameter (Phase 4.7)."""

    def test_spell_outcome_passed_to_spell_prompt(self) -> None:
        """spell_outcome is passed through to spell prompt."""
        from src.context.narrator import build_narrator_or_spell_prompt

        prompt, system_prompt, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="cast unveil on desk",
            spell_outcome="SUCCESS",
        )

        assert is_spell is True
        assert "RITE OUTCOME" in prompt
        assert "SUCCESS" in prompt

    def test_spell_outcome_failure_passed(self) -> None:
        """FAILURE spell_outcome is passed through."""
        from src.context.narrator import build_narrator_or_spell_prompt

        prompt, system_prompt, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="cast raise_the_lamp",
            spell_outcome="FAILURE",
        )

        assert is_spell is True
        assert "FAILURE" in prompt
        assert "fizzles" in prompt.lower()

    def test_spell_outcome_none_uses_legacy(self) -> None:
        """None spell_outcome uses legacy flow."""
        from src.context.narrator import build_narrator_or_spell_prompt

        prompt, system_prompt, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="cast unveil",
            # spell_outcome not passed (None)
        )

        assert is_spell is True
        assert "RITE OUTCOME" in prompt
        assert "legacy" in prompt.lower() or "Not calculated" in prompt

    def test_non_spell_ignores_outcome(self) -> None:
        """Non-spell input ignores spell_outcome."""
        from src.context.narrator import build_narrator_or_spell_prompt

        prompt, system_prompt, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="examine the desk",
            spell_outcome="SUCCESS",  # Should be ignored
        )

        assert is_spell is False
        assert "RITE OUTCOME" not in prompt
        assert "SUCCESS" not in prompt

    def test_backward_compatible_without_spell_outcome(self) -> None:
        """Function works without spell_outcome parameter (backward compatible)."""
        from src.context.narrator import build_narrator_or_spell_prompt

        # Should not raise any errors
        prompt, system_prompt, is_spell = build_narrator_or_spell_prompt(
            location_desc="The library",
            hidden_evidence=[],
            discovered_ids=[],
            not_present=[],
            player_input="cast unveil",
        )

        assert is_spell is True
        assert "RITE OUTCOME" in prompt
