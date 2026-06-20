"""Mentor feedback generator (template-based) for verdict evaluation."""

import logging
from typing import Any

from src.config.language import get_language_instruction

logger = logging.getLogger(__name__)


def format_common_mistakes(common_mistakes: list[dict[str, str]]) -> str:
    """Format common mistakes for Graves prompt."""
    if not common_mistakes:
        return "No common mistakes defined."
    lines = []
    for i, m in enumerate(common_mistakes, 1):
        lines.append(f"{i}. Error: {m.get('error', 'Unknown error')}")
        if m.get("reason"):
            lines.append(f"   Why players make this: {m['reason']}")
        if m.get("why_wrong"):
            lines.append(f"   Why it's wrong: {m['why_wrong']}")
    return "\n".join(lines)


def format_fallacies_to_catch(fallacies: list[dict[str, str]]) -> str:
    """Format fallacies to catch for Graves prompt."""
    if not fallacies:
        return "No specific fallacies defined."
    return "\n".join(
        f"- {f.get('fallacy', 'Unknown')}: {f['example']}"
        if f.get("example")
        else f"- {f.get('fallacy', 'Unknown')}"
        for f in fallacies
    )


def format_timeline(timeline: list[dict[str, Any]]) -> str:
    """Format timeline for Graves alibi evaluation."""
    if not timeline:
        return "No timeline available."
    lines = []
    for e in timeline:
        w = e.get("witnesses", [])
        w_str = f" (witnesses: {', '.join(w)})" if w else ""
        lines.append(f"- {e.get('time', '?')}: {e.get('event', 'Unknown event')}{w_str}")
    return "\n".join(lines)


def _format_bullet_list(items: list[str], empty_msg: str = "None defined.") -> str:
    """Format a list of strings as bullet points."""
    if not items:
        return empty_msg
    return "\n".join(f"- {item}" for item in items)


def format_deductions_required(deductions: list[str]) -> str:
    """Format required deductions for Graves prompt."""
    return _format_bullet_list(deductions, "No specific deductions required.")


def format_correct_reasoning(reasoning_list: list[str]) -> str:
    """Format correct reasoning requirements for Graves prompt."""
    return _format_bullet_list(reasoning_list, "No specific reasoning requirements.")


def _build_case_context_section(
    briefing_context: dict[str, Any] | None,
    culprit_note: str = "DO NOT reveal culprit",
) -> str:
    """Build case context section shared by roast and praise prompts."""
    if not briefing_context:
        return ""

    from src.context.rationality_context import get_rationality_context

    witnesses = briefing_context.get("witnesses", [])
    witness_info = "\n".join([f"- {w['name']}: {w.get('personality', '')}" for w in witnesses])
    suspects = briefing_context.get("suspects", [])
    suspect_list = ", ".join(suspects) if suspects else "To be determined"
    location = briefing_context.get("location", {})
    location_desc = f"{location.get('name', 'Unknown')}: {location.get('description', '')}"
    case_overview = briefing_context.get("case_overview", "")

    return f"""
CASE CONTEXT (for natural reference - {culprit_note}):
Overview: {case_overview}
Location: {location_desc}
Witnesses:
{witness_info}
Suspects: {suspect_list}

RATIONALITY PRINCIPLES (reference naturally when relevant):
{get_rationality_context()}
"""


def _build_victim_section(
    victim: dict[str, Any] | None,
    instruction: str = "reference naturally if player seems disconnected from stakes",
) -> str:
    """Build victim context section shared by roast and praise prompts."""
    if not victim or not victim.get("name"):
        return ""
    return f"""
VICTIM ({instruction}):
{victim.get("name", "")}: {victim.get("humanization", "")}
"""


def _build_evaluator_section(
    evaluator_result: dict[str, Any] | None,
    include_strengths: bool = False,
    trust_note: str = "",
) -> str:
    """Build evaluator assessment section shared by roast and praise prompts."""
    if not evaluator_result:
        return ""

    ev_summary = evaluator_result.get("summary", "")
    ev_weaknesses = evaluator_result.get("weaknesses", [])
    ev_fallacies = evaluator_result.get("fallacies", [])
    weaknesses_str = "\n".join(f"- {w}" for w in ev_weaknesses) if ev_weaknesses else "None"
    eval_fallacies_str = "\n".join(f"- {f}" for f in ev_fallacies) if ev_fallacies else "None"

    strengths_block = ""
    if include_strengths:
        ev_strengths = evaluator_result.get("strengths", [])
        strengths_str = "\n".join(f"- {s}" for s in ev_strengths) if ev_strengths else "None"
        strengths_block = f"\nStrengths found:\n{strengths_str}"

    header = "EVALUATOR ASSESSMENT (use this to inform your feedback"
    if trust_note:
        header += f" {trust_note}"
    header += "):"

    return f"""
{header}
Summary: {ev_summary}{strengths_block}
Weaknesses found:
{weaknesses_str}
Fallacies detected:
{eval_fallacies_str}
"""


