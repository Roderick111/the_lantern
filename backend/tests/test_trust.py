"""Tests for trust mechanics module."""

from src.utils.trust import (
    NATURAL_WARMING_MAX,
    NATURAL_WARMING_MIN,
    check_secret_triggers,
    clamp_trust,
    detect_evidence_in_message,
    extract_trust_delta,
    get_available_secrets,
    natural_warming,
    parse_trigger_condition,
    should_lie,
    strip_trust_tag,
)


class TestNaturalWarming:
    """Tests for natural_warming fallback."""

    def test_warming_in_range(self) -> None:
        """Natural warming returns value in [0, 5]."""
        for _ in range(50):
            val = natural_warming()
            assert NATURAL_WARMING_MIN <= val <= NATURAL_WARMING_MAX


class TestClampTrust:
    """Tests for clamp_trust function."""

    def test_clamp_within_range(self) -> None:
        """Values within range unchanged."""
        assert clamp_trust(50) == 50
        assert clamp_trust(0) == 0
        assert clamp_trust(100) == 100

    def test_clamp_below_minimum(self) -> None:
        """Negative values clamped to 0."""
        assert clamp_trust(-10) == 0
        assert clamp_trust(-100) == 0

    def test_clamp_above_maximum(self) -> None:
        """Values above 100 clamped to 100."""
        assert clamp_trust(110) == 100
        assert clamp_trust(200) == 100


class TestParseTriggerCondition:
    """Tests for parse_trigger_condition function."""

    def test_parse_trust_greater_than(self) -> None:
        """Parse trust>N condition."""
        conditions = parse_trigger_condition("trust>70")
        assert len(conditions) == 1
        assert conditions[0]["type"] == "and_group"
        assert conditions[0]["conditions"][0]["type"] == "trust"
        assert conditions[0]["conditions"][0]["operator"] == ">"
        assert conditions[0]["conditions"][0]["value"] == 70

    def test_parse_trust_less_than(self) -> None:
        """Parse trust<N condition."""
        conditions = parse_trigger_condition("trust<30")
        assert len(conditions) == 1
        assert conditions[0]["conditions"][0]["operator"] == "<"
        assert conditions[0]["conditions"][0]["value"] == 30

    def test_parse_evidence_condition(self) -> None:
        """Parse evidence:X condition."""
        conditions = parse_trigger_condition("evidence:frost_pattern")
        assert len(conditions) == 1
        assert conditions[0]["conditions"][0]["type"] == "evidence"
        assert conditions[0]["conditions"][0]["value"] == "frost_pattern"

    def test_parse_or_condition(self) -> None:
        """Parse OR conditions."""
        conditions = parse_trigger_condition("evidence:frost_pattern OR trust>70")
        assert len(conditions) == 2  # Two OR groups

    def test_parse_and_condition(self) -> None:
        """Parse AND conditions."""
        conditions = parse_trigger_condition("evidence:frost_pattern AND trust>60")
        assert len(conditions) == 1  # One AND group
        assert len(conditions[0]["conditions"]) == 2  # Two conditions in group


class TestCheckSecretTriggers:
    """Tests for check_secret_triggers function."""

    def test_trust_threshold_met(self) -> None:
        """Secret revealed when trust threshold met."""
        secret = {"id": "test", "trigger": "trust>70", "text": "Secret"}

        assert check_secret_triggers(secret, 80, []) is True
        assert check_secret_triggers(secret, 70, []) is False  # Not greater than
        assert check_secret_triggers(secret, 50, []) is False

    def test_evidence_trigger_met(self) -> None:
        """Secret revealed when evidence discovered."""
        secret = {"id": "test", "trigger": "evidence:frost_pattern", "text": "Secret"}

        assert check_secret_triggers(secret, 50, ["frost_pattern"]) is True
        assert check_secret_triggers(secret, 50, ["hidden_note"]) is False
        assert check_secret_triggers(secret, 50, []) is False

    def test_or_trigger_any_met(self) -> None:
        """Secret revealed if any OR condition met."""
        secret = {"id": "test", "trigger": "evidence:frost_pattern OR trust>70", "text": "Secret"}

        # Evidence alone
        assert check_secret_triggers(secret, 50, ["frost_pattern"]) is True
        # Trust alone
        assert check_secret_triggers(secret, 80, []) is True
        # Neither
        assert check_secret_triggers(secret, 50, []) is False

    def test_and_trigger_all_required(self) -> None:
        """Secret revealed only if ALL AND conditions met."""
        secret = {"id": "test", "trigger": "evidence:frost_pattern AND trust>60", "text": "Secret"}

        # Both met
        assert check_secret_triggers(secret, 70, ["frost_pattern"]) is True
        # Only evidence
        assert check_secret_triggers(secret, 50, ["frost_pattern"]) is False
        # Only trust
        assert check_secret_triggers(secret, 70, []) is False
        # Neither
        assert check_secret_triggers(secret, 50, []) is False


