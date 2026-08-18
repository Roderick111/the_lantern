#!/usr/bin/env python3
"""Run live narrator evidence diagnostics against the sealed archive.

Run from ``backend/`` (20 scenarios; fallback can add provider attempts):

    uv run python live_evidence_diagnostic.py --force-spell-success

The script sends authored case context to the configured LLM. It writes one
JSON object per scenario to ``telemetry/live_evidence_diagnostic.jsonl``.
That local log contains prompts, raw responses, parser results, spell target
state, and stream timing. API keys are never logged.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.api.helpers import calculate_spell_outcome  # noqa: E402
from src.api.llm_client import get_client  # noqa: E402
from src.case_store.loader import load_localized_case  # noqa: E402
from src.config.language import SUPPORTED_LANGUAGES  # noqa: E402
from src.context.narrator import build_narrator_or_spell_prompt  # noqa: E402
from src.context.spell_detection import detect_spell_with_fuzzy  # noqa: E402
from src.state.player_state import PlayerState  # noqa: E402
from src.utils.evidence import (  # noqa: E402
    RITE_CONTROL_MARKER_PATTERN,
    extract_evidence_from_response,
    extract_rite_control_result,
    validate_rite_control_result,
)

DEFAULT_LOG_PATH = ROOT / "telemetry" / "live_evidence_diagnostic.jsonl"
BRACKET_TAG_RE = re.compile(r"\[([^:\]\r\n]+):\s*([^\]\r\n]+)\]")
EVIDENCE_ID_RE = re.compile(r"(?:^|[- ])ID:\s*([a-z0-9_]+)", re.IGNORECASE)

LATIN_LANGUAGE_MARKERS = {
    "en": {"you", "the", "and", "find", "finds", "under", "beneath", "with"},
    "fr": {"vous", "le", "les", "et", "une", "sous", "avec", "trouvez"},
    "es": {"el", "los", "y", "debajo", "con", "encuentras", "examinas"},
    "de": {"du", "den", "und", "eine", "unter", "mit", "findest"},
    "pt": {"você", "uma", "debaixo", "dos", "papéis", "encontra", "examina"},
    "it": {"la", "una", "sotto", "trovi", "esamini", "fogli", "scrivania"},
}

LANGUAGE_PROBES = {
    "en": {
        "evidence": "frost_pattern",
        "manual": "I closely examine the frost patterns on the window.",
        "magic": "Essence, speak on the window to analyze the frost pattern.",
        "spell": "identify_substance",
        "target": "window",
    },
    "ru": {
        "evidence": "hidden_note",
        "manual": "Я внимательно перебираю бумаги на читальном столе в поисках записок.",
        "magic": "Скрытое, явись на столе, чтобы найти спрятанные записи.",
        "spell": "unveil",
        "target": "desk",
    },
    "fr": {
        "evidence": "singed_cloak_fiber",
        "manual": "J'examine la fibre vert foncé prise dans l'encadrement de la porte.",
        "magic": "Trace, gleam on the doorframe pour révéler les traces sur la fibre.",
        "spell": "raise_the_lamp",
        "target": "doorframe",
    },
    "es": {
        "evidence": "scuff_marks",
        "manual": "Examino las rozaduras recientes del suelo junto a la salida.",
        "magic": "Trace, gleam on the floor para seguir las marcas hacia la salida.",
        "spell": "raise_the_lamp",
        "target": "floor",
    },
    "de": {
        "evidence": "dual_shimmer",
        "manual": "Ich untersuche den zweifarbigen Schimmer auf Vanes Haut aus der Nähe.",
        "magic": "Essence, speak on Vane's skin, um den Schimmer zu analysieren.",
        "spell": "identify_substance",
        "target": "skin",
    },
    "pt": {
        "evidence": "frost_pattern",
        "manual": "Examino atentamente os padrões de gelo na janela.",
        "magic": "Essence, speak on the window para analisar o padrão de gelo.",
        "spell": "identify_substance",
        "target": "window",
    },
    "zh": {
        "evidence": "hidden_note",
        "manual": "我仔细翻查阅览桌上的文件，寻找被藏起来的纸条。",
        "magic": "Veil, dissolve over the desk，寻找隐藏的字条。",
        "spell": "unveil",
        "target": "desk",
    },
    "ja": {
        "evidence": "singed_cloak_fiber",
        "manual": "扉枠に引っかかった濃緑色の繊維を詳しく調べます。",
        "magic": "Trace, gleam on the doorframe、濃緑色の繊維の痕跡を調べる。",
        "spell": "raise_the_lamp",
        "target": "doorframe",
    },
    "ko": {
        "evidence": "scuff_marks",
        "manual": "출구 옆 바닥의 새 긁힌 자국을 자세히 조사한다.",
        "magic": "Trace, gleam on the floor, 출구로 이어지는 자국을 추적한다.",
        "spell": "raise_the_lamp",
        "target": "floor",
    },
    "it": {
        "evidence": "dual_shimmer",
        "manual": "Esamino da vicino il bagliore bicolore sulla pelle di Vane.",
        "magic": "Essence, speak on Vane's skin per analizzare il bagliore.",
        "spell": "identify_substance",
        "target": "skin",
    },
}


def build_scenarios() -> tuple[dict[str, str], ...]:
    """Build one manual and one successful-rite probe per supported language."""
    scenarios: list[dict[str, str]] = []
    for language in SUPPORTED_LANGUAGES:
        probe = LANGUAGE_PROBES[language]
        scenarios.extend(
            (
                {
                    "name": f"manual_{language}",
                    "kind": "manual",
                    "language": language,
                    "player_input": probe["manual"],
                    "expected_evidence_id": probe["evidence"],
                },
                {
                    "name": f"magic_{language}",
                    "kind": "magic",
                    "language": language,
                    "player_input": probe["magic"],
                    "expected_evidence_id": probe["evidence"],
                    "expected_spell_id": probe["spell"],
                    "target_keyword": probe["target"],
                },
            )
        )
    return tuple(scenarios)


SCENARIOS = build_scenarios()


def parse_args() -> argparse.Namespace:
    """Parse diagnostic options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=["all", *(scenario["name"] for scenario in SCENARIOS)],
        default="all",
        help="Scenario to run (default: all)",
    )
    parser.add_argument(
        "--force-spell-success",
        action="store_true",
        help="Use SUCCESS for rite prompts instead of the production random roll",
    )
    parser.add_argument("--max-tokens", type=int, default=500)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help="JSONL output path (default: telemetry/live_evidence_diagnostic.jsonl)",
    )
    return parser.parse_args()