def _build_enhanced_section(
    enhanced_solution: dict[str, Any] | None,
    include_mistakes: bool = False,
) -> str:
    """Build enhanced solution section. Roast mode includes mistakes/fallacies."""
    if not enhanced_solution:
        return ""

    deductions = enhanced_solution.get("deductions_required", [])
    correct_reasoning = enhanced_solution.get("correct_reasoning_requires", [])

    if include_mistakes:
        common_mistakes = enhanced_solution.get("common_mistakes", [])
        fallacies_to_catch = enhanced_solution.get("fallacies_to_catch", [])
        return f"""
COMMON MISTAKES (if player made one, call it out specifically):
{format_common_mistakes(common_mistakes)}

FALLACIES TO WATCH FOR:
{format_fallacies_to_catch(fallacies_to_catch)}

REQUIRED DEDUCTIONS (player should have made these):
{format_deductions_required(deductions)}

CORRECT REASONING REQUIRES:
{format_correct_reasoning(correct_reasoning)}
"""
    return f"""
DEDUCTIONS PLAYER SHOULD HAVE MADE (evaluate if they demonstrated these):
{format_deductions_required(deductions)}

CORRECT REASONING REQUIRES:
{format_correct_reasoning(correct_reasoning)}
"""


def build_mentor_feedback(
    correct: bool,
    score: int,
    fallacies: list[str],
    reasoning: str,
    accused_id: str,
    solution: dict[str, Any],
    feedback_templates: dict[str, Any],
    attempts_remaining: int,
) -> dict[str, Any]:
    """Build Graves's mentor feedback (template-based)."""
    quality = _determine_quality(score)
    reasoning_preview = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
    analysis = f"You accused {accused_id} because: {reasoning_preview}"
    fallacies_detailed = _build_fallacies_detailed(fallacies, feedback_templates)
    praise = _generate_praise(score, correct, fallacies)
    critique = _generate_critique(correct, accused_id, solution, fallacies)
    hint = _generate_adaptive_hint(attempts_remaining, solution) if not correct else None

    return {
        "analysis": analysis,
        "fallacies_detected": fallacies_detailed,
        "score": score,
        "quality": quality,
        "critique": critique,
        "praise": praise,
        "hint": hint,
    }


def _determine_quality(score: int) -> str:
    """Determine quality level from score."""
    if score >= 90:
        return "excellent"
    elif score >= 75:
        return "good"
    elif score >= 60:
        return "fair"
    elif score >= 40:
        return "poor"
    else:
        return "failing"


def _build_fallacies_detailed(
    fallacies: list[str],
    feedback_templates: dict[str, Any],
) -> list[dict[str, str]]:
    """Build detailed fallacy list with descriptions."""
    fd = feedback_templates.get("fallacies", {})
    return [
        {
            "name": n,
            "description": fd.get(n, {}).get("description", f"Logical fallacy: {n}"),
            "example": fd.get(n, {}).get("example", ""),
        }
        for n in fallacies
    ]


def _generate_praise(score: int, correct: bool, fallacies: list[str]) -> str:
    """Generate praise for what player did well (Graves-style conditional)."""
    if score >= 90:
        return "Outstanding. This is what I expect from a competent Lantern Inspector."
    elif score >= 75:
        return "Good work. You cited relevant evidence and reasoned clearly."
    elif score >= 60:
        return "Adequate. You got there, but barely."
    elif correct and len(fallacies) == 0:
        return "Correct, but I've seen better reasoning from probationary recruits."
    elif correct:
        return "Right answer, wrong path. Don't rely on luck."
    else:
        return "Try harder. This is embarrassing."


def _generate_critique(
    correct: bool,
    accused_id: str,
    solution: dict[str, Any],
    fallacies: list[str],
) -> str:
    """Generate critique for what player missed (Graves-style harsh)."""
    if correct and len(fallacies) == 0:
        return "Acceptable work. But don't let it go to your head."
    elif correct:
        fallacy_str = ", ".join(fallacies) if fallacies else "some logical gaps"
        return (
            f"Right answer, WRONG reasoning. Your logic was riddled with "
            f"{fallacy_str}. Sloppy work, Lantern Inspector."
        )
    else:
        actual_culprit = solution.get("culprit", "unknown")
        key_evidence = solution.get("key_evidence", [])
        evidence_str = ", ".join(key_evidence) if key_evidence else "key evidence"
        return (
            f"WRONG. You accused {accused_id} when the evidence clearly points to "
            f"{actual_culprit}. Did you even LOOK at the {evidence_str}? Pathetic."
        )


