"""Tests for spell LLM context builder."""

import pytest

from src.context.spell_llm import (
    _build_unknown_spell_prompt,
    _normalize_spell_name,
    build_spell_effect_prompt,
    is_spell_input,
    parse_spell_from_input,
)


class TestBuildSpellEffectPrompt:
    """Tests for build_spell_effect_prompt function."""

    @pytest.fixture
    def location_context(self) -> dict:
        """Sample location context."""
        return {
            "description": "The dusty library stretches before you.",
            "spell_contexts": {
                "special_interactions": {
                    "unveil": {
                        "targets": ["desk", "shelves", "window"],
                        "reveals_evidence": ["hidden_note"],
                    },
                    "echo_reading": {
                        "targets": ["focus", "victim_focus"],
                        "reveals_evidence": ["focus_signature"],
                    },
                },
            },
        }

    def test_includes_spell_name(self, location_context: dict) -> None:
        """Prompt includes spell name."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
        )

        assert "Unveil" in prompt
        assert "== RITE ==" in prompt

    def test_includes_target(self, location_context: dict) -> None:
        """Prompt includes target."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
        )

        assert "desk" in prompt.lower()

    def test_includes_location_description(self, location_context: dict) -> None:
        """Prompt includes location description."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
        )

        assert "dusty library" in prompt.lower()

    def test_includes_valid_targets(self, location_context: dict) -> None:
        """Prompt includes valid targets for spell."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
        )

        assert "VALID TARGETS" in prompt
        assert "desk" in prompt
        assert "shelves" in prompt

    def test_includes_revealable_evidence(self, location_context: dict) -> None:
        """Prompt includes evidence that can be revealed."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
            player_context={"discovered_evidence": []},
        )

        assert "hidden_note" in prompt

    def test_includes_exact_candidate_evidence_contract_data(self, location_context: dict) -> None:
        """Dynamic prompt includes candidate ID and exact required tag."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
            player_context={"discovered_evidence": []},
            spell_outcome="SUCCESS",
        )

        assert "ID: hidden_note" in prompt
        assert "Required tag: [EVIDENCE_hidden_note]" in prompt
        assert "Can reveal:" not in prompt

    def test_contains_dynamic_data_but_no_behavior_or_length_policy(
        self, location_context: dict
    ) -> None:
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
            player_context={"discovered_evidence": []},
            spell_outcome="SUCCESS",
        )

        assert "== RITE ==" in prompt
        assert "== CANDIDATE EVIDENCE ==" in prompt
        assert "== RULES ==" not in prompt
        assert "LENGTH:" not in prompt
        assert "sentences" not in prompt

    def test_excludes_discovered_evidence(self, location_context: dict) -> None:
        """Prompt excludes already discovered evidence."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
            player_context={"discovered_evidence": ["hidden_note"]},
        )

        assert "No new evidence" in prompt or "ID: hidden_note" not in prompt

    def test_unknown_spell_handled(self) -> None:
        """Unknown spell returns appropriate prompt."""
        prompt = build_spell_effect_prompt(
            spell_name="expelliarmus",
            target=None,
            location_context={},
        )

        assert "not recognized" in prompt.lower() or "unknown" in prompt.lower()

    def test_no_target_handled(self, location_context: dict) -> None:
        """No target handled gracefully."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target=None,
            location_context=location_context,
        )

        assert "general area" in prompt.lower()