class TestGetAvailableSecrets:
    """Tests for get_available_secrets function."""

    def test_returns_triggered_secrets(self) -> None:
        """Returns secrets whose triggers are met."""
        witness = {
            "secrets": [
                {"id": "secret1", "trigger": "trust>70", "text": "Text 1"},
                {"id": "secret2", "trigger": "evidence:hidden_note", "text": "Text 2"},
                {"id": "secret3", "trigger": "trust>90", "text": "Text 3"},
            ]
        }

        available = get_available_secrets(witness, 80, ["hidden_note"])

        assert len(available) == 2
        secret_ids = [s["id"] for s in available]
        assert "secret1" in secret_ids  # trust>70 met (80)
        assert "secret2" in secret_ids  # evidence:hidden_note met
        assert "secret3" not in secret_ids  # trust>90 not met (80)

    def test_no_secrets_available(self) -> None:
        """Returns empty list if no triggers met."""
        witness = {
            "secrets": [
                {"id": "secret1", "trigger": "trust>90", "text": "Text 1"},
            ]
        }

        available = get_available_secrets(witness, 50, [])
        assert available == []


class TestShouldLie:
    """Tests for should_lie function."""

    def test_lie_when_trust_low_and_topic_matches(self) -> None:
        """Witness lies when trust is low and question matches topic."""
        witness = {
            "lies": [
                {
                    "condition": "trust<30",
                    "topics": ["where were you", "that night"],
                    "response": "I was in the common room.",
                }
            ]
        }

        lie = should_lie(witness, "Where were you that night?", 20)
        assert lie is not None
        assert lie["response"] == "I was in the common room."

    def test_no_lie_when_trust_high(self) -> None:
        """No lie when trust is above threshold."""
        witness = {
            "lies": [
                {
                    "condition": "trust<30",
                    "topics": ["where were you"],
                    "response": "I was in the common room.",
                }
            ]
        }

        lie = should_lie(witness, "Where were you?", 50)
        assert lie is None

    def test_no_lie_when_topic_not_matched(self) -> None:
        """No lie when question doesn't match any topic."""
        witness = {
            "lies": [
                {
                    "condition": "trust<30",
                    "topics": ["cassian", "thorne"],
                    "response": "I didn't see Cassian.",
                }
            ]
        }

        lie = should_lie(witness, "What's your favorite book?", 20)
        assert lie is None