def utc_now() -> str:
    """Return an ISO timestamp in UTC."""
    return datetime.now(UTC).isoformat()


def write_log(log_file: Path, record: dict[str, Any]) -> None:
    """Append one structured diagnostic record."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def prompt_ids(prompt: str) -> list[str]:
    """Extract canonical IDs shown in prompt evidence sections."""
    ids = EVIDENCE_ID_RE.findall(prompt)
    for line in prompt.splitlines():
        if line.lower().startswith("must reveal when target matches:"):
            ids.extend(re.findall(r"[a-z0-9_]+", line.split(":", 1)[1], re.IGNORECASE))
    return list(dict.fromkeys(ids))


def output_language_stats(text: str) -> dict[str, int]:
    """Count Cyrillic and Latin letters in model output."""
    return {
        "cyrillic_letters": len(re.findall(r"[А-Яа-яЁё]", text)),
        "latin_letters": len(re.findall(r"[A-Za-z]", text)),
    }


def split_diagnostic_response(response: str) -> tuple[str, str]:
    """Separate test-only first-line reasoning from narration."""
    stripped = response.lstrip()
    first_line, separator, remainder = stripped.partition("\n")
    if not first_line.lower().startswith("[reasoning:"):
        return "", response.strip()
    reasoning = first_line[len("[REASONING:") :]
    if reasoning.endswith("]"):
        reasoning = reasoning[:-1]
    return reasoning.strip(), remainder.lstrip() if separator else ""


def evidence_set_matches(actual: list[str], expected: list[str]) -> bool:
    """Require exact evidence IDs, including multiplicity."""
    return Counter(actual) == Counter(expected)


def detect_narration_language(text: str) -> str | None:
    """Detect supported narration language without external dependencies."""
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    if re.search(r"[\u0400-\u04ff]", text):
        return "ru"
    if re.search(r"[\u3400-\u9fff]", text):
        return "zh"

    tokens = re.findall(r"[^\W\d_]+", text.casefold(), re.UNICODE)
    scores = {
        language: sum(token in markers for token in tokens)
        for language, markers in LATIN_LANGUAGE_MARKERS.items()
    }
    best_score = max(scores.values(), default=0)
    winners = [language for language, score in scores.items() if score == best_score]
    return winners[0] if best_score >= 2 and len(winners) == 1 else None


def narration_matches_language(text: str, expected_language: str) -> bool:
    """Return whether narration uses the scenario's requested language."""
    return detect_narration_language(text) == expected_language