class TestParseSpellFromInput:
    """Tests for parse_spell_from_input function."""

    def test_cast_spell_simple(self) -> None:
        """Parse 'cast unveil'."""
        spell_id, target = parse_spell_from_input("cast unveil")

        assert spell_id == "unveil"
        assert target is None

    def test_cast_spell_with_target(self) -> None:
        """Parse 'cast unveil on desk'."""
        spell_id, target = parse_spell_from_input("cast unveil on desk")

        assert spell_id == "unveil"
        assert target == "desk"

    def test_casting_spell_simple(self) -> None:
        """Parse "I'm casting Raise the Lamp"."""
        spell_id, target = parse_spell_from_input("I'm casting Raise the Lamp")

        assert spell_id == "raise_the_lamp"
        assert target is None

    def test_casting_spell_with_target(self) -> None:
        """Parse "I'm casting Echo Reading on the focus"."""
        spell_id, target = parse_spell_from_input("I'm casting Echo Reading on the focus")

        assert spell_id == "echo_reading"
        assert target == "the focus"

    def test_spell_name_with_target(self) -> None:
        """Parse 'unveil on shelves'."""
        spell_id, target = parse_spell_from_input("unveil on shelves")

        assert spell_id == "unveil"
        assert target == "shelves"

    def test_just_spell_name(self) -> None:
        """Parse just spell name."""
        spell_id, target = parse_spell_from_input("raise_the_lamp")

        assert spell_id == "raise_the_lamp"
        assert target is None

    def test_unknown_spell(self) -> None:
        """Unknown spell returns None."""
        spell_id, target = parse_spell_from_input("cast expelliarmus")

        assert spell_id is None
        assert target is None

    def test_no_spell(self) -> None:
        """No spell in input returns None."""
        spell_id, target = parse_spell_from_input("examine the desk")

        assert spell_id is None
        assert target is None

    def test_case_insensitive(self) -> None:
        """Spell parsing is case insensitive."""
        spell_id1, _ = parse_spell_from_input("cast Unveil")
        spell_id2, _ = parse_spell_from_input("cast Unveil")
        spell_id3, _ = parse_spell_from_input("cast unveil")

        assert spell_id1 == spell_id2 == spell_id3 == "unveil"

    def test_multi_word_spell(self) -> None:
        """Parse multi-word spell name."""
        spell_id, target = parse_spell_from_input("cast echo reading on focus")

        assert spell_id == "echo_reading"
        assert target == "focus"

    def test_mnemonic_delving(self) -> None:
        """Parse mnemonic_delving spell."""
        spell_id, target = parse_spell_from_input("cast mnemonic_delving on elena")

        assert spell_id == "mnemonic_delving"
        assert target == "elena"


class TestNormalizeSpellName:
    """Tests for _normalize_spell_name function."""

    def test_direct_match(self) -> None:
        """Direct spell ID match."""
        assert _normalize_spell_name("unveil") == "unveil"

    def test_match_by_name(self) -> None:
        """Match by display name."""
        assert _normalize_spell_name("Unveil") == "unveil"

    def test_multi_word_with_space(self) -> None:
        """Multi-word spell with space."""
        assert _normalize_spell_name("echo reading") == "echo_reading"

    def test_partial_match(self) -> None:
        """Partial name match."""
        assert _normalize_spell_name("echo") == "echo_reading"

    def test_unknown_returns_none(self) -> None:
        """Unknown spell returns None."""
        assert _normalize_spell_name("expelliarmus") is None


class TestIsSpellInput:
    """Tests for is_spell_input function."""

    def test_cast_spell_is_spell(self) -> None:
        """'cast unveil' is spell input."""
        assert is_spell_input("cast unveil") is True

    def test_casting_is_spell(self) -> None:
        """'I'm casting Raise the Lamp' is spell input."""
        assert is_spell_input("I'm casting Raise the Lamp") is True

    def test_examine_not_spell(self) -> None:
        """'examine desk' is not spell input."""
        assert is_spell_input("examine the desk") is False

    def test_look_around_not_spell(self) -> None:
        """'look around' is not spell input."""
        assert is_spell_input("look around") is False

    def test_unknown_spell_not_spell(self) -> None:
        """Unknown spell not recognized as spell input."""
        assert is_spell_input("cast expelliarmus") is False


class TestBuildUnknownSpellPrompt:
    """Tests for _build_unknown_spell_prompt function."""

    def test_includes_spell_name(self) -> None:
        """Unknown spell prompt includes attempted spell name."""
        prompt = _build_unknown_spell_prompt("expelliarmus")

        assert "expelliarmus" in prompt

    def test_indicates_unknown(self) -> None:
        """Unknown spell prompt indicates spell not recognized."""
        prompt = _build_unknown_spell_prompt("fake_spell")

        assert "not recognized" in prompt.lower() or "unknown" in prompt.lower()


# =============================================================================
# Phase 4.6.2: Single-Stage Fuzzy + Semantic Detection Tests
# =============================================================================


