"""Locale overlay loading and mechanics-preservation tests."""

import re

import pytest

from src.case_store.loader import (
    _merge_locale_values,
    get_evidence_details_for_ids,
    list_cases_with_metadata,
    load_case,
    load_localized_case,
)


def test_russian_case_overlay_localizes_player_text() -> None:
    base = load_case("case_001")["case"]
    localized = load_localized_case("case_001", "ru")["case"]

    assert localized["title"] == "Опечатанная библиотека"
    assert localized["locations"]["library"]["name"] == "Опечатанная библиотека"
    assert localized["locations"]["library"]["description"] != base["locations"]["library"]["description"]
    for case_data in (base, localized):
        description = case_data["locations"]["library"]["description"]
        assert "\n\n" in description
        assert re.search(r"[^\n]\n[^\n]", description) is None
    assert localized["locations"]["library"]["surface_elements"][0] != base["locations"]["library"]["surface_elements"][0]
    assert localized["locations"]["library"]["not_present"][0]["response"] != base["locations"]["library"]["not_present"][0]["response"]
    assert localized["locations"]["library"]["hidden_evidence"][0]["id"] == base["locations"]["library"]["hidden_evidence"][0]["id"]
    assert localized["timeline"][0]["event"] != base["timeline"][0]["event"]
    assert localized["post_verdict"]["correct"]["confrontation"][0]["text"] != base["post_verdict"]["correct"]["confrontation"][0]["text"]


def test_russian_overlay_preserves_mechanics() -> None:
    base = load_case("case_001")["case"]
    localized = load_localized_case("case_001", "ru")["case"]

    assert localized["solution"]["culprit"] == base["solution"]["culprit"]
    assert localized["solution"]["key_evidence"] == base["solution"]["key_evidence"]
    assert localized["locations"]["library"]["spell_contexts"] == base["locations"]["library"]["spell_contexts"]
    assert [w["id"] for w in localized["witnesses"]] == [w["id"] for w in base["witnesses"]]


def test_evidence_index_does_not_cross_contaminate_locales() -> None:
    english = load_localized_case("case_001", "en")
    russian = load_localized_case("case_001", "ru")

    assert get_evidence_details_for_ids("case_001", english, ["stolen_nightshade"])[0]["name"] == "Stolen Nightshade"
    assert get_evidence_details_for_ids("case_001", russian, ["stolen_nightshade"])[0]["name"] == "Украденная белладонна"


def test_russian_case_list_hides_untranslated_cases() -> None:
    cases, errors = list_cases_with_metadata("ru")

    assert errors == []
    assert [case.id for case in cases] == ["case_001"]


def test_locale_overlay_rejects_mechanics_override() -> None:
    with pytest.raises(ValueError, match="mechanics"):
        _merge_locale_values(
            {"case": {"id": "case_001", "solution": {"culprit": "wisp"}}},
            {"case": {"id": "case_001", "solution": {"culprit": "elena"}}},
        )