def _generate_adaptive_hint(attempts_remaining: int, solution: dict[str, Any]) -> str:
    """Generate adaptive hint based on attempts remaining."""
    key_evidence = solution.get("key_evidence", [])
    method = solution.get("method", "unknown method")

    if attempts_remaining >= 7:
        return "Think harder. Review all evidence carefully."
    elif attempts_remaining >= 4:
        evidence_hint = ", ".join(key_evidence[:2]) if key_evidence else "key evidence"
        return f"Focus on the key evidence: {evidence_hint}."
    else:
        return f"The {method.lower()} points directly to the culprit. Check who had the capability."


def get_wrong_suspect_response(
    accused_id: str,
    feedback_templates: dict[str, Any],
    attempts_remaining: int,
) -> str | None:
    """Get pre-written response for wrong suspect accusation."""
    wrong_suspect_responses = feedback_templates.get("wrong_suspect_responses", {})
    response_template = wrong_suspect_responses.get(accused_id.lower())

    if response_template:
        return response_template.format(attempts_remaining=attempts_remaining)
    return None


def build_graves_roast_prompt(
    player_reasoning: str,
    accused_suspect: str,
    actual_culprit: str,  # Keep param for signature compat but don't use
    evidence_cited: list[str],
    key_evidence_missed: list[str],
    fallacies: list[str],
    score: int,
    briefing_context: dict[str, Any] | None = None,
    enhanced_solution: dict[str, Any] | None = None,
    victim: dict[str, Any] | None = None,
    timeline: list[dict[str, Any]] | None = None,
    attempt_number: int = 1,
    evaluator_result: dict[str, Any] | None = None,
    language: str = "en",
) -> str:
    """Build LLM prompt for Graves's harsh feedback on incorrect verdict."""
    cited_str = ", ".join(evidence_cited) if evidence_cited else "None"
    missed_str = ", ".join(key_evidence_missed) if key_evidence_missed else "None"

    context_section = _build_case_context_section(briefing_context, "DO NOT reveal culprit")
    enhanced_section = _build_enhanced_section(enhanced_solution, include_mistakes=True)
    victim_section = _build_victim_section(victim)
    evaluator_section = _build_evaluator_section(evaluator_result)

    timeline_section = ""
    if timeline:
        timeline_section = f"""
TIMELINE (for evaluating alibi arguments):
{format_timeline(timeline)}
"""

    return f"""You are Inspector Alastor Graves, a gruff veteran Lantern Inspector trainer.
{context_section}{enhanced_section}{victim_section}{timeline_section}{evaluator_section}
A student submitted an INCORRECT verdict (attempt #{attempt_number}):
- Accused: {accused_suspect} (WRONG - but don't reveal who IS guilty)
- Reasoning: "{player_reasoning}"
- Evidence cited: {cited_str}
- Key evidence missed: {missed_str}
- Reasoning score: {score}/100

Your task: ROAST this verdict hard, then nudge them toward the truth without giving away the answer.

REQUIREMENTS (weave together naturally, no separate sections):
1. Mock their flawed reasoning — quote their bad logic back at them
2. If they missed key evidence, mention AT MOST 1-2 pieces they should look at — describe them naturally (e.g. "the shimmer on his skin" not "dual_shimmer"). NEVER list all missed evidence.
3. ONE subtle hint toward the correct path (without naming the culprit)
4. ONE rationality principle woven in naturally
5. If attempt >= 3, show growing exasperation — they keep making the same mistakes

RULES:
- 3-4 sentences MAXIMUM. Punchy, direct, savage.
- NEVER list evidence as tags or IDs. Always refer to evidence naturally in prose (e.g. "the torn letter" not "torn_letter").
- NEVER include examples, parenthetical notes, meta-commentary, or instructions.
- Use paragraph breaks (double newlines) for readability.
- Stay fully in character as Graves. Output ONLY Graves's words.{get_language_instruction(language)}"""


