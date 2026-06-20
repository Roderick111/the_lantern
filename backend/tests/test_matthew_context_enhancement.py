from src.context.matthew_llm import build_context_prompt


def test_build_context_prompt_includes_new_fields():
    """Verify location description and witness history are in the prompt."""

    # Mock data
    case_context = {
        "victim": "Mr. Body",
        "location": "Library",
        "suspects": ["Plum", "Scarlet"],
        "witnesses": ["Mustard", "Green"],
    }
    evidence = []
    history = []

    # New fields
    location_desc = "A dusty room filled with ancient tomes and a smell of old parchment."
    witness_history = "Player: Where were you?\nWitness (Mustard): In the kitchen."

    # Build prompt
    prompt = build_context_prompt(
        case_context=case_context,
        evidence_discovered=evidence,
        conversation_history=history,
        location_description=location_desc,
        witness_history=witness_history,
    )

    # Assertions
    assert "CURRENT SITUATION (where you are):" in prompt
    assert location_desc in prompt
    assert "RECENT WITNESS INTERACTIONS (what player just asked):" in prompt
    assert witness_history in prompt


def test_build_context_prompt_handles_empty_fields():
    """Verify fallbacks for empty new fields."""
    case_context = {"victim": "Mr. Body"}

    prompt = build_context_prompt(
        case_context=case_context,
        evidence_discovered=[],
        conversation_history=[],
        location_description="",
        witness_history="",
    )

    assert "Unknown location" in prompt
    assert "No recent witness interactions" in prompt