class TestDetectSpellWithFuzzy:
    """Tests for detect_spell_with_fuzzy function (Phase 4.6.2)."""

    def test_exact_spell_name(self) -> None:
        """Exact spell name detection."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        spell_id, target = detect_spell_with_fuzzy("use mnemonic_delving")
        assert spell_id == "mnemonic_delving"

    def test_spell_name_with_target(self) -> None:
        """Spell detection with target extraction."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        spell_id, target = detect_spell_with_fuzzy("cast unveil on desk")
        assert spell_id == "unveil"
        assert target == "desk"

    def test_fuzzy_match_typo(self) -> None:
        """Fuzzy matching handles typos."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        # Common typo: legulemancy
        spell_id, target = detect_spell_with_fuzzy("legulemancy on her")
        assert spell_id == "mnemonic_delving"
        assert target == "her"

    def test_fuzzy_match_mnemonic_delving_typo(self) -> None:
        """Fuzzy matching detects mnemonic_delving with typo (user requirement: fuzzy only)."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        spell_id, target = detect_spell_with_fuzzy("I cast legulemancy on elena")
        assert spell_id == "mnemonic_delving"
        assert target == "elena"

    def test_no_false_positive_conversational(self) -> None:
        """Conversational phrases don't trigger detection."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        spell_id, target = detect_spell_with_fuzzy("What's in your mind?")
        assert spell_id is None
        assert target is None

    def test_no_false_positive_simple_question(self) -> None:
        """Simple questions don't trigger detection."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        spell_id, target = detect_spell_with_fuzzy("Can you remember anything?")
        assert spell_id is None
        assert target is None

    def test_natural_description_without_formula_is_not_a_rite(self) -> None:
        """Natural objectives require an explicit formula or invocation verb."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        for text in (
            "show hidden marks on the note",
            "repair this glass",
            "what potion is this?",
        ):
            spell_id, target = detect_spell_with_fuzzy(text)
            assert spell_id is None
            assert target is None

    def test_all_7_spells_detected(self) -> None:
        """All 7 rites can be detected by name."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        spells = [
            ("cast unveil", "unveil"),
            ("raise_the_lamp", "raise_the_lamp"),
            ("homenum unveil", "sense_presence"),
            ("specialis unveil", "identify_substance"),
            ("echo reading", "echo_reading"),
            ("mend on vase", "mend"),
            ("mnemonic_delving", "mnemonic_delving"),
        ]

        for text, expected_id in spells:
            spell_id, _ = detect_spell_with_fuzzy(text)
            assert spell_id == expected_id, f"Failed for {text}"

    def test_english_formula_examples_detected(self) -> None:
        """Displayed English formulas are executable rites."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        examples = [
            ("Veil, dissolve over this desk.", "unveil"),
            ("Presence, answer beyond this wall.", "sense_presence"),
            ("Essence, speak in this vial.", "identify_substance"),
            ("Trace, gleam in the alcove.", "raise_the_lamp"),
            ("Echo, speak on Elena's focus.", "echo_reading"),
            ("Shards, unite.", "mend"),
            ("Memory, open on Elena's recollection of the archive.", "mnemonic_delving"),
        ]

        for text, expected_id in examples:
            spell_id, _ = detect_spell_with_fuzzy(text)
            assert spell_id == expected_id, f"Failed for {text}"

    def test_explicit_spell_wrapper_is_supported(self) -> None:
        """Explicit wrapper verbs may precede a displayed formula."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        spell_id, target = detect_spell_with_fuzzy(
            "I spell Veil, dissolve over this desk."
        )
        assert spell_id == "unveil"
        assert target == "this desk"

    def test_russian_formula_examples_detected(self) -> None:
        """Displayed Russian formulas are executable rites."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        examples = [
            ("Скрытое, явись на этом столе.", "unveil"),
            ("Присутствие, отзовись за этой стеной.", "sense_presence"),
            ("Суть, откройся в этом флаконе.", "identify_substance"),
            ("Свет, укажи след в нише.", "raise_the_lamp"),
            ("Отзвук чар, явись на фокусе Елены.", "echo_reading"),
            ("Разбитое стекло, сойдись.", "mend"),
            ("Чужая память, отворись на воспоминание Елены о библиотеке.", "mnemonic_delving"),
        ]

        for text, expected_id in examples:
            spell_id, _ = detect_spell_with_fuzzy(text)
            assert spell_id == expected_id, f"Failed for {text}"


class TestExtractTargetFromInput:
    """Tests for extract_target_from_input function (Phase 4.6.2)."""

    def test_on_target(self) -> None:
        """Extracts target after 'on'."""
        from src.context.spell_llm import extract_target_from_input

        target = extract_target_from_input("cast unveil on the desk")
        assert target == "the desk"

    def test_at_target(self) -> None:
        """Extracts target after 'at'."""
        from src.context.spell_llm import extract_target_from_input

        target = extract_target_from_input("cast raise_the_lamp at the corner")
        assert target == "the corner"

    def test_no_target(self) -> None:
        """Returns None if no target specified."""
        from src.context.spell_llm import extract_target_from_input

        target = extract_target_from_input("cast unveil")
        assert target is None

    def test_russian_inflected_target_is_canonicalized(self) -> None:
        """Russian target inflections map to case mechanics IDs."""
        from src.context.spell_llm import detect_spell_with_fuzzy

        spell_id, target = detect_spell_with_fuzzy("Скрытое, явись на столе")

        assert spell_id == "unveil"
        assert target == "desk"


class TestExtractIntentFromInput:
    """Tests for extract_intent_from_input function (Phase 4.6.2)."""

    def test_find_out_about(self) -> None:
        """Extracts intent from 'to find out about X'."""
        from src.context.spell_llm import extract_intent_from_input

        intent = extract_intent_from_input("read her mind to find out about cassian")
        assert intent == "cassian"

    def test_about_pattern(self) -> None:
        """Extracts intent from 'about X'."""
        from src.context.spell_llm import extract_intent_from_input

        intent = extract_intent_from_input("mnemonic_delving about the crime")
        assert intent == "the crime"

    def test_russian_memory_intent(self) -> None:
        """Russian memory-purpose wording is recognized for focused delving."""
        from src.context.spell_llm import extract_intent_from_input

        intent = extract_intent_from_input(
            "Чужая память, отворись на воспоминание Елены о библиотеке"
        )
        assert intent == "воспоминание Елены о библиотеке"

    def test_no_intent(self) -> None:
        """Returns None if no intent specified."""
        from src.context.spell_llm import extract_intent_from_input

        intent = extract_intent_from_input("use mnemonic_delving on her")
        assert intent is None


class TestDetectFocusedMnemonicDelving:
    """Tests for detect_focused_mnemonic_delving function (Phase 4.6.2)."""

    def test_focused_with_intent(self) -> None:
        """Focused Mnemonic Delving detected with search intent."""
        from src.context.spell_llm import detect_focused_mnemonic_delving

        is_focused, target = detect_focused_mnemonic_delving("read her mind to find out about cassian")
        assert is_focused is True
        assert target == "cassian"

    def test_unfocused_no_intent(self) -> None:
        """Unfocused Mnemonic Delving detected without search intent."""
        from src.context.spell_llm import detect_focused_mnemonic_delving

        is_focused, target = detect_focused_mnemonic_delving("use mnemonic_delving on elena")
        assert is_focused is False
        assert target is None


class TestBuildMnemonicDelvingNarrationPrompt:
    """Tests for build_mnemonic_delving_narration_prompt function (Phase 4.8)."""

    def test_success_with_intent_template(self) -> None:
        """Success template includes search intent and witness name."""
        from src.context.spell_llm import build_mnemonic_delving_narration_prompt

        prompt = build_mnemonic_delving_narration_prompt(
            outcome="success",
            detected=False,
            witness_name="Elena",
            search_intent="Cassian",
        )

        assert "Elena" in prompt
        assert "Cassian" in prompt
        assert "success" in prompt.lower()

    def test_failure_undetected_template(self) -> None:
        """Failure undetected template included."""
        from src.context.spell_llm import build_mnemonic_delving_narration_prompt

        prompt = build_mnemonic_delving_narration_prompt(
            outcome="failure",
            detected=False,
            witness_name="Rowan",
        )

        assert "Rowan" in prompt
        assert "fail" in prompt.lower()

    def test_failure_detected_template(self) -> None:
        """Failure detected template shows detection status."""
        from src.context.spell_llm import build_mnemonic_delving_narration_prompt

        prompt = build_mnemonic_delving_narration_prompt(
            outcome="failure",
            detected=True,
            witness_name="Elena",
        )

        assert "Elena" in prompt
        assert "detect" in prompt.lower()


# =============================================================================
# Phase 4.7: Spell Success Calculation Tests
# =============================================================================


class TestCalculateSpecificityBonus:
    """Tests for calculate_specificity_bonus function (Phase 4.7)."""

    def test_no_bonus(self) -> None:
        """Plain spell name has no bonus."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("Unveil")
        assert bonus == 0

    def test_target_bonus_on(self) -> None:
        """Target with 'on X' gives +20%."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("Unveil on desk")
        assert bonus == 20

    def test_target_bonus_at(self) -> None:
        """Target with 'at X' gives +20%."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("Raise the Lamp at the corner")
        assert bonus == 20

    def test_target_bonus_toward(self) -> None:
        """Target with 'toward X' gives +20%."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("cast unveil toward window")
        assert bonus == 20

    def test_target_bonus_against(self) -> None:
        """Target with 'against X' gives +20%."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("specialis unveil against substance")
        assert bonus == 20

    def test_intent_bonus_to_find(self) -> None:
        """Intent with 'to find' gives +10%."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("Unveil to find hidden objects")
        assert bonus == 10

    def test_intent_bonus_to_reveal(self) -> None:
        """Intent with 'to reveal' gives +10%."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("Unveil to reveal secrets")
        assert bonus == 10

    def test_intent_bonus_to_show(self) -> None:
        """Intent with 'to show' gives +10%."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("Raise the Lamp to show the way")
        assert bonus == 10

    def test_intent_bonus_to_uncover(self) -> None:
        """Intent with 'to uncover' gives +10%."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("Unveil to uncover evidence")
        assert bonus == 10

    def test_intent_bonus_to_detect(self) -> None:
        """Intent with 'to detect' gives +10%."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("Sense Presence to detect people")
        assert bonus == 10

    def test_both_target_and_intent(self) -> None:
        """Both target and intent gives +30%."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus = calculate_specificity_bonus("Unveil on desk to find letters")
        assert bonus == 30

    def test_case_insensitive(self) -> None:
        """Bonus detection is case insensitive."""
        from src.context.spell_llm import calculate_specificity_bonus

        bonus1 = calculate_specificity_bonus("unveil ON desk TO FIND clues")
        bonus2 = calculate_specificity_bonus("Unveil on desk to find clues")
        assert bonus1 == bonus2 == 30

    def test_russian_formula_target_bonus(self) -> None:
        """Russian formula targets receive the same specificity bonus as English."""
        from src.context.spell_llm import calculate_specificity_bonus

        assert calculate_specificity_bonus("Суть, откройся в этом флаконе") == 20

    def test_intent_phrases_cover_all_setting_languages(self) -> None:
        """Each selectable game language has a recognized intent phrase."""
        from src.context.spell_llm import calculate_specificity_bonus

        inputs = [
            "Unveil to analyze the desk",
            "Суть, откройся чтобы понять узор",
            "Essence, speak pour analyser la fenêtre",
            "Essence, speak para analizar la ventana",
            "Essence, speak um zu analysieren das Fenster",
            "Essence, speak para analisar a janela",
            "Essence, speak 为了分析窗户",
            "Essence, speak 窓を分析するため",
            "Essence, speak 창문을 분석하기 위해",
            "Essence, speak per analizzare la finestra",
        ]

        assert all(calculate_specificity_bonus(text) >= 10 for text in inputs)


