# Case Design Guide - Victorian occult detective Investigation Game

Complete guide to creating professional-quality cases using the enhanced YAML schema (Phase 5.5+).

---

## Quick Start

1. Copy `docs/case-files/case_template.yaml` to `backend/src/case_store/case_NNN.yaml`
2. Follow the [REQUIRED] field annotations
3. Reference `CASE_002_RESTRICTED_SECTION.md` for complete example
4. Test: Drop file in case_store/, restart server or call GET /api/cases

**World frame:** Every case is a **live 1890s investigation** — present-tense crime scenes, living witnesses. Do not frame cases as training exercises, historical reconstructions, or closed-file replays. See `docs/game-design/WORLD_AND_NARRATIVE.md`.

---

## Design Philosophy: Story First, Rationality Second

**The core principle**: This game succeeds when it tells compelling character stories through investigation. If stories are boring and linear, players won't engage—and they won't learn rationality principles even if we teach them perfectly.

### Priority Hierarchy

**1. CHARACTER STORIES (First Priority)**
- Investigate to reveal interesting, human stories about complex characters
- Each witness should have wants, fears, moral dilemmas that emerge through dialogue
- Evidence should reveal character depth, not just plot mechanics
- Player should care about the people involved, not just "solving the puzzle"

**Example**: Elena isn't just "the student who found the body." She's a loyal friend secretly teaching Rowan defensive spells after he was bullied. Her badge at the crime scene creates conflict: tell the truth and get Rowan expelled, or withhold details and look guilty herself.

**2. MYSTERY STRUCTURE (Second Priority)**
- Create solid, logically structured narratives with ambiguity and contradictions
- Multiple suspects with plausible motives
- Evidence that creates hypothesis shifts (initial theory → red herring → truth)
- Timeline and physical evidence as the keys to resolution
- Avoid linear "collect evidence against obvious suspect" gameplay

