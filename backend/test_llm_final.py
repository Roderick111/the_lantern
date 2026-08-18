#!/usr/bin/env python3
"""Final integration test with correct function signatures."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_mentor_feedback():
    """Test mentor.py - Graves feedback generation"""
    print("\n" + "=" * 70)
    print("TEST: Mentor Feedback (Graves)")
    print("=" * 70)

    try:
        from src.context.mentor import build_graves_feedback_llm

        print("📡 Generating Graves feedback (may take 5-10 seconds)...")

        # Use correct signature from mentor.py:597
        feedback = await build_graves_feedback_llm(
            correct=True,
            score=85,
            fallacies=[],
            reasoning="The evidence clearly shows poisoning based on the vial found.",
            accused_id="suspect_001",
            solution={
                "culprit": "suspect_001",
                "critical_evidence": ["evidence_vial"],
                "motive": "revenge",
            },
            attempts_remaining=2,
            evidence_cited=["evidence_vial", "evidence_timeline"],
            feedback_templates={"correct_praise": "Good work", "incorrect_roast": "Not quite"},
            case_id="case_001",
        )

        print("✅ Mentor feedback generated")
        print(f"   Type: {type(feedback)}")
        print(f"   Length: {len(feedback)} chars")
        print(f"   Preview: '{feedback[:200]}...'")

        return True

    except Exception as e:
        print(f"❌ Mentor test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_briefing_question():
    """Test briefing.py - Graves Q&A"""
    print("\n" + "=" * 70)
    print("TEST: Briefing System (Graves Q&A)")
    print("=" * 70)

    try:
        from src.context.briefing import ask_graves_question

        print("📡 Testing Graves briefing (may take 5-10 seconds)...")

        # Use correct signature from briefing.py:188
        response = await ask_graves_question(
            question="What should I focus on in this investigation?",
            case_assignment="A student has been found dead in the dungeons.",
            teaching_moment="Remember to look for contradictions in witness statements.",
            rationality_concept="base_rate_fallacy",
            concept_description="Ignoring prior probabilities when evaluating evidence.",
            conversation_history=[],
            briefing_context={
                "witnesses": ["witness_001", "witness_002"],
                "suspects": ["suspect_001"],
                "location": "Blackwood Collegiate Dungeons",
                "overview": "Mysterious death investigation",
            },
        )

        print("✅ Briefing response generated")
        print(f"   Type: {type(response)}")
        print(f"   Length: {len(response)} chars")
        print(f"   Preview: '{response[:200]}...'")

        return True

    except Exception as e:
        print(f"❌ Briefing test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " FINAL INTEGRATION TEST - Multi-LLM Provider System ".center(68) + "║")
    print("╚" + "=" * 68 + "╝")

    # Quick config check
    print("\n📋 Configuration:")
    print("-" * 70)
    from src.config.llm_settings import get_llm_settings

    settings = get_llm_settings()
    print(f"   Provider: {settings.DEFAULT_LLM_PROVIDER}")
    print(f"   Model: {settings.DEFAULT_MODEL}")
    print(f"   Fallback: {settings.FALLBACK_MODEL}")

    # Run tests
    results = []
    results.append(("Mentor Feedback", await test_mentor_feedback()))
    results.append(("Briefing Q&A", await test_briefing_question()))

    # Summary
    print("\n" + "=" * 70)
    print("FINAL TEST SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<50} {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print("=" * 70)
    print(f"TOTAL: {passed}/{total} tests passed ({passed / total * 100:.0f}%)")

    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("\n✅ Multi-LLM Provider System is FULLY OPERATIONAL")
        print("\nNext steps:")
        print("   1. Start backend: uv run uvicorn src.main:app --reload")
        print("   2. Test witness interrogation via API")
        print("   3. Test verdict submission with Graves feedback")
        print("=" * 70)
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
