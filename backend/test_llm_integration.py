#!/usr/bin/env python3
"""Test script to verify Multi-LLM Provider System is working correctly.

Run: cd backend && uv run python test_llm_integration.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_config_loading():
    """Test 1: Verify LLM settings load from .env"""
    print("\n" + "=" * 70)
    print("TEST 1: Configuration Loading")
    print("=" * 70)

    try:
        from src.config.llm_settings import get_llm_settings

        settings = get_llm_settings()

        print("✅ Settings loaded successfully")
        print(f"   Provider: {settings.DEFAULT_LLM_PROVIDER}")
        print(f"   Model: {settings.DEFAULT_MODEL}")
        print(f"   Fallback enabled: {settings.ENABLE_FALLBACK}")
        print(f"   Fallback model: {settings.FALLBACK_MODEL}")

        # Check API key is present (don't print it!)
        api_key = settings.get_api_key_for_provider(settings.DEFAULT_LLM_PROVIDER)
        if api_key:
            print(f"   API key: {'*' * 20} (configured)")
        else:
            print("   ❌ API key: NOT CONFIGURED")
            return False

        return True

    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False


async def test_llm_client_initialization():
    """Test 2: Verify LLM client initializes"""
    print("\n" + "=" * 70)
    print("TEST 2: LLM Client Initialization")
    print("=" * 70)

    try:
        from src.api.llm_client import get_client

        client = get_client()

        print("✅ LLM client initialized successfully")
        print(f"   Client type: {type(client).__name__}")
        print(f"   Settings loaded: {client.settings is not None}")

        return True

    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return False


async def test_simple_llm_call():
    """Test 3: Make actual LLM API call"""
    print("\n" + "=" * 70)
    print("TEST 3: Simple LLM API Call")
    print("=" * 70)

    try:
        from src.api.llm_client import get_client

        client = get_client()

        print("📡 Making API call: 'Say hello in 5 words or less'")

        response = await client.get_response(
            prompt="Say hello in 5 words or less", max_tokens=50, temperature=0.7
        )

        print("✅ LLM responded successfully")
        print(f"   Response: '{response}'")
        print(f"   Length: {len(response)} characters")

        return True

    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_system_prompt():
    """Test 4: LLM call with system prompt"""
    print("\n" + "=" * 70)
    print("TEST 4: LLM Call with System Prompt")
    print("=" * 70)

    try:
        from src.api.llm_client import get_client

        client = get_client()

        print("📡 Making API call with system prompt")

        response = await client.get_response(
            prompt="What's your role?",
            system="You are a detective investigating a crime. Respond in character.",
            max_tokens=100,
            temperature=0.7,
        )

        print("✅ System prompt working")
        print(f"   Response: '{response[:100]}...'")

        return True

    except Exception as e:
        print(f"❌ System prompt test failed: {e}")
        return False


async def test_mentor_integration():
    """Test 5: Test mentor.py integration"""
    print("\n" + "=" * 70)
    print("TEST 5: Mentor Module Integration")
    print("=" * 70)

    try:
        from src.context.mentor import build_graves_feedback_llm

        print("📡 Testing Graves feedback generation (this may take 5-10 seconds)")

        # Simple test case
        feedback = await build_graves_feedback_llm(
            case_id="case_001",
            hypothesis_id="h1_murder",
            user_reasoning="The victim was poisoned because there was a vial found.",
            is_correct=True,
            evidence_quality="good",
        )

        print("✅ Mentor integration working")
        print(f"   Feedback type: {type(feedback)}")
        print(f"   Feedback preview: '{feedback[:150]}...'")

        return True

    except Exception as e:
        print(f"❌ Mentor integration failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_briefing_integration():
    """Test 6: Test briefing.py integration"""
    print("\n" + "=" * 70)
    print("TEST 6: Briefing Module Integration")
    print("=" * 70)

    try:
        from src.context.briefing import ask_graves_question

        print("📡 Testing Graves briefing question (this may take 5-10 seconds)")

        response = await ask_graves_question(
            case_id="case_001",
            question="What should I know about this case?",
            conversation_history=[],
        )

        print("✅ Briefing integration working")
        print(f"   Response type: {type(response)}")
        print(f"   Response preview: '{response[:150]}...'")

        return True

    except Exception as e:
        print(f"❌ Briefing integration failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all integration tests"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " MULTI-LLM PROVIDER SYSTEM - INTEGRATION TEST SUITE ".center(68) + "║")
    print("╚" + "=" * 68 + "╝")

    results = []

    # Run tests
    results.append(("Config Loading", await test_config_loading()))
    results.append(("Client Init", await test_llm_client_initialization()))
    results.append(("Simple API Call", await test_simple_llm_call()))
    results.append(("System Prompt", await test_system_prompt()))
    results.append(("Mentor Integration", await test_mentor_integration()))
    results.append(("Briefing Integration", await test_briefing_integration()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<50} {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print("=" * 70)
    print(f"TOTAL: {passed}/{total} tests passed ({passed / total * 100:.0f}%)")

    if passed == total:
        print("\n🎉 All tests PASSED! Multi-LLM Provider System is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED. Check configuration or API keys.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
