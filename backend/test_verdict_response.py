#!/usr/bin/env python3
"""Test script to see EXACT verdict response structure that backend sends."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_verdict_response_structure():
    """Generate a sample verdict response to see exact JSON structure."""
    print("\n" + "=" * 70)
    print("BACKEND VERDICT RESPONSE STRUCTURE TEST")
    print("=" * 70)

    from src.api.routes import (
        ConfrontationDialogue,
        FallacyDetail,
        MentorFeedback,
        SubmitVerdictResponse,
    )

    # Create a sample response matching what the backend would send
    sample_response = SubmitVerdictResponse(
        correct=True,
        attempts_remaining=2,
        case_solved=True,
        mentor_feedback=MentorFeedback(
            analysis="Good work on identifying the culprit.",
            fallacies_detected=[
                FallacyDetail(
                    name="Confirmation Bias",
                    description="Seeking only confirming evidence",
                    example="",  # Using default
                )
            ],
            score=85,
            quality="good",
            critique="",
            praise="",
            hint=None,  # Nullable field
        ),
        confrontation=ConfrontationDialogue(
            dialogue=[
                {"speaker": "Lantern Inspector", "text": "I know what you did."},
                {"speaker": "Cassian", "text": "You can't prove anything!"},
            ],
            aftermath="Cassian was taken into custody.",
        ),
        reveal=None,
        wrong_suspect_response=None,
    )

    # Convert to dict (this is what gets sent as JSON)
    response_dict = sample_response.model_dump()

    print("\n📤 EXACT JSON THAT BACKEND SENDS:")
    print("=" * 70)
    print(json.dumps(response_dict, indent=2))

    print("\n" + "=" * 70)
    print("FIELD-BY-FIELD ANALYSIS")
    print("=" * 70)

    def analyze_field(path, value, indent=0):
        """Recursively analyze field structure."""
        prefix = "  " * indent
        if isinstance(value, dict):
            print(f"{prefix}{path}:")
            for k, v in value.items():
                analyze_field(k, v, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{path}: array[{len(value)}]")
            if value and isinstance(value[0], dict):
                print(f"{prefix}  First item:")
                for k, v in value[0].items():
                    analyze_field(k, v, indent + 2)
        else:
            type_info = type(value).__name__
            null_info = " (NULL)" if value is None else ""
            empty_info = " (EMPTY)" if value == "" else ""
            print(f"{prefix}{path}: {type_info}{null_info}{empty_info} = {repr(value)[:50]}")

    for key, value in response_dict.items():
        analyze_field(key, value)

    print("\n" + "=" * 70)
    print("ZOD SCHEMA REQUIREMENTS")
    print("=" * 70)

    print("\n✅ Required fields (must be present):")
    print("   - correct: boolean")
    print("   - attempts_remaining: number")
    print("   - case_solved: boolean")
    print("   - mentor_feedback: object")

    print("\n⚠️  Nullable fields (can be null):")
    print("   - confrontation: object | null")
    print("   - reveal: string | null")
    print("   - wrong_suspect_response: string | null")

    print("\n🔍 mentor_feedback sub-fields:")
    print("   - analysis: string (required)")
    print("   - fallacies_detected: array (required, can be [])")
    print("   - score: number (required)")
    print("   - quality: string (required)")
    print("   - critique: string (required)")
    print("   - praise: string (required)")
    print("   - hint: string | null | undefined (optional)")

    print("\n🔍 fallacies_detected[].fields:")
    print("   - name: string (required)")
    print("   - description: string (required)")
    print("   - example: string | undefined (optional)")

    print("\n🔍 confrontation.fields (if present):")
    print("   - dialogue: array of objects (required)")
    print("   - aftermath: string (required)")

    print("\n🔍 dialogue[].fields:")
    print("   - speaker: string (required)")
    print("   - text: string (required)")
    print("   - tone: string | undefined (optional)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_verdict_response_structure())
