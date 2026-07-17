"""Test narrator verbosity modes with real LLM calls.

Sends 5 immersive inputs through all 3 verbosity modes and compares results.
Run: uv run python -m tests.test_narrator_verbosity
"""

import asyncio
import json
import time
from pathlib import Path

from src.api.llm_client import get_client
from src.context.narrator import build_narrator_prompt, build_system_prompt

# ---------------------------------------------------------------------------
# Test fixtures — realistic case_001 data
# ---------------------------------------------------------------------------

LOCATION_DESC = """Frost on the windows. Unnatural cold.

The Sealed Archive spans three alcoves separated by towering shelves —
each a world unto itself, sound muffled by ancient tomes. You stand in
the western alcove. The eastern alcove, where a reading chair sits with
a burned-down candle, is forty feet away and out of direct sight line.

Professor Aldric Vane lies motionless near the reading desk. Black robes pooled
around him. His right arm outstretched — reaching toward a circle of melted
candles. His expression: not anger. Concern. His focus is partially drawn
from his robes, as if he started to react to something.

The smell of nightshade. Scattered herbs. The air feels wrong — heavy,
charged, cold in a way that has nothing to do with the season."""

SURFACE_ELEMENTS = [
    "Reading desk with scattered parchments and an ancient tome open to cramped handwriting",
    "Circle of melted candles on the floor, ritual space cleared",
    "Scattered dried herbs near the candle circle — pungent, unfamiliar smell",
    "Frost-covered window with unnatural patterns radiating from floor",
    "Professor Vane's body — arm reaching toward the ritual circle, focus partially drawn, expression of concern",
    "Odd dual-tone shimmer on Professor Vane's skin: blue-white and yellowish-green",
    "Faint scuff marks leading toward the exit",
    "A dark green fiber caught on the doorframe",
    "Eastern alcove visible in the distance — reading chair, burned-down candle",
]

HIDDEN_EVIDENCE = [
    {
        "id": "hidden_note",
        "name": "Crumpled Apology Note",
        "discovery_guidance": "Revealed when player searches the reading desk, examines papers, or uses Unveil on the desk area.",
        "description": 'A small, crumpled note written in shaky, childlike handwriting: "Master Professor, D. is sorry..."',
        "tag": "[EVIDENCE: hidden_note]",
        "significance": "Connects to an ingredient theft but not necessarily the attack.",
    },
    {
        "id": "frost_pattern",
        "name": "Frost Discharge Pattern",
        "discovery_guidance": "Revealed when player casts Identify Substance on frost/window/floor, or performs magical analysis.",
        "description": "The frost radiates from a single point near the candle circle. Magical discharge signature.",
        "tag": "[EVIDENCE: frost_pattern]",
        "significance": "Forbidden craft was used here — but what kind?",
    },
    {
        "id": "singed_cloak_fiber",
        "name": "Singed Green Fiber",
        "discovery_guidance": "Revealed when player examines the doorframe closely or uses Raise the Lamp near the exit.",
        "description": "An expensive green wool fiber, singed at the edges. Caught on the doorframe.",
        "tag": "[EVIDENCE: singed_cloak_fiber]",
        "significance": "Someone wearing expensive green robes left in a hurry.",
    },
]

NOT_PRESENT = [
    {
        "triggers": ["blood", "bleeding"],
        "response": "There is no blood at this scene. Paralytic binding leaves no wounds.",
    },
]

VICTIM = {
    "name": "Professor Aldric Vane",
    "humanization": "The most feared professor at Blackwood Collegiate — harsh, unforgiving, brilliant. His arm is outstretched, reaching toward a student he was trying to protect.",
    "cause_of_death": "Layered paralytic binding: Thief's Candle discharge + bound familiar binding magic",
}

WORLD_CONTEXT = """It is the students' second year at Blackwood Collegiate. The The Hollow Below has been opened.
Mr. Crankshaw's cat, Morrigan, was found held in stillness weeks ago. uninitiated-born students live in fear.
The school is tense, divided, suspicious."""

# ---------------------------------------------------------------------------
# 5 immersive player inputs (no evidence should be revealed for most)
# ---------------------------------------------------------------------------

PLAYER_INPUTS = [
    # 1. Generic atmospheric exploration
    "I step into the Sealed Archive and take in the scene. What does it feel like?",
    # 2. Specific object examination (no evidence match)
    "I kneel beside Professor Vane's body and study his face. What expression is frozen there?",
    # 3. Sensory exploration
    "I close my eyes and breathe in deeply. What do I smell? I listen to the silence.",
    # 4. Environmental interaction
    "I walk slowly toward the eastern alcove, running my fingers along the spines of the ancient books on the shelves as I go.",
    # 5. Emotional/atmospheric reaction
    "I stand at the frost-covered window and trace the unnatural patterns with my focus tip, not casting anything, just feeling the cold radiate through the glass.",
]

MODES = ["concise", "storyteller", "atmospheric"]