class TestCalculateSpellSuccess:
    """Tests for calculate_spell_success function (Phase 4.7)."""

    def test_first_attempt_base_rate(self) -> None:
        """First attempt uses 70% base rate."""
        from unittest.mock import patch

        from src.context.spell_llm import calculate_spell_success

        # Roll 65 < 70% base rate = success
        with patch("src.context.spell_detection.random.random", return_value=0.65):
            result = calculate_spell_success("unveil", "Unveil", 0, "library")
            assert result is True

        # Roll 75 > 70% base rate = failure
        with patch("src.context.spell_detection.random.random", return_value=0.75):
            result = calculate_spell_success("unveil", "Unveil", 0, "library")
            assert result is False

    def test_specificity_bonus_applied(self) -> None:
        """Specificity bonus increases success rate."""
        from unittest.mock import patch

        from src.context.spell_llm import calculate_spell_success

        # Roll 85 - with target +20% and intent +10%, ceiling keeps this at 90%.
        with patch("src.context.spell_detection.random.random", return_value=0.85):
            result = calculate_spell_success(
                "unveil", "Unveil on desk to find clues", 0, "library"
            )
            assert result is True

    def test_decline_per_attempt(self) -> None:
        """Each attempt reduces success rate by 10%."""
        from unittest.mock import patch

        from src.context.spell_llm import calculate_spell_success

        # Roll 65 - 1st attempt (70%) succeeds, 2nd attempt (60%) fails
        with patch("src.context.spell_detection.random.random", return_value=0.65):
            result1 = calculate_spell_success("unveil", "Unveil", 0, "library")
            result2 = calculate_spell_success("unveil", "Unveil", 1, "library")
            assert result1 is True  # 70% base > 65% roll
            assert result2 is False  # 60% (70-10) < 65% roll

    def test_floor_at_30_percent(self) -> None:
        """Success rate never goes below 30%."""
        from unittest.mock import patch

        from src.context.spell_llm import calculate_spell_success

        # 7th attempt: 70 - 60 = 30% (floor)
        # Roll 25 < 30% = success
        with patch("src.context.spell_detection.random.random", return_value=0.05):
            result = calculate_spell_success("unveil", "Unveil", 6, "library")
            assert result is True

        # Roll 35 > 30% = failure
        with patch("src.context.spell_detection.random.random", return_value=0.35):
            result = calculate_spell_success("unveil", "Unveil", 6, "library")
            assert result is False

    def test_floor_even_with_many_attempts(self) -> None:
        """Floor holds even with many more attempts."""
        from unittest.mock import patch

        from src.context.spell_llm import calculate_spell_success

        # 10th attempt would be 70 - 90 = -20%, but floor keeps it at 30%
        with patch("src.context.spell_detection.random.random", return_value=0.05):
            result = calculate_spell_success("unveil", "Unveil", 9, "library")
            assert result is True  # 30% floor > 5% roll

    def test_second_attempt_rate(self) -> None:
        """2nd attempt has 60% base (70 - 10)."""
        from unittest.mock import patch

        from src.context.spell_llm import calculate_spell_success

        with patch("src.context.spell_detection.random.random", return_value=0.55):
            result = calculate_spell_success("unveil", "Unveil", 1, "library")
            assert result is True  # 60% > 55%

        with patch("src.context.spell_detection.random.random", return_value=0.65):
            result = calculate_spell_success("unveil", "Unveil", 1, "library")
            assert result is False  # 60% < 65%

    def test_third_attempt_rate(self) -> None:
        """3rd attempt has 50% base (70 - 20)."""
        from unittest.mock import patch

        from src.context.spell_llm import calculate_spell_success

        with patch("src.context.spell_detection.random.random", return_value=0.45):
            result = calculate_spell_success("unveil", "Unveil", 2, "library")
            assert result is True  # 50% > 45%

        with patch("src.context.spell_detection.random.random", return_value=0.55):
            result = calculate_spell_success("unveil", "Unveil", 2, "library")
            assert result is False  # 50% < 55%

    def test_all_safe_spells(self) -> None:
        """All 6 safe spells use same calculation."""
        from unittest.mock import patch

        from src.context.spell_llm import SAFE_INVESTIGATION_SPELLS, calculate_spell_success

        # All should succeed with roll 0.5 < 70% base
        with patch("src.context.spell_detection.random.random", return_value=0.5):
            for spell_id in SAFE_INVESTIGATION_SPELLS:
                result = calculate_spell_success(spell_id, f"cast {spell_id}", 0, "library")
                assert result is True, f"Failed for {spell_id}"

    def test_maximum_90_percent(self) -> None:
        """Maximum success rate is 90% (70 + 20 + 10, capped)."""
        from unittest.mock import patch

        from src.context.spell_llm import calculate_spell_success

        # Roll 89 < 90% = success
        with patch("src.context.spell_detection.random.random", return_value=0.89):
            result = calculate_spell_success(
                "unveil", "Unveil on desk to find letters", 0, "library"
            )
            assert result is True

        # Roll 91 > 90% = failure
        with patch("src.context.spell_detection.random.random", return_value=0.91):
            result = calculate_spell_success(
                "unveil", "Unveil on desk to find letters", 0, "library"
            )
            assert result is False

    def test_easy_mode_uses_50_to_100_bounds(self) -> None:
        """Easy assistance raises spell floor and ceiling only."""
        from unittest.mock import patch

        from src.context.spell_llm import calculate_spell_success

        with patch("src.context.spell_detection.random.random", return_value=0.49):
            assert calculate_spell_success("unveil", "Unveil", 9, "library", "easy") is True

        with patch("src.context.spell_detection.random.random", return_value=0.99):
            assert calculate_spell_success("unveil", "Unveil on desk to find letters", 0, "library", "easy") is True

        with patch("src.context.spell_detection.random.random", return_value=1.0):
            assert calculate_spell_success("unveil", "Unveil on desk to find letters", 0, "library", "easy") is False


