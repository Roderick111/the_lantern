#!/usr/bin/env python3
"""Test Graves LLM feedback generation to see why it's falling back to templates."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_graves_feedback():
    """Test Graves feedback with actual LLM call."""
    print("\n" + "=" * 70)
    print("GRAVES LLM FEEDBACK TEST")
    print("=" * 70)

    from src.context.mentor import build_graves_feedback_llm

    # Test with correct verdict
    print("\n📝 Testing CORRECT verdict feedback...")
    print("-" * 70)

    try:
        feedback = await build_graves_feedback_llm(
            correct=True,
            score=85,
            fallacies=[],
            reasoning="The evidence clearly shows Professor Morraine used forbidden craft to commit the crime. The focus signatures match and the timing aligns perfectly.",
            accused_id="professor_morraine",
            solution={
                "culprit": "professor_morraine",
                "critical_evidence": ["focus_signature", "timing_evidence"],
                "method": "Forbidden craft ritual",
                "motive": "Academic rivalry",
            },
            attempts_remaining=9,
            evidence_cited=["focus_signature", "timing_evidence"],
            feedback_templates={"correct_praise": "Well done", "incorrect_roast": "Think again"},
            case_id="case_002",
        )

        print("✅ SUCCESS - LLM Feedback Generated:")
        print(f"\n{feedback}\n")
        print(f"Length: {len(feedback)} characters")

        # Check if it's template fallback
        if "Reasoning quality:" in feedback and len(feedback) < 150:
            print("\n⚠️  WARNING: This looks like TEMPLATE fallback!")
            print("   Template pattern detected")
        else:
            print("\n✅ This looks like real LLM response")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()

    # Test with incorrect verdict
    print("\n" + "=" * 70)
    print("📝 Testing INCORRECT verdict feedback...")
    print("-" * 70)

    try:
        feedback = await build_graves_feedback_llm(
            correct=False,
            score=45,
            fallacies=["confirmation_bias"],
            reasoning="I think Cassian did it because he's always suspicious.",
            accused_id="cassian_thorne",
            solution={
                "culprit": "professor_morraine",
                "critical_evidence": ["focus_signature", "timing_evidence"],
                "method": "Forbidden craft ritual",
                "motive": "Academic rivalry",
            },
            attempts_remaining=8,
            evidence_cited=["cassian_testimony"],
            feedback_templates={"correct_praise": "Well done", "incorrect_roast": "Think again"},
            case_id="case_002",
        )

        print("✅ SUCCESS - LLM Feedback Generated:")
        print(f"\n{feedback}\n")
        print(f"Length: {len(feedback)} characters")

        if "actual culprit was" in feedback.lower():
            print("\n⚠️  WARNING: This looks like TEMPLATE fallback!")
        else:
            print("\n✅ This looks like real LLM response")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_graves_feedback())