def build_diagnostic_system_prompt(system_prompt: str) -> str:
    """Add test-only decision reasoning without changing production prompts."""
    system_prompt = system_prompt.replace(
        "- Never add meta-comments, notes, or OOC reasoning. "
        "Evidence control tags required by this prompt are the only exception.\n",
        "",
    )
    return f"""{system_prompt.rstrip()}

== DIAGNOSTIC-ONLY REQUIREMENT ==
Start every response with exactly one metadata line:
[REASONING: in 30 words or fewer, state whether matching evidence will be provided or not, and justify why]
Base the justification on the player's action, target, candidate description, and
discovery guidance. Then provide normal narration and required evidence control.
This test-only rule overrides any conflicting ban on meta reasoning."""


def scenario_selection(name: str) -> list[dict[str, str]]:
    """Return requested scenarios."""
    if name == "all":
        return list(SCENARIOS)
    return [scenario for scenario in SCENARIOS if scenario["name"] == name]


async def run_scenario(
    scenario: dict[str, str],
    *,
    force_spell_success: bool,
    max_tokens: int,
    temperature: float,
    log_file: Path,
    run_id: str,
) -> bool:
    """Build production narration plus test-only reasoning instrumentation."""
    language = scenario["language"]
    player_input = scenario["player_input"]
    expected_evidence_id = scenario["expected_evidence_id"]
    case_data = load_localized_case("case_001", language)["case"]
    location = case_data["locations"]["library"]
    state = PlayerState(case_id="case_001", current_location="library", language=language)

    spell_id, target = detect_spell_with_fuzzy(player_input)
    spell_outcome: str | None = None
    if spell_id:
        if force_spell_success:
            spell_outcome = "SUCCESS"
        else:
            spell_outcome = calculate_spell_outcome(spell_id, player_input, state)

    prompt, system_prompt, is_spell = build_narrator_or_spell_prompt(
        location_desc=location["description"],
        hidden_evidence=location["hidden_evidence"],
        discovered_ids=state.discovered_evidence,
        not_present=location.get("not_present", []),
        player_input=player_input,
        surface_elements=location.get("surface_elements", []),
        conversation_history=[],
        spell_contexts=location.get("spell_contexts"),
        verbosity=state.narrator_verbosity,
        world_context=case_data.get("world_context"),
        case_setting=case_data.get("setting", ""),
        language=language,
        spell_id=spell_id,
        target=target,
        spell_outcome=spell_outcome,
    )
    system_prompt = build_diagnostic_system_prompt(system_prompt)

    known_ids = [str(evidence["id"]) for evidence in location["hidden_evidence"]]
    prompt_evidence_ids = prompt_ids(prompt)
    target_rejected = is_spell and "Target status: INVALID" in prompt
    started = time.monotonic()
    chunks: list[dict[str, Any]] = []
    response = ""
    error: str | None = None
    llm_attempts: list[dict[str, Any]] = []

    print(f"\n[{scenario['name']}] language={language} input={player_input!r}")
    print(
        f"  detected spell={spell_id or '-'} target={target or '-'} outcome={spell_outcome or '-'}"
    )
    print(f"  prompt evidence IDs={prompt_evidence_ids}")
    if target_rejected:
        print("  prompt rejects target: no evidence can be revealed")

    try:
        stream = get_client().get_response_stream(
            prompt,
            system=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            trace=llm_attempts,
            disable_reasoning=True,
        )
        async for chunk in stream:
            now = time.monotonic() - started
            chunks.append({"index": len(chunks), "elapsed_s": round(now, 3), "chars": len(chunk)})
            response += chunk
    except Exception as exc:  # noqa: BLE001 - diagnostic must log and continue
        error = str(exc)

    total_s = round(time.monotonic() - started, 3)
    first_chunk_s = chunks[0]["elapsed_s"] if chunks else None
    reasoning, narration = split_diagnostic_response(response)
    exact_tag_ids = extract_evidence_from_response(narration)
    control_valid: bool | None = None
    control_reason: str | None = None
    control_result: str | None = None
    if is_spell:
        control_valid, control_reason = validate_rite_control_result(
            narration,
            set(prompt_evidence_ids),
        )
        control_result = extract_rite_control_result(narration)
    bracket_tags = [
        {"label": label.strip(), "value": value.strip()}
        for label, value in BRACKET_TAG_RE.findall(narration)
    ]
    expected_evidence_ids = [expected_evidence_id]
    narration_text = RITE_CONTROL_MARKER_PATTERN.sub("", narration).strip()
    detected_language = detect_narration_language(narration_text)
    checks = {
        "nonempty_response": bool(narration_text),
        "expected_evidence_revealed": expected_evidence_id in exact_tag_ids,
        "exact_evidence_set": evidence_set_matches(exact_tag_ids, expected_evidence_ids),
        "narration_language_correct": detected_language == language,
        "spell_detected": not scenario["kind"] == "magic" or is_spell,
        "rite_control_valid": not is_spell or control_valid is True,
        "reasoning_present": bool(reasoning),
    }
    passed = error is None and all(checks.values())
    record = {
        "run_id": run_id,
        "timestamp": utc_now(),
        "scenario": scenario["name"],
        "case_id": "case_001",
        "location_id": "library",
        "language": language,
        "player_input": player_input,
        "kind": scenario["kind"],
        "expected_evidence_id": expected_evidence_id,
        "model": getattr(get_client().settings, "DEFAULT_MODEL", "unknown"),
        "spell": {
            "detected": is_spell,
            "id": spell_id,
            "target": target,
            "outcome": spell_outcome,
            "force_success": force_spell_success,
        },
        "known_evidence_ids": known_ids,
        "prompt": {
            "sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "text": prompt,
            "system_text": system_prompt,
            "evidence_ids": prompt_evidence_ids,
            "has_exact_tag_rule": "[EVIDENCE_ID]" in system_prompt or "[EVIDENCE_ID]" in prompt,
            "has_language_rule": "LANGUAGE RULE" in system_prompt,
            "has_hidden_evidence_section": "HIDDEN EVIDENCE" in prompt,
            "has_spell_evidence_section": "CANDIDATE EVIDENCE" in prompt,
            "target_rejected": target_rejected,
        },
        "response": response,
        "response_language_stats": output_language_stats(narration_text),
        "parser": {
            "exact_evidence_tag_ids": exact_tag_ids,
            "bracket_tags": bracket_tags,
            "rite_control_valid": control_valid,
            "rite_control_reason": control_reason,
            "rite_control_result": control_result,
            "reasoning": reasoning,
            "narration": narration,
            "detected_narration_language": detected_language,
        },
        "stream": {
            "chunk_count": len(chunks),
            "first_chunk_s": first_chunk_s,
            "total_s": total_s,
            "chars": len(response),
            "chunks": chunks,
        },
        "llm_attempts": llm_attempts,
        "error": error,
        "checks": checks,
        "passed": passed,
    }
    write_log(log_file, record)

    if error:
        print(f"  ERROR: {error}")
        return False

    print(f"  raw response: {response!r}")
    print(f"  parsed [EVIDENCE_ID] IDs: {exact_tag_ids}")
    if is_spell:
        print(
            f"  rite control: valid={control_valid} reason={control_reason or '-'} "
            f"result={control_result or '-'}"
        )
    print(f"  decision reasoning: {reasoning or 'MISSING'}")
    print(
        f"  stream: chunks={len(chunks)} first={first_chunk_s}s "
        f"total={total_s}s chars={len(response)}"
    )
    print(f"  llm attempts: {llm_attempts}")
    print(f"  result: {'PASS' if passed else 'FAIL'} checks={checks}")
    return passed


async def main() -> int:
    """Run selected scenarios and return a process exit code."""
    args = parse_args()
    run_id = uuid4().hex
    settings = get_client().settings
    log_file = args.log_file.expanduser().resolve()
    write_log(
        log_file,
        {
            "run_id": run_id,
            "timestamp": utc_now(),
            "event": "run_started",
            "model": settings.DEFAULT_MODEL,
            "scenario": args.scenario,
            "force_spell_success": args.force_spell_success,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        },
    )
    print(f"Live evidence diagnostic: run_id={run_id}")
    print(f"Log: {log_file}")
    print(f"Model: {settings.DEFAULT_MODEL}")

    results: list[bool] = []
    for scenario in scenario_selection(args.scenario):
        results.append(
            await run_scenario(
                scenario,
                force_spell_success=args.force_spell_success,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                log_file=log_file,
                run_id=run_id,
            )
        )
    passed = sum(results)
    write_log(
        log_file,
        {
            "run_id": run_id,
            "timestamp": utc_now(),
            "event": "run_finished",
            "scenarios_passed": passed,
            "scenarios_total": len(results),
        },
    )
    print(
        f"\nFinished: {passed}/{len(results)} scenarios passed. "
        "Inspect JSONL log for full prompts/responses."
    )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