class TestSafeInvestigationSpells:
    """Tests for SAFE_INVESTIGATION_SPELLS constant (Phase 4.7)."""

    def test_six_safe_spells(self) -> None:
        """Exactly 6 safe investigation rites defined."""
        from src.context.spell_llm import SAFE_INVESTIGATION_SPELLS

        assert len(SAFE_INVESTIGATION_SPELLS) == 6

    def test_excludes_mnemonic_delving(self) -> None:
        """Mnemonic Delving is not in safe spells (uses trust-based system)."""
        from src.context.spell_llm import SAFE_INVESTIGATION_SPELLS

        assert "mnemonic_delving" not in SAFE_INVESTIGATION_SPELLS

    def test_includes_expected_spells(self) -> None:
        """All expected investigation rites included."""
        from src.context.spell_llm import SAFE_INVESTIGATION_SPELLS

        expected = {
            "unveil",
            "raise_the_lamp",
            "sense_presence",
            "identify_substance",
            "echo_reading",
            "mend",
        }
        assert SAFE_INVESTIGATION_SPELLS == expected


class TestBuildSpellOutcomeSection:
    """Tests for _build_spell_outcome_section function (Phase 4.7)."""

    def test_success_outcome(self) -> None:
        """SUCCESS outcome generates appropriate section."""
        from src.context.spell_llm import _build_spell_outcome_section

        section = _build_spell_outcome_section("SUCCESS")
        assert section == "SUCCESS"

    def test_failure_outcome(self) -> None:
        """FAILURE outcome generates appropriate section."""
        from src.context.spell_llm import _build_spell_outcome_section

        section = _build_spell_outcome_section("FAILURE")
        assert section == "FAILURE"

    def test_none_outcome(self) -> None:
        """None outcome generates legacy flow section."""
        from src.context.spell_llm import _build_spell_outcome_section

        section = _build_spell_outcome_section(None)
        assert section == "NOT_CALCULATED"


