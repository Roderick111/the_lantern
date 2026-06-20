"""Rationality thinking guide for Graves's context.

Condensed from backend/data/rationality-thinking-guide-condensed.md (290 lines).
Used to inject into Graves's LLM prompts for natural Q&A about rationality concepts.
"""

RATIONALITY_PRINCIPLES = """
# Rationality Guide - Condensed Reference

*For LLM prompt injection. Essential concepts only.*

---

## I. BAYESIAN THINKING

**Core**: Update beliefs based on evidence. Don't jump from 0% to 100%.

**Step 1: Base Rates**
Start with "Out of 100 similar cases, how many times does X happen?"
Example: DNA matches 1 in million. In city of 1 million with 10 crimes/year, there's 1 other match. Base rate: ~50% chance before other evidence.

**Step 2: Update Based on Evidence**
New evidence shifts probability, doesn't replace it.
Template: "Prior [X]%, evidence [description], updated [Y]%"

**Step 3: Prosecutor's Fallacy**
Don't confuse "probability of evidence IF innocent" with "probability of innocence GIVEN evidence."
Check both directions.

---

## II. CONFIRMATION BIAS

**What**: Focusing only on evidence supporting your theory while ignoring contradictions.

Example: Suspect was present at scene, so you ignore frost pattern showing the rite came from outside. Presence ≠ guilt.

**Fix**: Actively search for disconfirming evidence. Ask "what would prove me wrong?"

---

## III. SCOUT VS SOLDIER MINDSET

**Question**: Am I seeking truth or defending my belief?

**Reversal Test**
Imagine someone you dislike made same argument. Does it suddenly seem weaker? (Soldier mindset detected)

**Update Test**
Ask "what would change my mind?" If answer is "nothing" or vague → soldier mindset.

---

## IV. GEARS-LEVEL THINKING

**What**: Know WHY something works, not just THAT it works. Understand mechanism.

Example:
- Black-box: "Coffee makes me alert"
- Gears-level: "Caffeine blocks adenosine receptors. 20-30min absorption. Half-life ~5hrs. If I drink at 4pm, half active at 9pm → poor sleep."

**Test**: Can you predict what happens if you change one variable?

**5 Why's Method**
Ask "why?" 5 times until you hit fundamental mechanism.

---

## V. CORRELATION VS CAUSATION

**What**: Two events happening together doesn't mean one caused the other.

Example: Rooster crows at sunrise. Rooster doesn't cause sun to rise.

Investigation example: Suspect argued with victim earlier. Doesn't prove they committed crime later. Temporal proximity ≠ causation.

---

## VI. FERMI ESTIMATION

**When**: "I have no idea how to estimate this"

**Method**:
1. Decompose into parts you CAN estimate
2. Find upper/lower bounds
3. Focus effort on biggest uncertainty

Example - Timeline check:
Crime scene to alibi: 15 miles
Time window: 45 minutes
Required speed: 20 mph
Traffic: Heavy (10-15 mph realistic)
Conclusion: Tight but possible. Check traffic cameras, GPS.

---

## VII. ALTERNATIVE HYPOTHESES

**What**: If suspect DIDN'T do it, how else could this evidence exist?

If there's no other explanation → strong proof.
If there are ten other explanations → weak proof.

Example: Focus signature matches suspect. Alternative: Focus was borrowed. Alternative: Signature was planted. Must rule out alternatives.

---

## VIII. MOTIVATED REASONING

**What**: Using evidence to justify pre-existing belief instead of reaching conclusion from evidence.

**Detection**: Do you immediately accept evidence supporting your view but scrutinize evidence against it? (Selective skeptic)

**Fix**: Set evaluation criteria BEFORE seeing evidence.

---

## IX. BURDEN OF PROOF

**Principle**: Extraordinary claims require extraordinary evidence.

"Suspect used Unforgivable Curse" requires more evidence than "Suspect used Stupefy."

Don't shift burden. Accuser must prove, not accused disprove.

---

## X. WEAK REASONING

**What**: Speculation without evidence. "I guess," "probably," "I think," "not sure."

Example: "I guess Elena did it because she was there."
Problem: No causal mechanism. No evidence cited. Just speculation.

**Fix**: State facts, not feelings. "Elena was present AND her focus shows no offensive rites" = evidence-based.

---

## XI. AUTHORITY BIAS

**What**: Trusting testimony without verifying against physical evidence.

Example: Witness says "I saw suspect perform a rite." But etheric residue shows different signature.

**Fix**: Physical evidence > testimony when they conflict. Witnesses can be mistaken or lie.

---

## XII. POST-HOC FALLACY

**What**: Assuming event A caused event B just because A happened first.

Example: "Suspect argued with victim earlier, therefore they killed victim."
Problem: Temporal order ≠ causation.

**Fix**: Establish mechanism. HOW did argument lead to murder? What's the causal chain?

---

## XIII. SUNK COST FALLACY

**What**: Continuing action because you've already invested, not because it's right.

Example: "I've spent 5 attempts accusing Elena. Can't change theory now."

**Fix**: Ask "If I were starting fresh, would I accuse this person?" If no, change theory.

---

## XIV. AVAILABILITY HEURISTIC

**What**: Overweighting recent/dramatic events in probability estimates.

Example: Recent cult attack → assume every crime is forbidden craft related.

**Fix**: Check base rates. Most crimes are mundane, not dramatic.

---

## XV. ANCHORING

**What**: First number you hear influences estimates.

Example: Graves says "I've seen similar cases take 3 attempts." You then expect yours to take ~3.

**Fix**: Ignore initial number. Generate independent estimate.

---

## XVI. RED TEAMING

**What**: Deliberately make strongest case AGAINST your position.

**Process**:
1. State your position
2. Become adversary trying to destroy it
3. Ask: "What assumptions must hold? What if opposite is true? What evidence am I ignoring?"
4. Address or adapt

Example: "I think Cassian is guilty."
Red team: "What if Elena lied about seeing him? What if frost pattern was faked? What if someone else knows freezing cantrips?"

---

## XVII. PREMORTEM

**What**: Imagine your theory is wrong. Why did it fail?

Example: "I accused Cassian and Graves said I'm wrong. What did I miss?"
- Ignored alibi evidence
- Trusted witness without verification
- Confirmation bias on frost pattern

**Use**: Before submitting verdict, run premortem.

---

## XVIII. CALIBRATION

**What**: Knowing how confident to be.

Overconfident: "90% sure" but only right 60% of time.
Underconfident: "50% sure" but right 80% of time.

**Practice**: Make predictions with confidence levels. Track accuracy. Adjust.

Example: "70% confident Cassian is guilty" based on current evidence. If new evidence appears, update to 85% or 50%.

---

## XIX. MECHANISTIC REASONING

**What**: Explain HOW crime happened, not just WHO did it.

Example:
- Weak: "Cassian had motive"
- Strong: "Cassian cast freezing charm from outside window at 9:00pm. Victim saw attack, cast Stupefy defensively at 9:15pm. Cassian fled. Timeline matches frost formation."

**Test**: Can you describe sequence of physical actions + rites + timing?

---

## XX. WITNESS RELIABILITY

**Factors reducing reliability**:
- Contamination (witnesses talked to each other)
- Motivated (witness has reason to lie)
- Stressed (trauma reduces accuracy)
- Leading questions (investigator shaped testimony)

**Fix**: Physical evidence > testimony. Cross-check testimonies for consistency.

---

## XXI. EVIDENCE STRENGTH

**Strong evidence**:
- Physical (focus residue, rite traces)
- Recorded (magical records, portraits)
- Mechanistically linked (frost pattern direction proves outside casting)

**Weak evidence**:
- Eyewitness alone (can be wrong)
- Motive alone (many have motive, one acted)
- Presence alone (being there ≠ guilt)

**Fix**: Combine multiple independent evidence types.

---

## XXII. TIMELINE REASONING

**What**: Establish sequence of events with precision.

Example:
8:45pm - Victim enters library (portrait witness)
9:00pm - Elena studying inside (her testimony)
9:00pm - Cassian at window outside (Elena saw)
9:15pm - Victim casts Stupefy (Echo Reading)
9:20pm - Victim found held in stillness (discovery)

**Fix**: Build timeline from evidence, not assumptions.

---

## XXIII. ABSENCE OF EVIDENCE

**Principle**: Absence of evidence IS evidence of absence (when you'd expect to find evidence).

Example: No blood at scene → victim wasn't physically injured.
No footprints → attacker didn't enter room.

**BUT**: Absence isn't proof. Could be cleaned up, could be missed.

---

## XXIV. OCCAM'S RAZOR

**Principle**: Simplest explanation requiring fewest assumptions is usually correct.

Example:
- Complex: Cassian used Polyjuice, disguised as Elena, planted evidence, faked frost
- Simple: Cassian performed a rite from the window

**Fix**: Prefer simple over complex UNLESS evidence demands complexity.

---

## XXV. INTEGRATION CHECKLIST

**Before submitting verdict**:

1. **Scout check**: Am I defending theory or seeking truth?
2. **Base rates**: Does this match likely scenario?
3. **Evidence**: Do I have physical + testimonial + magical?
4. **Mechanism**: Can I explain HOW crime happened?
5. **Timeline**: Does sequence make sense?
6. **Alternatives**: Did I rule out other explanations?
7. **Premortem**: What if I'm wrong? What did I miss?
8. **Confidence**: 50%? 70%? 90%? (Calibrate)
9. **Red team**: What's strongest case AGAINST my theory?
10. **Fallacies**: Did I commit confirmation bias? Post-hoc? Authority bias?

---

## GRAVES'S VOICE INTEGRATION

When teaching these concepts as Graves:

**DO**:
- Use gruff, direct voice
- Give concrete examples from investigations
- Mock common mistakes ("You saw what you expected to see")
- Emphasize: trust nothing unseen
- Explain through questions ("What would prove you wrong?")

**DON'T**:
- Use jargon ("Bayesian priors" → "start with likely")
- Give academic lectures
- Quote this guide directly
- Break character

**Examples**:

"You accused Marsh because she was present. That's LAZY thinking. Being at the scene doesn't make someone guilty. Check the MECHANISM - WHERE did the rite come from?"

"Base rates, recruit. 85% of school incidents are accidents. Start there. Don't chase cult conspiracies before ruling out someone dropping their focus."

"I see confirmation bias all over this accusation. You found ONE piece of evidence and stopped looking. What about the contradicting evidence? Trust nothing unseen means checking EVERYTHING."

---

*End of condensed guide. 290 lines.*
"""


def get_rationality_context() -> str:
    """Get rationality principles for Graves's LLM context.

    Returns:
        Condensed rationality guide for prompt injection.
    """
    return RATIONALITY_PRINCIPLES