**Example**: Players suspect Elena (found body, badge at scene) → consider Wisp (theft conflict, "D." note) → evidence shifts to Cassian (Thief's Candle letter, timeline, witnesses). Each phase feels earned, not arbitrary.

**3. TEACHING RATIONALITY (Third Priority)**
- Rationality concepts emerge naturally from solving complex mysteries
- Don't sacrifice story quality to force a teaching moment
- Let players discover biases by making mistakes, then show them why
- Use Graves's feedback to highlight fallacies AFTER verdict, not during investigation

**Example**: Players accusing Elena teaches "don't assume person who found body is guilty" more effectively than lecturing about availability bias upfront.

### What Makes a Case Engaging

**✅ Good Mystery Design:**
- Three witnesses with different secrets (only one is the culprit)
- Red herring evidence that initially points to wrong suspect
- Ambiguous notes or evidence (e.g., "D." could mean Cassian or Wisp)
- Timeline that eliminates suspects with alibis
- Physical evidence that shifts theories (Thief's Candle proves magic was used)
- Moral complexity (accident vs intentional, reckless vs evil)

**❌ Boring Mystery Design:**
- One obvious suspect, all evidence points to them
- Linear evidence collection (find clue A → B → C → solved)
- No contradictions or hypothesis shifts
- Witnesses have no depth beyond "helpful" or "lying"
- Solution is clear from the briefing

### Balancing Story and Structure

**Technical constraints** (must preserve for code compatibility):
- Evidence IDs must be unique strings (e.g., `hidden_note`, `torn_letter`)
- Witness IDs must match YAML keys exactly
- Solution.culprit must reference a witness ID
- Timeline uses consistent time format
- Trigger phrases must be lowercase strings

**Creative freedom** (tell your story here):
- Victim humanization (who they were, what was lost)
- Witness psychology (wants, fears, moral_complexity)
- Evidence significance (why it matters narratively)
- Secrets and lies (what characters hide, when they reveal)
- Post-verdict confrontation dialogue
- Teaching moments in wrong verdict responses

### Case Design Checklist

Before finalizing your case, ask:

1. **Character Stories**: Do witnesses have compelling internal conflicts beyond "helpful witness" or "lying suspect"?
2. **Mystery Flow**: Will players form multiple hypotheses, or is the solution obvious from the start?
3. **Evidence Ambiguity**: Is there at least one piece of evidence that could support multiple theories?
4. **Timeline**: Does the timeline eliminate at least one plausible suspect with an alibi?
5. **Moral Complexity**: Is the culprit purely evil, or do they have understandable (if not excusable) motivations?
6. **Teaching Integration**: Do rationality concepts emerge naturally from mistakes, or are they forced?
7. **World Context**: Does the case feel grounded in a specific era with atmospheric details?
8. **Witness Reactions**: Does every key evidence piece have per-witness reactions showing different interpretations?
9. **Atmospheric Evidence**: Does each location have 1-2 world-building evidence pieces (strength 10-20)?
10. **Evidence Descriptions**: Are descriptions raw data only — no self-interpreting conclusions?
11. **Spoiler-Free Descriptions**: Does every witness have a `description` (player sees) separate from `personality` (AI only)?
12. **Solution Detail**: Are `deductions_required`, `common_mistakes`, and `fallacies_to_catch` filled in?
13. **Prose Formatting**: Is dialogue/prose using `>` and bullet lists using `|`?

If you answered "no" to questions 1-4, your case may be too linear. Revise to add complexity.

---

## YAML Formatting Rules

Two scalar types matter for case content:

| Syntax | Behavior | Use For |
|--------|----------|---------|
| `>` (folded) | Joins lines into paragraphs | Prose, dialogue, descriptions, aftermath |
| `\|` (literal) | Preserves line breaks exactly | Bullet lists, structured content |

```yaml
# Prose — use > (folded):
- speaker: "graves"
  text: >
    You followed the evidence where it led, not where your
    assumptions wanted it to go. That takes discipline.

# Bullet lists — use | (literal):
teaching_moment: |
  - The timeline eliminates Elena
  - The dual shimmer proves two attackers
```

**Dialogue**: The `speaker` field identifies who talks — don't prefix text with "GRAVES:", "DOBBY:", etc.

---

## Mechanics (Phase 5.5+)

### World Context

**Purpose**: Ground the narrator in a specific era and atmosphere. The narrator weaves this naturally into descriptions — it is NOT dumped verbatim to the player.

```yaml
case:
  world_context: |
    It is the students' second year at Blackwood Collegiate. The The Hollow Below has been opened. Mr. Crankshaw's cat, Morrigan, was found held in stillness weeks ago. uninitiated-born students live in fear.

    Cassian, Elena, and the other students are twelve or thirteen years old — children dealing with forces beyond their understanding.

    Wisp is still enslaved by the Thorne family. He has no legal rights.
```

**Guidelines**:
- Establish the era: what year, what larger events are happening
- State character ages explicitly — this shapes how the narrator writes dialogue and reactions
- Include social/political dynamics (bound familiar slavery, Board of Governors, school fear)
- Keep it to 3-5 short paragraphs — this is injected into every narrator prompt
- Write full sentences on single lines — YAML `|` blocks preserve line breaks literally

**Used by**: Narrator LLM (atmospheric grounding in every investigation response)

---

### Witness Reactions on Evidence

**Purpose**: When a player **presents evidence** to a witness during interrogation, the witness reacts with a one-line interpretation. Different witnesses interpret the same evidence differently based on their knowledge, bias, and involvement.

```yaml
hidden_evidence:
  - id: "frost_pattern"
    name: "Unusual Frost Pattern"
    # ... other fields ...
    witness_reactions:
      elena: "The center scorch is unusual. Freezing cantrips don't leave burns. This looks like combustion followed by rapid cold expansion."
      cassian: "*changes subject quickly* Probably a malfunctioning ward. Old library, old magic."
      whitmore: "Cursed artifact discharge. Several cursed objects produce frost like this — Thief's Candle, Cursed Opal, Winter's Grip amulet."
      wisp: "Wisp does not know about frost. Wisp was not there. *does not look at the evidence*"
```

**Guidelines**:
- Write in character voice — first person, with emotional markers (`*pauses*`, `*voice breaks*`)
- Each witness should interpret differently: one provides analysis, one deflects, one accidentally reveals knowledge, one overreacts
- Reactions are injected into the LLM prompt as a **mandatory instruction** — the witness MUST convey the reaction's substance
- Keep reactions to 1-2 sentences. The LLM adds body language and emotion on top
- The guilty party's reactions should be subtly off — too dismissive, too specific, or physically uncomfortable

**Used by**: Witness LLM (evidence presentation prompt), injected as `== YOUR REACTION (you MUST convey this) ==`

---

### Discovery Guidance (Semantic Discovery)

**Purpose**: Replace rigid keyword triggers with semantic descriptions that the narrator LLM interprets. This allows natural player phrasing to reveal evidence without needing exact trigger words.

```yaml
# OLD (deprecated — still supported but not recommended):
triggers:
  - "search desk"
  - "look under desk"
  - "examine desk closely"

# NEW (preferred):
discovery_guidance: "Revealed when player searches the reading desk, examines papers, or uses Unveil on the desk area."
```

**Guidelines**:
- Describe the player actions that should reveal this evidence in plain English
- Include both physical actions ("searches the floor") and magical actions ("casts Identify Substance on the body")
- The narrator LLM uses this semantically — "investigate the table" matches "searches the reading desk"
- Be specific about location — "examines the desk" should not reveal floor evidence

**Used by**: Narrator LLM (evidence revelation decisions)

---

### Atmospheric Evidence

**Purpose**: Low-strength evidence that builds the world without advancing the mystery. Gives the narrator more to describe, creates realistic noise, and makes investigation feel like exploring a living world rather than a puzzle with only plot-relevant pieces.

```yaml
- id: "prefect_patrol_notes"
  name: "Prefect Patrol Schedule"
  type: "documentary"
  discovery_guidance: "Revealed when player examines the corridor notice board or asks about security."
  description: |
    A patrol schedule showing reduced coverage due to The Hollow Below fears. Half the prefects refuse night patrol. Library wing coverage suspended after 9 PM.
  tag: "[EVIDENCE: prefect_patrol_notes]"
  significance: "Security gaps explain how multiple people accessed the area undetected."
  strength: 15        # Very low — world-building
  points_to: []       # Empty — no suspects implicated
  witness_reactions:
    elena: "Half the prefects refusing patrol? No wonder the corridor was empty."
    cassian: "If there were proper patrols, none of this would have... *stops himself*"
```

**Design principles**:
- **strength 10-20**: Low enough to not distract from real evidence, high enough to feel like a find
- **points_to: []**: Never implicates a suspect directly
- **Every location should have 1-2**: Prevents "empty room" feeling after main evidence is found
- **Types that work well**: administrative records, staff notes, patrol schedules, student complaints, confiscation logs, duty rosters, graffiti, damaged infrastructure
- **Connect to world_context**: Atmospheric evidence should reinforce the era (Lodge succession fears, bound familiar conditions, security failures)
- **Witness reactions reveal character, not case facts**: Elena gets angry about bound familiar rights, Cassian dismisses concerns, etc.

---

### Approximate Timelines

**Purpose**: Narrative-style timing feels more natural than minute-by-minute precision. Precise timestamps belong in in-world documents (kitchen logs, library slips), not in the meta-timeline.

```yaml
# BAD — minute-by-minute feels clinical:
- time: "9:47 PM"
  event: "Elena enters Sealed Stacks"
- time: "9:50 PM"
  event: "Cassian leaves common room"
- time: "9:55 PM"
  event: "Cassian enters Sealed Stacks"

# GOOD — narrative timing, group related events:
- time: "Late evening, shortly before curfew"
  event: "Elena enters the Sealed Stacks to research her defense. Around the same time, Cassian leaves the Iron Lodge common room carrying the wrapped Thief's Candle."
  evidence: ["elena_book_slip", "student_testimony"]
```

**Guidelines**:
- Use phrases: "three days before", "late afternoon", "shortly before curfew", "around ten o'clock", "moments after", "shortly after"
- Group related events that happen close together into single entries
- Precise times can still appear in evidence descriptions (they're in-world documents)
- 8-12 timeline entries is ideal — fewer than minute-by-minute but enough to reconstruct events

---

### Briefing Gameplay Instructions

**Purpose**: The briefing synopsis should include beginner-friendly, in-character instructions on how to play. Use markdown bold/italic for emphasis — the frontend renders these with `renderInlineMarkdown`.

```yaml
synopsis: |
  Professor Aldric Vane found held in stillness in the Sealed Stacks. Evidence of etheric discharge.

  **How to investigate:** Type what you want to do — *"examine the frost patterns"*, *"cast Identify Substance on the body"*, *"search the desk"*. Be specific. The more precise your actions, the more you'll find.

  **Talk to witnesses** by selecting them from the sidebar. Ask questions, build trust, and **present evidence** to see how they react — different people interpret the same clue differently.

  When you're ready, **submit your verdict**. But don't rush — the obvious answer is rarely the right one.
```

**Guidelines**:
- Keep instructions immersive — they're part of the dossier, not a help screen
- Use bold for action types, italic for example commands
- 3-4 instruction lines max — enough to orient beginners without overwhelming

---

## Field Usage Guidelines

### Victim Humanization

**Purpose**: Make players care emotionally about solving the case

**name** (required if victim section present):
- Full name, proper capitalization
- Example: "Helena Blackwood", "Theodore Nott"

**age** (required if victim section present):
- Age descriptor that gives context
- Good: "Fourth-year Candlewick", "First-year Ashford", "Sixth-year transfer student"
- Bad: "14 years old" (too clinical)

**humanization** (required if victim section present):
- 2-3 sentences creating emotional connection
- Include: What they were like, what made them memorable, what was lost
- Good: "You remember her from the library—always buried in focuslore texts, muttering about core resonance frequencies. Brilliant, obsessive, the kind of student who'd sneak into the Sealed Stacks for research long after curfew. Someone silenced that curious mind permanently."
- Bad: "A student who was killed." (too vague)

**memorable_trait** (required if victim section present):
- One distinctive detail that sticks
- Examples: "Focuslore obsessive", "Always wore mismatched socks", "Hummed while studying"

**cause_of_death** (required for complete cases):
- **Critical**: First word becomes crime type shown to all witnesses automatically
- Format: "[Simple action] [by/with/from] [details]"
- Examples:
  - "Paralytic binding curse from cursed object discharge" → Witnesses see "Paralytic binding"
  - "Crushed by a massive bookshelf (staged as accident)" → Witnesses see "Crushed"
  - "Stabbed with enchanted letter opener" → Witnesses see "Stabbed"
- Bad: "Died" (too vague), "Killed" (not specific)
- Used by: Witness context (automatic extraction), Graves (verdict evaluation)

**time_of_death** (optional, recommended):
- Precise time for timeline coordination
- Example: "10:05 PM"
- Used by: Graves (verdict evaluation), Timeline cross-referencing

---

### Evidence Enhancement

**discovery_guidance** (required, replaces legacy `triggers`):
- Semantic description of how the player discovers this evidence
- The narrator LLM interprets this — no need for exact keyword matching
- Example: `"Revealed when player searches the reading desk, examines papers, or uses Unveil on the desk area."`
- Used by: Narrator LLM (decides when to reveal evidence)

**significance** (optional, recommended):
- One sentence: WHY this evidence matters to the case
- Example: "Proves Levitation Cantrip was used at high power"
- Used by: Narrator (subtle emphasis), Graves (feedback), Matthew (commentary)

**strength** (optional, recommended):
- 0-100 rating of evidence quality
- Calibration:
  - 100: Critical, case-solving evidence (levitation scorch marks, erased log)
  - 80-90: Strong evidence that implicates/eliminates (missing focus, shelf marks)
  - 60-70: Moderate evidence (witness testimony, circumstantial)
  - 40-50: Weak evidence (presence, opportunity)
  - 20-30: Red herring or misleading (Sterling's scarf)
  - 10-20: Atmospheric/world-building (patrol notes, duty rosters)
- Used by: Matthew (targets strong evidence), Graves (feedback quality)

**points_to** (optional, recommended):
- List of suspect IDs this evidence implicates
- Empty list `[]` for atmospheric evidence
- Example: `["professor_morraine", "marcus_sterling"]`
- Used by: Graves (evaluating player reasoning)

**contradicts** (optional, recommended):
- List of suspect IDs or theory names this evidence exonerates
- Example: `["crankshaw_guilty", "adrian_guilty", "accident_theory"]`
- Used by: Graves (catching player mistakes)

**witness_reactions** (optional, recommended):
- Per-witness one-line reactions when evidence is presented during interrogation
- Each witness interprets the same evidence differently
- Written in character voice with emotional markers
- Example:
  ```yaml
  witness_reactions:
    elena: "Two layers of magic? That's... the blue-white is artifact discharge. But the yellowish-green — I've read about that color."
    cassian: "*genuinely confused* Two colors? I only used one artifact. What's the second one?"
    wisp: "*tries to leave the conversation* Wisp does not understand initiate magic."
  ```
- Used by: Witness LLM (evidence presentation prompt)

---

### Witness Description vs Personality

Every witness needs two text fields:

- **`description`** — shown to the player. Spoiler-free: role, house, observable traits. No guilt or inner conflict.
- **`personality`** — used by the AI for roleplay. Full inner state, lying tells, emotional reactions. Spoilers are expected here.

```yaml
- id: "wisp"
  name: "Wisp"
  description: >
    A bound familiar who serves the Thorne family. Speaks in third person, wrings
    his hands constantly. Admitted to stealing nightshade from Professor Vane's stores.
  personality: |
    Still enslaved to the Thorne family. His guilt about Professor Vane is overwhelming
    but he cannot confess. When lying: physically pained, may hit himself.
    When confronted with evidence: silence, then self-harm attempt.
```

If `description` is missing, the system falls back to showing `personality` — but this leaks spoilers, so always include both.

---

### Witness Psychological Depth

**wants** (required for complete cases):
- What the witness is trying to achieve in this situation
- Drives their behavior during interrogation
- Good: "Help investigation without getting friends in trouble", "Protect house reputation while cooperating"
- Bad: "Tell the truth" (too generic)
- Used by: Witness LLM (shapes responses based on trust level)

**fears** (required for complete cases):
- What stops them from helping fully
- Creates internal conflict
- Good: "Retaliation from Iron Lodges if she names names", "Expulsion so close to graduation"
- Bad: "Being caught lying" (too generic)
- Used by: Witness LLM (low trust = fear dominates, high trust = trust overcomes fear)

**moral_complexity** (required for complete cases):
- 2-4 sentences describing internal conflict
- Why they're torn between competing values
- What makes them human, not just an NPC
- Good: "Hannah saw something important but doesn't want to betray Marcus, who helped her pass Alchemy last year. She's not malicious—just caught between loyalty to someone who was kind to her and doing what's right. The guilt of staying silent wars with fear of social consequences."
- Bad: "She's conflicted." (too vague)
- Used by: Witness LLM (informs roleplay nuance), Graves (feedback on witness handling)

**secrets** (optional):
- Hidden information witness may reveal during interrogation
- **Phase 6.5+: Context-aware revelation system**
  - Innocent people cooperate at 50+ trust, but secrets reveal based on personal stakes
  - LLM receives trust-tiered guidance specific to each secret's risk
  - Separation: general cooperation (want to help) vs secret revelation (what's at stake)
- Structure:
  ```yaml
  secrets:
    - id: "secret_identifier"
      trigger: "trust>70 OR evidence:some_evidence"  # Legacy field, kept for reference
      risk_type: "protective"  # [REQUIRED] What makes this hard to reveal
      risk_level: "high"       # [OPTIONAL] low | medium | high
      why_hiding: "Rowan could be expelled if authorities find out"  # [REQUIRED] Context for LLM
      text: |
        What witness says when revealing this secret.
        Written in character voice (first person, 2-4 sentences).
        Include emotional authenticity and hesitation if appropriate.
      keywords:  # [OPTIONAL] Multi-word phrases for detection
        - "tutoring rowan defensive"
        - "blonde hair running"
        - "hand of glory cursed"
  ```

**Risk Types** (required for Phase 6.5+):
- `none` - Neutral info, no personal cost (e.g., "I saw someone at 8pm")
  - Shared freely at 50+ trust, if asked at <50
- `protective` - Protects someone witness cares about (friend, student, vulnerable person)
  - Deflect <50, hint 50-70, reveal with caveats 70+
  - Example: "Rowan could be expelled", "Wisp could be killed by masters"
- `self_incriminating` - Witness did something wrong/illegal
  - Lie/deny <50, deflect hard 50-75, reluctant admission 75+
  - Example: "This connects me to the crime", "I could go to Dreadmoor Penitentiary"
- `emotional` - Deeply personal, shameful, vulnerable
  - Avoid topic <65, share with difficulty 65+
  - Example: "My deepest shame", "The truth about my past"

**Why Hiding** (required for Phase 6.5+):
- One sentence explaining **why this is hard to reveal**
- Used by LLM to understand emotional/social stakes
- Examples:
  - Protective: "Rowan could be expelled if this gets out"
  - Self-incriminating: "This confession means Dreadmoor Penitentiary or expulsion"
  - Emotional: "I've never told anyone about my father's betrayal"

#### Secret Detection System

Secrets are automatically detected using **two complementary methods**:

**Method 1: Denial-Aware Keyword Matching** (Phase 6.5+)
- Player explicitly searches for specific phrases during Mnemonic Delving
- **Context-aware**: Rejects keywords in denial context
- Checks 40 characters before keyword for denial patterns: "don't", "never", "not", "nothing about", etc.
- Examples:
  - ✅ "Father sent me a hand of glory" → Detected (affirmative)
  - ❌ "I don't know anything about a hand of glory" → Not detected (denial)
  - ✅ "I was teaching Rowan defensive magic" → Detected (affirmative)
  - ❌ "I wasn't teaching Rowan anything" → Not detected (denial)

**Method 2: 5-Consecutive-Word Matching** (Phase 6.5+, upgraded from 4)
- Detects when LLM naturally reveals secret during interrogation/evidence presentation
- Uses sliding window algorithm: checks if any 5 consecutive words in witness response ALL appear in secret text
- Filters common stopwords to prevent false positives
- **Stricter threshold** (5 words vs 4) reduces false positives
- Example: Secret "I was teaching Rowan defensive magic in secret" → Witness says "Fine! I confess - teaching Rowan defensive magic in secret was wrong" → Secret revealed (5+ consecutive words)

**Both methods work across all 3 contexts:**
1. **Regular Interrogation** - Witness naturally reveals during questioning
2. **Evidence Presentation** - Witness reacts to evidence with revealing response
3. **Mnemonic Delving Spell** - Player searches witness's mind with specific intent

---

#### Keywords Field (Optional)

**Purpose**: Enables targeted secret discovery via Mnemonic Delving spell.

**Best Practices**:
- ✅ **Use multi-word phrases** (3-4 words): `"tutoring rowan defensive"`, `"hand of glory cursed"`
- ✅ **Specific and unique**: `"cassian thorne returning"`, `"wisp stole ingredients"`
- ✅ **Match secret content**: Extract key phrases directly from secret text
- ❌ **Avoid single common words**: `"was"`, `"there"`, `"magic"` (causes false positives)
- ❌ **Avoid generic terms**: `"person"`, `"thing"`, `"something"`

**Example**:
```yaml
secrets:
  - id: "tutoring_a_peer"
    trigger: "trust>65"
    text: |
      I was there to research spells for... for Rowan. I've been teaching him
      defensive magic in secret. The Iron Lodges have been hexing him in corridors.
    keywords:  # Optional but recommended for Mnemonic Delving targeting
      - "tutoring rowan"           # ✅ Specific person + activity
      - "defensive magic training"   # ✅ Multi-word unique phrase
      - "secret combat lessons"      # ✅ Distinctive action
      - "iron lodge hexing rowan"  # ✅ Specific situation
```

**Detection Example**:
- Mnemonic Delving search: *"searching for who she's been teaching"*
  - Contains keyword `"teaching"` → ✅ Secret revealed
- Witness response: *"Fine! I was teaching Rowan defensive magic okay?"*
  - 4 consecutive words `"tutoring rowan defensive magic"` → all match secret → ✅ Secret revealed
- Witness response: *"I was just studying in the library"*
  - No keyword match, no 4-word match → ❌ Secret stays hidden

---

**Writing Guidelines**:
- Write in character voice, not clinical/robotic
- Good: "Alright. I... I saw Cassian Thorne. Running. From the Sealed Stacks. He looked absolutely terrified."
- Bad: "I observed suspect flee scene at 9:15 PM" (too clinical)
- Secrets should feel like emotional confessions, not police reports

---

### Automatic Witness Context System

**Purpose**: Every witness automatically receives basic case facts without manual configuration.

**What's Provided Automatically**:

When any witness is interrogated, the system automatically injects:

```
== CASE CONTEXT (public knowledge) ==
Victim: [victim.name]
What happened: [first word of victim.cause_of_death]
Where: [first location.name]
```

**Fields Used for Auto-Extraction**:
1. `victim.name` → Displayed as-is to all witnesses
2. `victim.cause_of_death` → First word extracted and simplified
   - "Paralytic binding curse from..." → "Paralytic binding"
   - "Crushed by a massive..." → "Crushed"
3. `locations` dict → First location's `name` field used as crime scene

**Why This Matters**:
- Everyone at Blackwood Collegiate would know these basic facts
- Professor Whitmore doesn't need "investigating Professor Vane" in her `knowledge` - she already knows
- Witnesses can reference the victim by name naturally
- Keeps witness `knowledge` focused on their unique observations

**Implementation** (routes.py:1457-1472):
```python
victim_info = case_data.get("victim", {})
cause_of_death = victim_info.get("cause_of_death", "")
crime_type = cause_of_death.split()[0]  # First word only

case_context = {
    "victim_name": victim_info.get("name", ""),
    "crime_type": crime_type,
    "location": first_location.get("name", ""),
}
```

**Best Practices**:

✅ **DO use witness.knowledge for**:
- Specific personal observations: "Caught Cassian at 11:00 PM trying to re-enter library"
- What they personally did: "Secured Cassian's belongings, found letter"
- Sensory details: "Heard voices before crash"
- Relationships: "Cassian is in my Alchemy class"

❌ **DON'T use witness.knowledge for**:
- Victim's identity ("Investigating Professor Vane's paralytic binding") - auto-provided
- Crime location ("Crime happened in library") - auto-provided
- Crime type ("Looking into the attack") - auto-provided

**Example**:

```yaml
# Case YAML structure
victim:
  name: "Professor Aldric Vane"
  cause_of_death: "Paralytic binding curse from cursed object discharge"

locations:
  library:
    name: "Blackwood Collegiate Library - Sealed Stacks"
    # ... rest of location config

# Witness definition
witnesses:
  - id: "whitmore"
    name: "Professor Minerva Whitmore"
    knowledge:
      # ✅ SPECIFIC observations only
      - "Caught Cassian trying to re-enter the library at 11:00 PM"
      - "Cassian claimed he 'forgot a book' despite crime scene tape"
      - "Secured Cassian's belongings, found Magnus's letter"

# What Professor Whitmore's LLM prompt receives:
# == CASE CONTEXT (public knowledge) ==
# Victim: Professor Aldric Vane
# What happened: Paralytic binding
# Where: Blackwood Collegiate Library - Sealed Stacks
#
# == YOUR KNOWLEDGE ==
# - Caught Cassian trying to re-enter the library at 11:00 PM
# - Cassian claimed he 'forgot a book' despite crime scene tape
# - Secured Cassian's belongings, found Magnus's letter
```

---

### Briefing Structure

**Purpose**: Provide Inspector Graves's case introduction and pre-investigation teaching question.

**Structure**:
```yaml
briefing:
  case_id: "case_001"  # [REQUIRED] Must match case.id

  dossier:  # [REQUIRED] Structured case summary
    title: "The Sealed Stacks"
    victim: "Professor Aldric Vane (Alchemy Master)"
    location: "Blackwood Collegiate Library - Sealed Stacks"
    time: "22:00 (Found)"
    status: "Held in stillness / St. Mungo's"
    synopsis: |
      Brief description of the case. What happened?
      Who are the suspects? What's the player's job?

  teaching_question:  # [REQUIRED] Pre-investigation rationality question
    prompt: "Out of 100 school deaths ruled 'accidents,' how many actually ARE accidents?"
    concept_summary: "Base Rates: Start with likely scenarios, not dramatic theories."
    choices:  # 2-4 answer choices
      - id: "choice_a"
        text: "25% - Most are forbidden craft cover-ups"
        response: |
          *Inspector Graves's magical eye spins wildly*

          GRAVES: "Paranoia. Trust nothing unseen is good, but assume
          conspiracy everywhere and you'll chase shadows while the real
          culprit walks away. 85% are accidents. Use logic."

      - id: "choice_b"
        text: "85% - Most are just reckless students"
        response: |
          *Inspector Graves nods approval*

          GRAVES: "Correct. Start with the most likely explanation:
          incompetence or accident. Then let the evidence prove
          otherwise. That's how you avoid chasing ghosts."

  rationality_concept: "base_rates"  # [REQUIRED] Concept ID
  concept_description: "Start with likely scenarios (base rates), not dramatic theories."

  transition: |  # [OPTIONAL] Text after briefing, before investigation
    *Inspector Graves's magical eye spins*

    TRUST NOTHING UNSEEN, recruit. Now investigate.
```

**Guidelines**:
- **case_id**: Must match the top-level `case.id` exactly
- **dossier.title**: Case title (matches case.title)
- **dossier.victim**: Name and role (e.g., "Helena Blackwood (Top Arithmancy Student)")
- **dossier.synopsis**: 2-4 sentences summarizing the case
- **teaching_question.prompt**: Question testing rationality concept
- **teaching_question.concept_summary**: One-line summary of the concept
- **teaching_question.choices**: 2-4 multiple choice answers with Graves's responses
- **rationality_concept**: ID like "base_rates", "hidden_variables", "confirmation_bias"
- **transition**: Optional send-off before investigation begins

**Common Teaching Concepts**:
- `base_rates` - Start with likely scenarios, not dramatic theories
- `hidden_variables` - Systems fail when something was wrong from the start
- `confirmation_bias` - Don't only look for evidence supporting your theory
- `correlation_not_causation` - Presence doesn't prove guilt

**Used by**: Briefing LLM (Graves's character), Teaching system

---

### Witness Portrait System

**Purpose**: Provide visual immersion for each character without requiring complex YAML configuration.

**Convention-Based Approach**:
The system automatically looks for portrait images based on the witness `id` defined in the YAML.

1. **File Format**: `.png`
2. **File Name**: Must match the `id` of the witness exactly (e.g., `professor_morraine.png`).
3. **Location**: `frontend/public/portraits/`

**Workflow for Designers**:
1. Generate or create a 16-bit pixel art portrait.
2. Ensure the witness ID in your `case_NNN.yaml` is something concise like `adrian_clearmont`.
3. Name your image file `adrian_clearmont.png`.
4. Drop it into `frontend/public/portraits/`.
5. The game will automatically detect and render the image in the interrogation modal.

**Graceful Fallback**:
If no image is found in the `portraits/` folder, the interface will automatically display a terminal-themed `?` placeholder. No code changes or YAML field updates are necessary to add new portraits.

---


### Timeline System

**Purpose**: Enable alibi checking and temporal reconstruction

**Structure**:
```yaml
timeline:
  - time: "Three days before the attack"
    event: "Wisp steals nightshade from Professor Vane's stores to heal Pippa"
    witnesses: []
    evidence: ["hidden_note"]

  - time: "Late evening, shortly before curfew"
    event: "Elena enters the Sealed Stacks. Around the same time, Cassian leaves carrying the wrapped artifact."
    witnesses: []
    evidence: ["elena_book_slip", "student_testimony"]

  - time: "Around ten o'clock"
    event: "Professor Vane arrives and attempts to cancel the ritual. The artifact discharges."
    witnesses: []
    evidence: ["focus_signature"]
```

**Guidelines**:
- Use **approximate narrative timing** ("late evening", "shortly before curfew", "moments after") — not minute-by-minute
- Group related events that happen close together into single entries
- Precise timestamps can appear in **evidence descriptions** (in-world documents like kitchen logs)
- Order chronologically
- Include crime timing explicitly
- Mark witnesses who can confirm each event
- Link to supporting evidence
- Aim for 8-12 entries total

**Used by**: Graves (alibi evaluation), Narrator (timeline references)

---

### Enhanced Solution Fields

**deductions_required** (optional, recommended):
- List of logical steps player must make
- Example:
  ```yaml
  - "Levitation scorch marks prove Levitation Cantrip used"
  - "High power eliminates weak casters (Adrian) and non-magical (Mr. Crankshaw)"
  - "Erased log entry at 10:15 PM connects to Morraine's presence"
  ```

**correct_reasoning_requires** (optional, recommended):
- What player must understand conceptually
- Example:
  ```yaml
  - "Base rates: Most accidents are accidents (start with likely)"
  - "Timeline eliminates suspects with alibis"
  - "Magical capability limits suspect pool"
  ```

**common_mistakes** (optional, recommended):
- Errors players are likely to make
- Structure:
  ```yaml
  - error: "Accuse Sterling"
    reason: "Obvious suspect, strong motive, scarf at scene"
    why_wrong: "Timeline proves he left before 9 PM"
  ```

**fallacies_to_catch** (optional, recommended):
- Logical fallacies to teach
- Structure:
  ```yaml
  - fallacy: "confirmation_bias"
    example: "Player locks onto Sterling, ignores timeline evidence"
  ```

**Used by**: Graves (verdict evaluation, educational feedback)

---

### Case Identity Fields

**crime_type** (optional, recommended):
- One of: "murder", "theft", "corruption", "assault", "conspiracy"
- Sets tone and teaching focus
- Used by: Narrator (atmosphere)

**hook** (optional, recommended):
- One sentence that creates intrigue
- Goes on landing page (case.description)
- Good: "A brilliant Candlewick found dead under a collapsed bookshelf. Accident, or murder disguised?"
- Bad: "There was a death in the library." (too plain)

**twist** (optional, recommended):
- What subverts player's initial theory
- Example: "The obvious suspect (Sterling) left before the crime. The real killer never physically touched the victim—used Levitation Cantrip to stage an 'accident'."
- Used by: Narrator (foreshadowing), Graves (teaching moment)

---

## Field Requirement Levels

**[REQUIRED]**: Case won't load without it
- case.id, case.title, case.difficulty
- victim.name (if victim section present)
- witness.name, witness.description, witness.personality
- evidence.discovery_guidance (replaces legacy `triggers`)
- solution.culprit

**[REQUIRED for complete cases]**: Needed for professional quality
- victim.age, victim.humanization, victim.memorable_trait
- witness.wants, witness.fears, witness.moral_complexity
- evidence.witness_reactions (per-witness interpretations)
- case.world_context (era/atmosphere for narrator)
- solution.deductions_required, solution.common_mistakes, solution.fallacies_to_catch

**[OPTIONAL but recommended]**: Enhances case quality significantly
- evidence.significance, evidence.strength, evidence.points_to
- atmospheric evidence (1-2 per location, strength 10-20)
- timeline section (approximate timing)
- solution.deductions_required, solution.common_mistakes
- case.crime_type, case.hook, case.twist
- briefing synopsis with gameplay instructions

**[OPTIONAL]**: Nice to have, not essential
- victim.time_of_death, victim.cause_of_death
- evidence.contradicts
- post_verdict.wrong_suspects (per-suspect responses)

---

## Where Fields Are Used

| Field | Player Sees | AI Uses For |
|-------|-------------|-------------|
| witness.description | ✅ Witness modal | — |
| witness.personality | ❌ Never | Roleplay |
| wants/fears/moral_complexity | ❌ | Witness roleplay, Graves feedback |
| victim.humanization | ❌ | Narrator atmosphere, Graves context |
| evidence.witness_reactions | ❌ | Witness evidence reactions |
| evidence.discovery_guidance | ❌ | Narrator decides when to reveal |
| world_context | ❌ | Narrator atmosphere |
| solution fields | ❌ | Verdict scoring, Graves feedback |
| timeline | ❌ | Narrator references, alibi checking |

---

## Examples

See `docs/case-files/CASE_002_RESTRICTED_SECTION.md` for complete implementation of all Phase 5.5 fields.

### Evidence Enhancement Example

```yaml
hidden_evidence:
  # Case evidence — advances the mystery
  - id: "levitation_scorch_marks"
    name: "Levitation Scorch Marks"
    type: "magical"
    discovery_guidance: "Revealed when player looks up at the ceiling, examines the area above the bookshelf, or casts Unveil on the ceiling."
    description: |
      Faint scorch marks on ceiling above bookshelf. Signature of high-powered Levitation Cantrip.
    tag: "[EVIDENCE: levitation_scorch_marks]"
    significance: "Proves Levitation Cantrip used at high power"
    strength: 100
    points_to: ["professor_morraine", "marcus_sterling"]
    contradicts: ["crankshaw_guilty", "adrian_guilty", "accident_theory"]
    witness_reactions:
      hannah_abbott: "Scorch marks? On the ceiling? That's... that's a levitation spell. A strong one."
      marcus_sterling: "Could be anything. Old castle, old magic. Scorch marks happen."
      professor_morraine: "*slight pause* Interesting. The power required for that would be considerable."

  # Atmospheric evidence — builds the world
  - id: "library_complaints_log"
    name: "Student Complaints Log"
    type: "documentary"
    discovery_guidance: "Revealed when player examines the library desk, searches administrative records."
    description: |
      A complaints log showing students reporting strange noises from the Sealed Stacks over the past week. Three separate complaints, all dismissed by Miss Hawthorne as "overactive imaginations."
    tag: "[EVIDENCE: library_complaints_log]"
    significance: "Shows the Sealed Stacks had unusual activity before the crime. World context."
    strength: 10
    points_to: []
    witness_reactions:
      hannah_abbott: "Students heard things? And no one investigated? That's... concerning."
```

### Witness Psychological Depth Example

```yaml
witnesses:
  - id: "hannah_abbott"
    name: "Hannah Abbott"
    personality: "Nervous, people-pleaser, conflict-averse"
    background: "Ashford third-year, friends with both victim and suspect"

    # Phase 5.5 enhancements
    wants: "Help investigation without betraying friend Marcus"
    fears: "Retaliation from Iron Lodges, being seen as snitch"
    moral_complexity: |
      Hannah saw something critical but doesn't want to betray Marcus,
      who helped her pass Alchemy last year. She's torn between loyalty
      to a friend and duty to justice. Her people-pleasing nature makes
      this internal conflict especially painful.

    knowledge:
      - "Saw Marcus near library around 10 PM"
    secrets:
      - id: "saw_marcus_with_focus"
        trigger: "trust>65"
        risk_type: "protective"
        risk_level: "high"
        why_hiding: "Marcus helped me pass Alchemy - betraying him feels like breaking a debt of loyalty"
        text: |
          I... I saw Marcus's focus. It was glowing—faintly, but I know what
          I saw. He was near the Sealed Stacks entrance around 10 PM.
          I didn't want to believe it, but the light was unmistakable.
        keywords:
          - "marcus focus glowing"
          - "restricted section entrance"
          - "ten pm saw"
```

### Timeline Example

```yaml
timeline:
  - time: "Earlier that evening"
    event: "Mr. Crankshaw patrols past library entrance. Helena enters the Sealed Stacks shortly after."
    witnesses: ["argus_crankshaw", "miss_hawthorne"]
    evidence: ["checkout_log"]

  - time: "Around ten o'clock"
    event: "A loud crash is heard from the Sealed Stacks. Multiple students hear it from the corridor."
    witnesses: ["hannah_abbott", "adrian_clearmont"]
    evidence: ["bookshelf_collapse"]

  - time: "Shortly after"
    event: "Adrian finds Helena under the collapsed bookshelf. Mr. Crankshaw arrives and secures the scene."
    witnesses: ["adrian_clearmont", "argus_crankshaw"]
    evidence: []
```

### Enhanced Solution Example

```yaml
solution:
  culprit: "professor_morraine"
  method: "Used Levitation Cantrip to topple bookshelf"
  motive: "Helena discovered Morraine's use of forbidden craft for research"
  key_evidence:
    - "levitation_scorch_marks"
    - "erased_log_entry"

  # Phase 5.5 enhancements
  deductions_required:
    - "Scorch marks prove levitation spell used (not accident)"
    - "Shelf positioned deliberately before being dropped"
    - "Helena's missing focus suggests killer took it"

  correct_reasoning_requires:
    - "Evidence of magical involvement (scorch marks)"
    - "Proof of premeditation (shelf positioning)"
    - "Alibi verification (Morraine's lie)"

  common_mistakes:
    - error: "Accusing Marcus Sterling"
      reason: "Presence near scene + hostile relationship with victim"
      why_wrong: "Alibi confirmed by multiple witnesses, no magical skill for levitation"

  fallacies_to_catch:
    - fallacy: "confirmation_bias"
      example: "Focusing only on Marcus's hostility, ignoring contradictory alibi evidence"
```

---

## Testing Your Case

1. Drop YAML in `backend/src/case_store/`
2. Restart server or call `GET /api/cases`
3. Check logs for validation warnings
4. Test case discovery: Landing page shows new case
5. Test evidence discovery: Triggers work
6. Test witness depth: wants/fears affect responses
7. Test verdict: Graves uses enhanced solution fields

---

## Common Pitfalls

❌ **Vague humanization**: "A student who died" → ✅ "You remember her from the library—always buried in focuslore texts..."

❌ **Generic wants/fears**: "Tell the truth" / "Being caught" → ✅ "Help investigation without betraying friend Marcus" / "Retaliation from Iron Lodges"

❌ **Strength not calibrated**: Guessing numbers → ✅ Use calibration scale (100=critical, 80=strong, 50=moderate)

❌ **Missing timeline**: Can't check alibis → ✅ Include key events with witnesses who can confirm

❌ **No common_mistakes**: Generic Graves feedback → ✅ Specific per-suspect wrong verdict responses

---

## Field Summary Table

| Field | Required | Purpose |
|-------|----------|---------|
| victim.name | Yes | Identify victim |
| victim.humanization | Recommended | Emotional connection |
| witness.description | Yes | Spoiler-free character intro (player sees this) |
| witness.personality | Yes | Full roleplay profile (AI only) |
| witness.wants/fears | Recommended | Drive witness behavior |
| witness.moral_complexity | Recommended | Internal conflict |
| evidence.discovery_guidance | Yes | How player finds this evidence |
| evidence.significance | Recommended | Why this evidence matters |
| evidence.strength | Recommended | Quality rating (0-100) |
| evidence.witness_reactions | Recommended | Per-witness evidence interpretation |
| case.world_context | Recommended | Era/atmosphere grounding |
| timeline | Optional | Alibi checking |
| solution.deductions_required | Recommended | Logical steps to solve the case |
| solution.common_mistakes | Recommended | Predicted wrong accusations |
| solution.fallacies_to_catch | Recommended | Logical fallacies to teach |
| case.hook | Optional | Landing page intrigue |
| case.twist | Optional | Theory subversion |

---

**Version**: 2.1
**Last Updated**: 2026-04-09
**For**: Case designers creating professional-quality mysteries