async def run_test(mode: str, player_input: str, input_idx: int) -> dict:
    """Run a single narrator call and collect metrics."""
    prompt = build_narrator_prompt(
        location_desc=LOCATION_DESC,
        hidden_evidence=HIDDEN_EVIDENCE,
        discovered_ids=[],
        not_present=NOT_PRESENT,
        player_input=player_input,
        surface_elements=SURFACE_ELEMENTS,
        conversation_history=[],
        victim=VICTIM,
        verbosity=mode,
        world_context=WORLD_CONTEXT,
    )
    system_prompt = build_system_prompt(mode)

    client = get_client()
    start = time.monotonic()
    response = await client.get_response(
        prompt=prompt,
        system=system_prompt,
        max_tokens=1024,
    )
    elapsed = time.monotonic() - start

    text = response.strip()
    words = len(text.split())
    sentences = text.count(".") + text.count("!") + text.count("?")
    paragraphs = len([p for p in text.split("\n\n") if p.strip()])

    return {
        "mode": mode,
        "input_idx": input_idx + 1,
        "input_preview": player_input[:60] + "..." if len(player_input) > 60 else player_input,
        "response": text,
        "word_count": words,
        "sentence_count": sentences,
        "paragraph_count": paragraphs,
        "time_s": round(elapsed, 2),
    }


async def main():
    print("=" * 80)
    print("NARRATOR VERBOSITY MODE COMPARISON TEST")
    print("=" * 80)
    print(f"Modes: {MODES}")
    print(f"Inputs: {len(PLAYER_INPUTS)}")
    print(f"Total LLM calls: {len(MODES) * len(PLAYER_INPUTS)}")
    print()

    all_results: list[dict] = []

    for i, player_input in enumerate(PLAYER_INPUTS):
        print(f"\n{'─' * 80}")
        print(f"INPUT {i+1}: {player_input}")
        print(f"{'─' * 80}")

        # Run all 3 modes for this input concurrently
        tasks = [run_test(mode, player_input, i) for mode in MODES]
        results = await asyncio.gather(*tasks)

        for r in results:
            all_results.append(r)
            print(f"\n  [{r['mode'].upper():>12}] {r['word_count']:>3} words | {r['sentence_count']} sentences | {r['paragraph_count']} paragraphs | {r['time_s']}s")
            print(f"  {'─' * 70}")
            # Indent response for readability
            for line in r["response"].split("\n"):
                print(f"    {line}")

    # ---------------------------------------------------------------------------
    # Summary statistics
    # ---------------------------------------------------------------------------
    print(f"\n\n{'=' * 80}")
    print("SUMMARY STATISTICS")
    print(f"{'=' * 80}\n")

    for mode in MODES:
        mode_results = [r for r in all_results if r["mode"] == mode]
        avg_words = sum(r["word_count"] for r in mode_results) / len(mode_results)
        avg_sentences = sum(r["sentence_count"] for r in mode_results) / len(mode_results)
        avg_paragraphs = sum(r["paragraph_count"] for r in mode_results) / len(mode_results)
        min_words = min(r["word_count"] for r in mode_results)
        max_words = max(r["word_count"] for r in mode_results)

        print(f"  {mode.upper():>12}: avg {avg_words:.0f} words ({min_words}-{max_words}), "
              f"avg {avg_sentences:.1f} sentences, avg {avg_paragraphs:.1f} paragraphs")

    # Differentiation analysis
    print(f"\n{'─' * 80}")
    print("DIFFERENTIATION ANALYSIS")
    print(f"{'─' * 80}\n")

    mode_avgs = {}
    for mode in MODES:
        mode_results = [r for r in all_results if r["mode"] == mode]
        mode_avgs[mode] = sum(r["word_count"] for r in mode_results) / len(mode_results)

    concise_avg = mode_avgs["concise"]
    storyteller_avg = mode_avgs["storyteller"]
    atmospheric_avg = mode_avgs["atmospheric"]

    ratio_st_c = storyteller_avg / concise_avg if concise_avg > 0 else 0
    ratio_at_c = atmospheric_avg / concise_avg if concise_avg > 0 else 0
    ratio_at_st = atmospheric_avg / storyteller_avg if storyteller_avg > 0 else 0

    print(f"  storyteller/concise ratio:    {ratio_st_c:.2f}x (target: ~2-3x)")
    print(f"  atmospheric/concise ratio:    {ratio_at_c:.2f}x (target: ~3-5x)")
    print(f"  atmospheric/storyteller ratio: {ratio_at_st:.2f}x (target: ~1.5-2x)")
    print()

    if ratio_st_c < 1.5:
        print("  ⚠ PROBLEM: storyteller is not meaningfully longer than concise")
    if ratio_at_c < 2.0:
        print("  ⚠ PROBLEM: atmospheric is not meaningfully longer than concise")
    if ratio_at_st < 1.3:
        print("  ⚠ PROBLEM: atmospheric is barely different from storyteller")
    if ratio_st_c >= 1.5 and ratio_at_c >= 2.0 and ratio_at_st >= 1.3:
        print("  ✓ Verbosity modes show meaningful differentiation")

    # Save raw results
    output_path = Path(__file__).parent / "narrator_verbosity_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Raw results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
