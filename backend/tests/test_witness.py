"""Tests for witness context builder module (Phase 8.0 — Trust + Pressure)."""

import pytest

from src.context.witness import (
    build_witness_prompt,
    build_witness_system_prompt,
    describe_pressure,
    format_conversation_history,
    format_evidence_shown,
    format_knowledge,
    format_secrets,
)


@pytest.fixture
def sample_witness() -> dict:
    """Sample witness data for testing."""
    return {
        "id": "elena",
        "name": "Elena Marsh",
        "personality": "Brilliant student. Values truth and logic.",
        "background": "Top student. Peers with Cassian and Rowan.",
        "base_trust": 50,
        "knowledge": [
            "Was in library from 8:30pm to 9:30pm",
            "Heard raised voices around 9:00pm",
            "Saw someone running past the stacks",
        ],
        "secrets": [
            {
                "id": "saw_cassian",
                "trigger": "evidence:frost_pattern OR trust>70",
                "text": "I saw Cassian near the window at 9pm.",
                "why_hiding": "I don't want to accuse anyone without proof",
            },
            {
                "id": "borrowed_book",
                "trigger": "trust>80",
                "text": "I borrowed a restricted book.",
                "why_hiding": "Could get me expelled",
            },
        ],
        "lies": [
            {
                "condition": "trust<30",
                "topics": ["where were you", "that night"],
                "response": "I was in the common room all night.",
            },
        ],
    }


class TestFormatKnowledge:
    """Tests for format_knowledge function."""

    def test_format_knowledge_list(self) -> None:
        knowledge = ["Fact 1", "Fact 2", "Fact 3"]
        result = format_knowledge(knowledge)
        assert "- Fact 1" in result
        assert "- Fact 2" in result

    def test_format_empty_knowledge(self) -> None:
        result = format_knowledge([])
        assert "No specific knowledge" in result


class TestFormatSecrets:
    """Tests for format_secrets function (Phase 8.0 — full text, no filtering)."""

    def test_format_all_secrets_with_full_text(self) -> None:
        """All secrets shown with full text regardless of trust."""
        secrets = [
            {"id": "secret1", "text": "Secret text 1", "why_hiding": "Reason 1"},
            {"id": "secret2", "text": "Secret text 2"},
        ]
        result = format_secrets(secrets)

        assert "[secret1]" in result
        assert "Secret text 1" in result
        assert "Reason 1" in result
        assert "[secret2]" in result
        assert "Secret text 2" in result

    def test_format_no_secrets(self) -> None:
        result = format_secrets([])
        assert "no secrets to hide" in result.lower()


class TestFormatConversationHistory:
    """Tests for format_conversation_history function."""

    def test_format_history(self) -> None:
        history = [
            {"question": "Where were you?", "response": "In the library."},
            {"question": "What did you see?", "response": "Someone running."},
        ]
        result = format_conversation_history(history)
        assert "Player: Where were you?" in result
        assert "You: In the library." in result

    def test_format_empty_history(self) -> None:
        result = format_conversation_history([])
        assert "start of the conversation" in result

    def test_limits_to_last_20_exchanges(self) -> None:
        history = [{"question": f"Q{i}", "response": f"R{i}"} for i in range(30)]
        result = format_conversation_history(history)
        assert "Q0" not in result
        assert "Q9" not in result
        assert "Q10" in result
        assert "Q29" in result


class TestFormatEvidenceShown:
    """Tests for format_evidence_shown function."""

    def test_empty_evidence(self) -> None:
        result = format_evidence_shown([])
        assert result == ""

    def test_evidence_with_implication(self) -> None:
        details = [
            {"name": "Torn Letter", "implicates_me": True},
            {"name": "Frost Pattern", "implicates_me": False},
        ]
        result = format_evidence_shown(details)
        assert "Torn Letter" in result
        assert "implicates YOU" in result
        assert "Frost Pattern" in result


class TestDescribePressure:
    """Tests for describe_pressure function."""

    def test_no_pressure(self) -> None:
        assert "NONE" in describe_pressure(0)

    def test_low_pressure(self) -> None:
        assert "LOW" in describe_pressure(50)

    def test_moderate_pressure(self) -> None:
        assert "MODERATE" in describe_pressure(100)

    def test_high_pressure(self) -> None:
        assert "HIGH" in describe_pressure(200)

    def test_crushing_pressure(self) -> None:
        assert "CRUSHING" in describe_pressure(300)


