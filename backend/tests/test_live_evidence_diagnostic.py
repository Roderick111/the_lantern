"""Static contract tests for live evidence diagnostic matrix."""

import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest

import live_evidence_diagnostic as diagnostic
from src.config.language import SUPPORTED_LANGUAGES
from src.context import narrator, spell_prompts
from src.context.spell_detection import detect_spell_with_fuzzy


def test_live_matrix_has_two_calls_per_supported_language() -> None:
    assert len(diagnostic.SCENARIOS) == 20
    assert Counter(item["language"] for item in diagnostic.SCENARIOS) == {
        language: 2 for language in SUPPORTED_LANGUAGES
    }
    assert Counter(item["kind"] for item in diagnostic.SCENARIOS) == {
        "manual": 10,
        "magic": 10,
    }
    assert Counter(item["expected_evidence_id"] for item in diagnostic.SCENARIOS) == {
        "frost_pattern": 4,
        "hidden_note": 4,
        "singed_cloak_fiber": 4,
        "scuff_marks": 4,
        "dual_shimmer": 4,
    }


def test_reasoning_requirement_exists_only_in_diagnostic_script() -> None:
    marker = "== DIAGNOSTIC-ONLY REQUIREMENT =="
    assert marker in Path(diagnostic.__file__).read_text(encoding="utf-8")
    production_source = "".join(
        Path(module.__file__).read_text(encoding="utf-8") for module in (narrator, spell_prompts)
    )
    assert marker not in production_source

    diagnostic_system = diagnostic.build_diagnostic_system_prompt(
        "Keep this.\n- Never add meta-comments, notes, or OOC reasoning. "
        "Evidence control tags required by this prompt are the only exception.\nKeep that."
    )
    assert "Never add meta-comments" not in diagnostic_system
    assert "[REASONING:" in diagnostic_system
    assert "30 words or fewer" in diagnostic_system


def test_all_magic_probes_reach_expected_rite_and_target() -> None:
    for scenario in diagnostic.SCENARIOS:
        if scenario["kind"] != "magic":
            continue
        spell_id, target = detect_spell_with_fuzzy(scenario["player_input"])
        assert spell_id == scenario["expected_spell_id"], scenario["name"]
        assert target is not None, scenario["name"]
        assert scenario["target_keyword"] in target, scenario["name"]


def test_live_defaults_match_requested_generation_settings() -> None:
    with patch.object(sys, "argv", ["live_evidence_diagnostic.py"]):
        args = diagnostic.parse_args()
    assert args.max_tokens == 500
    assert args.temperature == 0.7


def test_reasoning_is_removed_before_evidence_parsing() -> None:
    response = (
        "[REASONING: Mentioning [EVIDENCE: wrong_id] only as metadata.]\n\n"
        "The note is hidden beneath the papers.\n\n"
        "[EVIDENCE: hidden_note]"
    )

    reasoning, narration = diagnostic.split_diagnostic_response(response)

    assert "wrong_id" in reasoning
    assert diagnostic.extract_evidence_from_response(narration) == ["hidden_note"]


def test_exact_evidence_set_rejects_unexpected_evidence() -> None:
    assert diagnostic.evidence_set_matches(["hidden_note"], ["hidden_note"])
    assert not diagnostic.evidence_set_matches(["hidden_note", "dropped_badge"], ["hidden_note"])


@pytest.mark.parametrize(
    ("language", "narration"),
    [
        ("en", "You examine the desk and find a folded note beneath the scattered papers."),
        ("ru", "Вы осматриваете стол и находите записку под разбросанными бумагами."),
        ("fr", "Vous examinez le bureau et trouvez une note sous les papiers dispersés."),
        ("es", "Examinas el escritorio y encuentras una nota debajo de los papeles."),
        ("de", "Du untersuchst den Tisch und findest eine Notiz unter den Papieren."),
        ("pt", "Você examina a mesa e encontra uma nota debaixo dos papéis espalhados."),
        ("zh", "你仔细检查书桌，在散落的文件下面发现了一张纸条。"),
        ("ja", "机の上を調べると、散らばった書類の下からメモが見つかる。"),
        ("ko", "책상을 자세히 조사하자 흩어진 서류 아래에서 쪽지를 발견한다."),
        ("it", "Esamini la scrivania e trovi una nota sotto i fogli sparsi."),
    ],
)
def test_narration_language_validation(language: str, narration: str) -> None:
    assert diagnostic.narration_matches_language(narration, language)
    assert not diagnostic.narration_matches_language(narration, "ru" if language != "ru" else "en")
