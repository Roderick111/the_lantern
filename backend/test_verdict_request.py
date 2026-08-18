#!/usr/bin/env python3
"""Test verdict request validation to see what backend expects."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_verdict_request_validation():
    """Test what the backend expects in SubmitVerdictRequest."""
    print("\n" + "=" * 70)
    print("BACKEND VERDICT REQUEST VALIDATION TEST")
    print("=" * 70)


    from pydantic import ValidationError

    from src.api.routes import SubmitVerdictRequest

    # Test 1: Valid request
    print("\n✅ TEST 1: Valid Request")
    print("-" * 70)
    try:
        valid_request = SubmitVerdictRequest(
            case_id="case_001",
            player_id="default",
            accused_suspect_id="cassian",
            reasoning="The evidence shows Cassian is guilty.",
            evidence_cited=["evidence_1", "evidence_2"],
        )
        print(f"SUCCESS: {valid_request.model_dump()}")
    except ValidationError as e:
        print(f"FAILED: {e}")

    # Test 2: Missing optional fields (with defaults)
    print("\n✅ TEST 2: Request with Defaults")
    print("-" * 70)
    try:
        default_request = SubmitVerdictRequest(
            accused_suspect_id="cassian",
            reasoning="The evidence shows Cassian is guilty.",
        )
        print(f"SUCCESS: {default_request.model_dump()}")
    except ValidationError as e:
        print(f"FAILED: {e}")

    # Test 3: Empty evidence_cited
    print("\n✅ TEST 3: Empty evidence_cited")
    print("-" * 70)
    try:
        empty_evidence_request = SubmitVerdictRequest(
            accused_suspect_id="cassian",
            reasoning="The evidence shows Cassian is guilty.",
            evidence_cited=[],
        )
        print(f"SUCCESS: {empty_evidence_request.model_dump()}")
    except ValidationError as e:
        print(f"FAILED: {e}")

    # Test 4: Invalid accused_suspect_id (too short)
    print("\n❌ TEST 4: Invalid accused_suspect_id (empty)")
    print("-" * 70)
    try:
        invalid_request = SubmitVerdictRequest(
            accused_suspect_id="",  # Invalid: min_length=1
            reasoning="The evidence shows Cassian is guilty.",
        )
        print(f"SUCCESS: {invalid_request.model_dump()}")
    except ValidationError as e:
        print(f"FAILED (expected): {e}")

    # Test 5: Invalid reasoning (empty)
    print("\n❌ TEST 5: Invalid reasoning (empty)")
    print("-" * 70)
    try:
        invalid_request = SubmitVerdictRequest(
            accused_suspect_id="cassian",
            reasoning="",  # Invalid: min_length=1
        )
        print(f"SUCCESS: {invalid_request.model_dump()}")
    except ValidationError as e:
        print(f"FAILED (expected): {e}")

    # Test 6: Invalid reasoning (too long)
    print("\n❌ TEST 6: Invalid reasoning (too long)")
    print("-" * 70)
    try:
        long_reasoning = "x" * 2001  # Invalid: max_length=2000
        invalid_request = SubmitVerdictRequest(
            accused_suspect_id="cassian",
            reasoning=long_reasoning,
        )
        print(f"SUCCESS: {invalid_request.model_dump()}")
    except ValidationError as e:
        print(f"FAILED (expected): {e.errors()[0]}")

    # Test 7: Invalid case_id pattern
    print("\n❌ TEST 7: Invalid case_id pattern (spaces)")
    print("-" * 70)
    try:
        invalid_request = SubmitVerdictRequest(
            case_id="case 001",  # Invalid: pattern doesn't allow spaces
            accused_suspect_id="cassian",
            reasoning="The evidence shows Cassian is guilty.",
        )
        print(f"SUCCESS: {invalid_request.model_dump()}")
    except ValidationError as e:
        print(f"FAILED (expected): {e.errors()[0]}")

    # Print expected request format
    print("\n" + "=" * 70)
    print("EXPECTED REQUEST FORMAT")
    print("=" * 70)
    print("""
{
  "case_id": "case_001",           // Default: "case_001", pattern: ^[a-zA-Z0-9_-]+$
  "player_id": "default",          // Default: "default", pattern: ^[a-zA-Z0-9_-]+$
  "accused_suspect_id": "cassian",   // REQUIRED, min_length: 1, pattern: ^[a-zA-Z0-9_-]+$
  "reasoning": "The frost...",     // REQUIRED, min_length: 1, max_length: 2000
  "evidence_cited": ["e1", "e2"]   // Default: [], list of evidence IDs
}
""")

    print("\n" + "=" * 70)
    print("VALIDATION RULES")
    print("=" * 70)
    print("""
✅ Required fields:
   - accused_suspect_id (min 1 char, max 64, alphanumeric + _-)
   - reasoning (min 1 char, max 2000)

✅ Optional fields (with defaults):
   - case_id (default: "case_001")
   - player_id (default: "default")
   - evidence_cited (default: [])

❌ Common validation failures:
   - Empty accused_suspect_id or reasoning
   - Reasoning > 2000 characters
   - Invalid characters in IDs (no spaces, special chars except _-)
   - IDs > 64 characters
""")


if __name__ == "__main__":
    test_verdict_request_validation()