class TestBuildWitnessPrompt:
    """Tests for build_witness_prompt function."""

    def test_prompt_contains_witness_name(self, sample_witness: dict) -> None:
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=50,

            conversation_history=[],
            player_input="Where were you?",
            case_context={
                "crime_type": "assault",
                "location": "the Sealed Archive",
                "setting": "Blackwood Collegiate, autumn 1890",
            },
        )
        assert "Elena Marsh" in prompt
        assert "the Sealed Archive" in prompt
        assert "Blackwood Collegiate, autumn 1890" in prompt
        assert "crime at Blackwood Collegiate" not in prompt

    def test_prompt_contains_personality(self, sample_witness: dict) -> None:
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=50,

            conversation_history=[],
            player_input="Where were you?",
        )
        assert "Brilliant student" in prompt

    def test_prompt_contains_knowledge(self, sample_witness: dict) -> None:
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=50,

            conversation_history=[],
            player_input="Where were you?",
        )
        assert "library from 8:30pm" in prompt

    def test_prompt_contains_trust_and_pressure(self, sample_witness: dict) -> None:
        """Prompt includes both trust and pressure as numbers."""
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=65,

            conversation_history=[],
            player_input="Where were you?",
            pressure=150,
        )
        assert "Trust: 65/100" in prompt
        assert "COOPERATIVE" in prompt
        assert "Pressure: 150" in prompt
        assert "Stance:" in prompt

    def test_prompt_contains_player_input(self, sample_witness: dict) -> None:
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=50,

            conversation_history=[],
            player_input="What did you see at 9pm?",
        )
        assert "What did you see at 9pm?" in prompt

    def test_system_prompt_contains_calibration(self) -> None:
        """System prompt includes trust+pressure behavioral guidance."""
        prompt = build_witness_system_prompt("Elena Marsh")
        assert "Low trust + low pressure" in prompt
        assert "High trust + high pressure" in prompt

    def test_secrets_always_full_text(self, sample_witness: dict) -> None:
        """Secrets include full text at ANY trust level (no compression)."""
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=20,

            conversation_history=[],
            player_input="Where were you?",
        )
        assert "saw Cassian near the window" in prompt
        assert "borrowed a restricted book" in prompt

    def test_no_mandatory_lie_system(self, sample_witness: dict) -> None:
        """No MANDATORY LIE or COVER STORY section — LLM decides from trust+pressure."""
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=20,

            conversation_history=[],
            player_input="Where were you that night?",
        )
        assert "MANDATORY LIE" not in prompt
        assert "COVER STORY" not in prompt
        assert "MUST respond with" not in prompt

    def test_evidence_presented_in_prompt(self, sample_witness: dict) -> None:
        """Evidence presentation adds section to prompt."""
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=50,

            conversation_history=[],
            player_input="I'd like to show you this evidence: Frost Pattern",
            evidence_presented={
                "name": "Frost Pattern",
                "description": "Geometric frost on the floor.",
                "witness_reaction": "*eyes widen* That's not natural frost...",
            },
        )
        assert "EVIDENCE BEING PRESENTED" in prompt
        assert "Frost Pattern" in prompt
        assert "gut reaction" in prompt
        assert "*eyes widen*" in prompt

    def test_evidence_shown_list_in_prompt(self, sample_witness: dict) -> None:
        """Previously shown evidence listed in prompt."""
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=50,

            conversation_history=[],
            player_input="Tell me more.",
            evidence_shown_details=[
                {"name": "Torn Letter", "implicates_me": True},
                {"name": "Frost Pattern", "implicates_me": False},
            ],
        )
        assert "EVIDENCE THE LANTERN INSPECTOR HAS SHOWN YOU" in prompt
        assert "Torn Letter" in prompt
        assert "implicates YOU" in prompt

    def test_pressure_description_in_prompt(self, sample_witness: dict) -> None:
        """Pressure is described in natural language."""
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=30,

            conversation_history=[],
            player_input="What happened?",
            pressure=250,
        )
        assert "CRUSHING" in prompt

    def test_system_prompt_contains_contradiction_rules(self) -> None:
        """System prompt instructs LLM about handling contradictions."""
        prompt = build_witness_system_prompt("Elena Marsh")
        assert "contradiction" in prompt.lower()
        assert "FORBIDDEN" in prompt


class TestBuildWitnessSystemPrompt:
    """Tests for build_witness_system_prompt function."""

    def test_system_prompt_contains_name(self) -> None:
        prompt = build_witness_system_prompt("Elena Marsh")
        assert "Elena Marsh" in prompt

    def test_system_prompt_mentions_trust_and_pressure(self) -> None:
        prompt = build_witness_system_prompt("Elena Marsh")
        assert "trust" in prompt.lower()
        assert "pressure" in prompt.lower()

    def test_system_prompt_contains_isolation(self) -> None:
        prompt = build_witness_system_prompt("Elena Marsh")
        assert "ISOLATION" in prompt or "SEPARATE" in prompt

    def test_system_prompt_contains_style_guidance(self) -> None:
        prompt = build_witness_system_prompt("Elena Marsh")
        assert "first person" in prompt.lower()
        assert "2-4 sentences" in prompt

    def test_system_prompt_includes_shared_style_filter(self) -> None:
        prompt = build_witness_system_prompt("Elena Marsh")
        assert "STYLE FILTER" in prompt
        assert "Maximum one em dash" in prompt
        assert "Use spaces around em dashes" not in prompt


class TestPromptIntegration:
    """Integration tests for witness prompts."""

    def test_full_prompt_structure(self, sample_witness: dict) -> None:
        """Full prompt has all expected sections."""
        prompt = build_witness_prompt(
            witness=sample_witness,
            trust=50,

            conversation_history=[
                {"question": "Hello", "response": "Hello there."},
            ],
            player_input="Tell me more.",
            pressure=100,
        )

        assert "PERSONALITY" in prompt
        assert "BACKGROUND" in prompt
        assert "KNOWLEDGE" in prompt
        assert "SECRETS" in prompt
        assert "CURRENT STATE" in prompt
        assert "Trust:" in prompt
        assert "Pressure:" in prompt
        assert "CONVERSATION" in prompt
        assert "Player:" in prompt