class TestDetectEvidenceInMessage:
    """Tests for detect_evidence_in_message function."""

    # Shared test fixture: case data with diverse evidence
    CASE_DATA = {
        "locations": {
            "library": {
                "hidden_evidence": [
                    {"id": "hidden_note", "name": "Crumpled Apology Note"},
                    {"id": "focus_signature", "name": "Professor Vane's Focus Signature"},
                    {"id": "frost_pattern", "name": "Frost Pattern"},
                ]
            },
            "kitchen": {
                "hidden_evidence": [
                    {"id": "kitchen_log", "name": "Kitchen Duty Log"},
                    {"id": "wisp_frostbite", "name": "Wisp's Frostbite Marks"},
                ]
            },
        }
    }
    ALL_IDS = ["hidden_note", "focus_signature", "frost_pattern", "kitchen_log", "wisp_frostbite"]

    # --- Explicit verb patterns (backward compat) ---

    def test_show_verb_with_name(self) -> None:
        """'show' verb + evidence name tokens triggers match."""
        result = detect_evidence_in_message("show the apology note", self.ALL_IDS, self.CASE_DATA)
        assert result == "hidden_note"

    def test_present_verb_with_id(self) -> None:
        """'present' verb + exact ID triggers match."""
        result = detect_evidence_in_message("present frost_pattern", self.ALL_IDS, self.CASE_DATA)
        assert result == "frost_pattern"

    # --- Natural language phrasings ---

    def test_what_about_phrase(self) -> None:
        """'What about X?' matches evidence."""
        result = detect_evidence_in_message(
            "What about the apology note?", self.ALL_IDS, self.CASE_DATA,
        )
        assert result == "hidden_note"

    def test_what_do_you_know(self) -> None:
        """'What do you know about X?' matches."""
        result = detect_evidence_in_message(
            "What do you know about Professor Vane's focus signature?", self.ALL_IDS, self.CASE_DATA,
        )
        assert result == "focus_signature"

    def test_does_this_mean_anything(self) -> None:
        """'Does X mean anything to you?' matches."""
        result = detect_evidence_in_message(
            "Does the frost pattern mean anything to you?", self.ALL_IDS, self.CASE_DATA,
        )
        assert result == "frost_pattern"

    def test_have_you_seen(self) -> None:
        """'Have you seen X?' matches."""
        result = detect_evidence_in_message(
            "Have you seen the kitchen duty log?", self.ALL_IDS, self.CASE_DATA,
        )
        assert result == "kitchen_log"

    def test_i_found_evidence(self) -> None:
        """'I found X' matches."""
        result = detect_evidence_in_message(
            "I found Wisp's frostbite marks", self.ALL_IDS, self.CASE_DATA,
        )
        assert result == "wisp_frostbite"

    def test_id_with_spaces(self) -> None:
        """Evidence ID with underscores matched as spaces."""
        result = detect_evidence_in_message(
            "Tell me about hidden note", self.ALL_IDS, self.CASE_DATA,
        )
        assert result == "hidden_note"

    def test_exact_id_mention(self) -> None:
        """Exact evidence ID in message triggers match."""
        result = detect_evidence_in_message(
            "What's focus_signature about?", self.ALL_IDS, self.CASE_DATA,
        )
        assert result == "focus_signature"

    # --- No false positives ---

    def test_no_match_unrelated_question(self) -> None:
        """Unrelated questions don't trigger."""
        result = detect_evidence_in_message("Where were you?", self.ALL_IDS, self.CASE_DATA)
        assert result is None

    def test_no_match_generic_words(self) -> None:
        """Generic words don't false-positive."""
        result = detect_evidence_in_message("Tell me more about that night", self.ALL_IDS, self.CASE_DATA)
        assert result is None

    def test_no_match_empty_discovered(self) -> None:
        """No match when no evidence discovered."""
        result = detect_evidence_in_message("show the hidden_note", [], self.CASE_DATA)
        assert result is None

    def test_no_match_undiscovered_evidence(self) -> None:
        """Only matches discovered evidence."""
        result = detect_evidence_in_message(
            "What about the kitchen duty log?", ["hidden_note"], self.CASE_DATA,
        )
        assert result is None

    # --- Case insensitivity ---

    def test_case_insensitive(self) -> None:
        """Detection is case-insensitive."""
        result = detect_evidence_in_message(
            "WHAT ABOUT THE FROST PATTERN?", self.ALL_IDS, self.CASE_DATA,
        )
        assert result == "frost_pattern"

    # --- Single-word evidence names need verb or exact match ---

    def test_single_word_with_verb(self) -> None:
        """Single-word name matches with presentation verb."""
        case = {"locations": {"a": {"hidden_evidence": [
            {"id": "potion", "name": "Potion"},
        ]}}}
        result = detect_evidence_in_message("show the potion", ["potion"], case)
        assert result == "potion"

    def test_single_word_exact_token(self) -> None:
        """Single-word name matches when token is exact."""
        case = {"locations": {"a": {"hidden_evidence": [
            {"id": "potion", "name": "Potion"},
        ]}}}
        result = detect_evidence_in_message("what about the potion?", ["potion"], case)
        assert result == "potion"