def build_graves_praise_prompt(
    player_reasoning: str,
    accused_suspect: str,
    evidence_cited: list[str],
    score: int,
    fallacies: list[str],
    briefing_context: dict[str, Any] | None = None,
    enhanced_solution: dict[str, Any] | None = None,
    victim: dict[str, Any] | None = None,
    attempt_number: int = 1,
    evaluator_result: dict[str, Any] | None = None,
    language: str = "en",
) -> str:
    """Build LLM prompt for Graves's feedback on correct verdict."""
    cited_str = ", ".join(evidence_cited) if evidence_cited else "None"

    context_section = _build_case_context_section(briefing_context, "for natural reference")
    enhanced_section = _build_enhanced_section(enhanced_solution)
    victim_section = _build_victim_section(victim, "acknowledge justice if appropriate")
    evaluator_section = _build_evaluator_section(
        evaluator_result, include_strengths=True, trust_note="— trust the score"
    )

    return f"""You are Inspector Alastor Graves, a gruff veteran Lantern Inspector trainer.
{context_section}{enhanced_section}{victim_section}{evaluator_section}
A student just submitted a CORRECT verdict (attempt #{attempt_number}):
- Accused: {accused_suspect} (CORRECT)
- Reasoning: "{player_reasoning}"
- Evidence cited: {cited_str}
- Reasoning score: {score}/100

Your task: Acknowledge they got it right, then calibrate your tone to the score.

TONE TIERS (follow the score STRICTLY):
- Score >=85: Grudging respect. Briefly acknowledge solid detective work, but stay gruff. Never gush. "Not bad" is high praise from Graves.
- Score 70-84: Gruff acknowledgment with mild criticism. They did decent work but missed some things. Point out what they could improve. A nod, not praise.
- Score 50-69: Dismissive. They stumbled into the right answer with weak reasoning. Mock the sloppy parts. Dare them to try again and prove it wasn't a fluke.
- Score <50: Savage. They got LUCKY and you know it. Tear apart every weak argument. Taunt them to try again with actual evidence-backed reasoning.
- If attempt >= 3: Show growing impatience that they keep submitting weak reasoning.

RULES:
- 3-4 sentences MAXIMUM. Punchy, direct.
- Weave in ONE rationality principle naturally — don't name-drop it like a textbook.
- If the evaluator found specific weaknesses or fallacies, address those — don't invent different ones.
- If score < 85 and they missed key evidence, mention AT MOST 1-2 pieces naturally (e.g. "the frost pattern" not "frost_pattern"). NEVER dump a list of evidence IDs.
- For scores < 70, end with a challenge to retry — make it about pride, not instructions.
- NEVER include examples, parenthetical notes, meta-commentary, or instructions to the player.
- NEVER start with "Good work" or praise if score < 85.
- Use paragraph breaks (double newlines) for readability.
- Stay fully in character as Graves. Output ONLY Graves's words.{get_language_instruction(language)}"""


async def build_graves_feedback_llm(
    correct: bool,
    score: int,
    fallacies: list[str],
    reasoning: str,
    accused_id: str,
    solution: dict[str, Any],
    attempts_remaining: int,
    evidence_cited: list[str],
    feedback_templates: dict[str, Any],
    case_id: str = "case_001",
    api_key: str | None = None,
    model: str | None = None,
    evaluator_result: dict[str, Any] | None = None,
    language: str = "en",
) -> str:
    """Generate Graves's feedback via Claude Haiku with template fallback."""
    try:
        from src.api.llm_client import get_client
        from src.case_store.loader import load_case

        try:
            case_data = load_case(case_id)
            case_section = case_data.get("case", case_data)
            briefing_context = case_section.get("briefing_context", {})
        except Exception:
            briefing_context = {}

        attempt_number = 10 - attempts_remaining + 1

        if correct:
            prompt = build_graves_praise_prompt(
                player_reasoning=reasoning,
                accused_suspect=accused_id,
                evidence_cited=evidence_cited,
                score=score,
                fallacies=fallacies,
                briefing_context=briefing_context,
                attempt_number=attempt_number,
                evaluator_result=evaluator_result,
                language=language,
            )
        else:
            critical_evidence = solution.get("critical_evidence", [])
            if not critical_evidence:
                critical_evidence = solution.get("key_evidence", [])
            cited_set = set(evidence_cited)
            key_missed = [e for e in critical_evidence if e not in cited_set]
            actual_culprit = solution.get("culprit", "unknown")

            prompt = build_graves_roast_prompt(
                player_reasoning=reasoning,
                accused_suspect=accused_id,
                actual_culprit=actual_culprit,
                evidence_cited=evidence_cited,
                key_evidence_missed=key_missed,
                fallacies=fallacies,
                score=score,
                briefing_context=briefing_context,
                attempt_number=attempt_number,
                evaluator_result=evaluator_result,
                language=language,
            )

        client = get_client()
        response = await client.get_response(
            prompt,
            max_tokens=200,
            api_key=api_key,
            model=model,
        )
        return response.strip()

    except Exception as e:
        import traceback

        logger.error(f"LLM feedback failed ({type(e).__name__}): {e}\n{traceback.format_exc()}")
        quality = _determine_quality(score)
        if not correct:
            culprit = solution.get("culprit", "unknown")
            preview = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
            return (
                f"Incorrect, recruit. The actual culprit was {culprit}. "
                f"You accused {accused_id} with reasoning: '{preview}'. "
                f"Quality: {quality}. Attempts remaining: {attempts_remaining}."
            )
        return (
            f"Correct. You identified {accused_id} as guilty. "
            f"Reasoning quality: {quality}. Good work."
        )
