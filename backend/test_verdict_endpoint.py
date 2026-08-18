#!/usr/bin/env python3
"""Test verdict endpoint directly to see exact error."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_verdict_endpoint():
    """Test verdict endpoint with various inputs to see errors."""
    print("\n" + "=" * 70)
    print("VERDICT ENDPOINT DIRECT TEST")
    print("=" * 70)

    from fastapi import HTTPException
    from pydantic import ValidationError

    from src.api.routes import SubmitVerdictRequest, submit_verdict

    # Test 1: Valid request
    print("\n✅ TEST 1: Valid Request")
    print("-" * 70)
    try:
        request = SubmitVerdictRequest(
            case_id="case_001",
            player_id="default",
            accused_suspect_id="cassian_thorne",
            reasoning="The evidence clearly points to Cassian as the culprit based on the focus signature.",
            evidence_cited=["focus_signature", "witness_statement"],
        )
        print(f"Request: {request.model_dump_json(indent=2)}")

        result = await submit_verdict(request)
        print("✅ SUCCESS")
        print(f"   Correct: {result.correct}")
        print(f"   Attempts remaining: {result.attempts_remaining}")
        print(f"   Mentor feedback: {result.mentor_feedback.analysis[:100]}...")

    except HTTPException as e:
        print(f"❌ HTTP Error {e.status_code}: {e.detail}")
    except ValidationError as e:
        print(f"❌ Validation Error: {e}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

    # Test 2: Empty reasoning
    print("\n❌ TEST 2: Empty Reasoning (should fail)")
    print("-" * 70)
    try:
        request = SubmitVerdictRequest(
            accused_suspect_id="cassian_thorne",
            reasoning="",  # Invalid
        )
        result = await submit_verdict(request)
        print("✅ Unexpected success")
    except ValidationError as e:
        print(f"❌ Validation Error (expected): {e.errors()[0]['msg']}")
    except HTTPException as e:
        print(f"❌ HTTP Error {e.status_code}: {e.detail}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

    # Test 3: Missing required fields
    print("\n❌ TEST 3: Missing accused_suspect_id (should fail)")
    print("-" * 70)
    try:
        # This should fail at Pydantic validation, not endpoint
        from pydantic import ValidationError

        request_dict = {
            "reasoning": "The evidence shows guilt.",
            # Missing accused_suspect_id
        }
        request = SubmitVerdictRequest(**request_dict)
        result = await submit_verdict(request)
        print("✅ Unexpected success")
    except ValidationError as e:
        print(f"❌ Validation Error (expected): {e.errors()[0]['msg']}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print("KEY FINDINGS")
    print("=" * 70)
    print("""
If you're getting a 400 error, check:

1. **Request Validation Errors** (400 Bad Request):
   - Empty accused_suspect_id or reasoning
   - Reasoning > 2000 characters
   - Invalid characters in IDs (only alphanumeric, _, -)

2. **Backend Errors** (500 Internal Server Error):
   - Case file not found
   - Solution not configured
   - Database/state errors

3. **Response Validation Errors** (Client-side Zod):
   - Zod schema mismatch with backend response
   - Missing required fields
   - Incorrect field types

To debug:
- Check browser Network tab → Request payload
- Check browser Console → Zod validation errors
- Check backend logs → FastAPI validation errors
""")


if __name__ == "__main__":
    asyncio.run(test_verdict_endpoint())