class TestExtractTrustDelta:
    """Tests for extract_trust_delta function."""

    def test_extract_positive(self) -> None:
        """Extract positive trust delta."""
        assert extract_trust_delta("Some response.\n[TRUST_DELTA: 5]") == 5

    def test_extract_negative(self) -> None:
        """Extract negative trust delta."""
        assert extract_trust_delta("Angry response.\n[TRUST_DELTA: -10]") == -10

    def test_extract_zero(self) -> None:
        """Extract zero trust delta."""
        assert extract_trust_delta("Neutral.\n[TRUST_DELTA: 0]") == 0

    def test_extract_with_plus_sign(self) -> None:
        """Extract with explicit plus sign."""
        assert extract_trust_delta("Nice.\n[TRUST_DELTA: +8]") == 8

    def test_clamp_too_high(self) -> None:
        """Clamp values above max (10)."""
        assert extract_trust_delta("[TRUST_DELTA: 50]") == 10

    def test_clamp_too_low(self) -> None:
        """Clamp values below min (-15)."""
        assert extract_trust_delta("[TRUST_DELTA: -30]") == -15

    def test_no_tag_returns_none(self) -> None:
        """Return None when no tag present."""
        assert extract_trust_delta("Just a normal response.") is None

    def test_case_insensitive(self) -> None:
        """Tag matching is case-insensitive."""
        assert extract_trust_delta("[trust_delta: 3]") == 3

    def test_extra_spaces(self) -> None:
        """Handle extra spaces in tag."""
        assert extract_trust_delta("[TRUST_DELTA:  -5 ]") == -5

    def test_tag_in_middle_of_text(self) -> None:
        """Extract tag even if not at end."""
        assert extract_trust_delta("Response here.\n[TRUST_DELTA: 7]\nExtra text") == 7

    def test_abbreviated_ta(self) -> None:
        """Extract from LLM-abbreviated TA: tag."""
        assert extract_trust_delta("Some response.\nTA: -12]") == -12

    def test_abbreviated_td(self) -> None:
        """Extract from LLM-abbreviated TD: tag."""
        assert extract_trust_delta("Response.\n[TD: 5]") == 5

    def test_abbreviated_with_bracket(self) -> None:
        """Extract abbreviated tag with opening bracket."""
        assert extract_trust_delta("Response.\n[TA: -2]") == -2


class TestStripTrustTag:
    """Tests for strip_trust_tag function."""

    def test_strip_complete_tag(self) -> None:
        """Strip complete trust delta tag."""
        result = strip_trust_tag("Some response.\n[TRUST_DELTA: 5]")
        assert result == "Some response."

    def test_strip_negative_tag(self) -> None:
        """Strip negative trust delta tag."""
        result = strip_trust_tag("Angry response.\n[TRUST_DELTA: -10]")
        assert result == "Angry response."

    def test_no_tag_unchanged(self) -> None:
        """Text without tag is unchanged."""
        result = strip_trust_tag("Just a response.")
        assert result == "Just a response."

    def test_strip_partial_tag(self) -> None:
        """Strip partial tag (during streaming)."""
        result = strip_trust_tag("Response so far... [TRUST_DELT")
        assert result == "Response so far..."

    def test_strip_partial_tag_with_colon(self) -> None:
        """Strip partial tag with colon."""
        result = strip_trust_tag("Response... [TRUST_DELTA:")
        assert result == "Response..."

    def test_preserve_response_content(self) -> None:
        """Don't strip non-tag content."""
        result = strip_trust_tag("I trust you with this information.")
        assert result == "I trust you with this information."

    def test_strip_abbreviated_ta(self) -> None:
        """Strip LLM-abbreviated TA: tag."""
        result = strip_trust_tag("How dare you speak to me like that.\nTA: -12]")
        assert result == "How dare you speak to me like that."

    def test_strip_abbreviated_td(self) -> None:
        """Strip LLM-abbreviated TD: tag."""
        result = strip_trust_tag("Response here.\n[TD: 5]")
        assert result == "Response here."