class TestBuildSpellEffectPromptWithOutcome:
    """Tests for build_spell_effect_prompt with spell_outcome parameter (Phase 4.7)."""

    @pytest.fixture
    def location_context(self) -> dict:
        """Sample location context."""
        return {
            "description": "The dusty library stretches before you.",
            "spell_contexts": {
                "special_interactions": {
                    "unveil": {
                        "targets": ["desk", "shelves", "window"],
                        "reveals_evidence": ["hidden_note"],
                    },
                },
            },
        }

    def test_success_outcome_in_prompt(self, location_context: dict) -> None:
        """Spell prompt includes SUCCESS outcome."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
            spell_outcome="SUCCESS",
        )

        assert "Outcome: SUCCESS" in prompt

    def test_failure_outcome_in_prompt(self, location_context: dict) -> None:
        """Spell prompt includes FAILURE outcome."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
            spell_outcome="FAILURE",
        )

        assert "Outcome: FAILURE" in prompt

    def test_no_behavior_rules_in_dynamic_prompt(self, location_context: dict) -> None:
        """Behavior rules live only in shared system prompt."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
            spell_outcome="SUCCESS",
        )

        assert "NEVER mention mechanical terms" not in prompt
        assert "== RULES ==" not in prompt

    def test_backward_compatible_without_outcome(self, location_context: dict) -> None:
        """Prompt works without spell_outcome (backward compatible)."""
        prompt = build_spell_effect_prompt(
            spell_name="unveil",
            target="desk",
            location_context=location_context,
            # No spell_outcome parameter
        )

        assert "Outcome: NOT_CALCULATED" in prompt
