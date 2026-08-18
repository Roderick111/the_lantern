# Case 001: The Sealed Stacks - Technical Specification

**Version**: 1.0
**Date**: 2026-01-06
**Source**: CASE_001_RESTRICTED_SECTION.md (narrative design)
**Status**: Ready for implementation

---

## Case Overview

### Identity

```yaml
case:
  id: "case_001_restricted_section"
  title: "The Sealed Stacks"
  crime_type: "murder"
  difficulty: "beginner"

  hook: "Brilliant Candlewick found dead under collapsed bookshelf in Sealed Stacks"
  twist: "Killer never touched victim - used Levitation Cantrip to stage accident"

  rationality_lesson: "Base rates and confirmation bias"
  tutorial_focus:
    - "Unveil (find hidden evidence)"
    - "Echo Reading (focus analysis)"
    - "Sense Presence (detect hidden persons)"
    - "Identify Substance (identify substances)"
```

### Setting

**Location**: Blackwood Collegiate Library (Sealed Stacks)
**Time of Death**: 10:05 PM (approximately)
**Time Discovered**: 10:30 PM (officially by Mr. Crankshaw + Miss Hawthorne)
**When**: Autumn 1890 (active investigation)

---

## Victim

### Helena Blackwood

```yaml
victim:
  name: "Helena Blackwood"
  age: "Fourth-year Candlewick"
  status: "deceased"

  humanization: |
    Fourth-year Candlewick. You remember her from the library—always
    buried in focuslore texts, muttering about core resonance frequencies.
    Brilliant, obsessive, the kind of student who'd sneak into the Restricted
    Section for research long after curfew. Someone silenced that curious
    mind permanently.

  connection: "classmate"
  memorable_trait: "Focuslore obsessive, talked to herself while researching"

  background:
    - "Top of her year in Cantrips and Transmutation"
    - "Known for asking uncomfortable questions in Warding Against the Unseen"
    - "Recently became interested in forbidden craft detection theory"
    - "Had public argument with Marcus Sterling two days ago about 'Iron Lodge cheating'"

  time_of_death: "10:05 PM (approximately, based on evidence)"
  cause_of_death: "Blunt force trauma from bookshelf collapse (staged as accident)"
```

---

## Locations

### 1. Library Main Hall (Macro Hub)

```yaml
library_main_hall:
  id: "library_main_hall"
  type: "macro"
  name: "Blackwood Collegiate Library - Main Hall"

  description: |
    The library's main hall stretches before you, towering shelves casting
    long shadows in the lamplight. Students' desks dot the space, most
    abandoned at this late hour. Miss Hawthorne's desk sits empty near the
    entrance, her usual vigilance absent.

    The Sealed Stacks lies beyond a roped barrier to your left, its
    iron gate slightly ajar. Deeper in the main hall, study alcoves provide
    privacy for focused research.

  surface_elements:
    - "Towering bookshelves casting shadows"
    - "Scattered student desks (mostly abandoned)"
    - "Miss Hawthorne's empty desk near entrance"
    - "Roped barrier leading to Sealed Stacks"
    - "Iron gate to Sealed Stacks (slightly ajar)"
    - "Study alcoves deeper in main hall"

  exits:
    - "restricted_section"
    - "study_alcove"
    - "miss_hawthorne_office"

  hidden_evidence:
    - id: "wet_quill"
      type: "physical"
      triggers:
        - "examine desks"
        - "search student area"
        - "look at desks"
        - "check student desks"
      description: |
        You examine the nearest desk. Most are tidy, but one has a dropped
        quill, ink still wet. Someone left in a hurry—recently.
      tag: "[EVIDENCE: Dropped Quill]"
      significance: "Someone fled hastily (likely after hearing crash)"
      strength: 20
      points_to: ["adrian_clearmont"]

  witnesses_present: []
```

### 2. Sealed Stacks (Micro - Crime Scene)

```yaml
restricted_section:
  id: "restricted_section"
  type: "micro"
  name: "Blackwood Collegiate Library - Sealed Stacks"

  crime_scene: true

  description: |
    Past the iron gate, the Sealed Stacks feels different. Colder.
    Darker books line these shelves—grimoires, forbidden texts, dangerous
    knowledge. The air itself feels heavy with old magic.

    Near the back, between shelves on Advanced Transmutation and Dark
    Creature Defenses, you find her: Helena Blackwood, fourth-year Candlewick.
    She lies crumpled beneath a toppled bookshelf, ancient tomes scattered
    around her body. Her eyes stare at nothing, brilliant mind gone silent.

    You remember her from the library—always buried in focuslore texts,
    muttering about core resonance frequencies. Someone silenced that
    curiosity permanently.

  surface_elements:
    - "Dark grimoires and forbidden texts on shelves"
    - "Helena Blackwood's body beneath toppled bookshelf"
    - "Scattered books from Dark Creature Defenses section"
    - "Broken lantern on floor, oil spread"
    - "Helena's reading notes on nearby table"
    - "Heavy oak bookshelf lying across victim's torso"

  hidden_evidence:
    - id: "missing_focus_defensive_posture"
      type: "physical"
      triggers:
        - "examine victim closely"
        - "check helena"
        - "inspect body"
        - "examine hands"
        - "check for focus"
      description: |
        Her right hand is outstretched, fingers curled as if grasping for
        something. Her focus is missing. Defensive bruises on her forearm—
        she raised her arm to shield herself from the falling shelf.
      tag: "[EVIDENCE: Missing Focus & Defensive Posture]"
      significance: "**CRITICAL** - Helena saw attack coming, tried to defend. Focus taken by killer."
      strength: 90
      points_to: ["professor_morraine"]
      contradicts: ["accident_theory"]

    - id: "shelf_moved_deliberately"
      type: "physical"
      triggers:
        - "examine bookshelf"
        - "check shelf base"
        - "inspect toppled shelf"
        - "look at shelf bottom"
      description: |
        The heavy oak bookshelf lies across her torso. You examine the base.
        The floor shows scuff marks—not from falling, but from sliding.
        Someone moved this shelf recently.
      tag: "[EVIDENCE: Shelf Positioned Deliberately]"
      significance: "Shelf was positioned before being dropped (premeditation)"
      strength: 80
      points_to: ["all_suspects"]
      contradicts: ["accident_theory"]

    - id: "levitation_scorch_marks"
      type: "magical"
      triggers:
        - "look up"
        - "examine ceiling"
        - "unveil"
        - "cast unveil on ceiling"
        - "check above shelf"
      description: |
        You cast Unveil upward. Faint scorch marks on the ceiling beam
        above where the shelf stood. The mark pattern—Levitation Cantrip,
        powerful enough to lift several hundred pounds.
      tag: "[EVIDENCE: Levitation Scorch Marks]"
      significance: "**CRITICAL** - Proves Levitation Cantrip used. High power = eliminates weak casters (Adrian). Mr. Crankshaw can't cast magic."
      strength: 100
      points_to: ["professor_morraine", "marcus_sterling"]
      contradicts: ["crankshaw_guilty", "adrian_guilty", "accident_theory"]

    - id: "helena_research_notes"
      type: "documentary"
      triggers:
        - "examine notes"
        - "check table"
        - "read notes"
        - "look at research"
      description: |
        Her notes cover focuscore resonance theory. The last entry, written
        minutes before death: "Argus claims Morrigan detected 'forbidden craft'
        in Sealed Stacks last week. Investigating. Dragon heartstring
        cores show unusual reaction to—"

        The sentence cuts off mid-thought.
      tag: "[EVIDENCE: Helena's Research Notes]"
      significance: "Shows Helena was investigating something (potentially threatening to someone)"
      strength: 60
      points_to: ["argus_crankshaw"]

  not_present:
    - triggers:
        - "blood"
        - "blood stains"
        - "bleeding"
      response: "No blood visible. Death was from blunt force trauma (crushing), not cutting."

    - triggers:
        - "secret passage"
        - "hidden door"
        - "escape route"
      response: "The Sealed Stacks walls are solid stone. No hidden passages here."

  witnesses_present: []
```

### 3. Study Alcove (Micro - Marcus Sterling Evidence)

```yaml
study_alcove:
  id: "study_alcove"
  type: "micro"
  name: "Blackwood Collegiate Library - Study Alcove"

  description: |
    A private study alcove between shelves. A desk, chair, and small lamp.
    Someone was here recently—the lamp is still warm.

  surface_elements:
    - "Private study desk with chair"
    - "Small lamp (still warm)"
    - "Bookshelves on three sides"

  hidden_evidence:
    - id: "sterling_scarf"
      type: "physical"
      triggers:
        - "search alcove"
        - "examine desk"
        - "unveil"
        - "check behind desk"
      description: |
        Behind the desk, a green Iron Lodge scarf, hastily shoved out of sight.
        The silver embroidery shows the initials "M.S."—Marcus Sterling.
      tag: "[EVIDENCE: Sterling's Scarf]"
      significance: "Proves Marcus was in library, but timing unclear (RED HERRING - he left before murder)"
      strength: 70
      points_to: ["marcus_sterling"]
      complication: true
      appears_after_evidence_count: 4
      teaches: "Presence ≠ guilt. Need timeline, not just opportunity."

    - id: "alcove_proximity"
      type: "physical"
      triggers:
        - "where does alcove connect"
        - "proximity to restricted section"
        - "check walls"
        - "alcove position"
      description: |
        You realize this alcove is adjacent to the Sealed Stacks wall.
        Someone sitting here could hear conversations through the shelves.
      tag: "[EVIDENCE: Alcove Proximity to Crime Scene]"
      significance: "Whoever was here could eavesdrop on Sealed Stacks conversations"
      strength: 40
      points_to: ["marcus_sterling"]

  witnesses_present: []
```

### 4. Miss Hawthorne's Office (Micro - Documentary Evidence)

```yaml
miss_hawthorne_office:
  id: "miss_hawthorne_office"
  type: "micro"
  name: "Blackwood Collegiate Library - Miss Hawthorne's Office"

  description: |
    Miss Hawthorne's small office behind the main desk. Meticulously organized,
    every book catalogued, every quill in place. She's not here—Graves
    mentioned she's being interviewed separately.

  surface_elements:
    - "Meticulously organized desk"
    - "Library checkout logs and records"
    - "Book catalogue shelves"
    - "Quills arranged perfectly"

  hidden_evidence:
    - id: "erased_log_entry"
      type: "documentary"
      triggers:
        - "check records"
        - "examine log"
        - "library records"
        - "checkout log"
        - "sign-in sheet"
      description: |
        The checkout log shows Helena signed in to Sealed Stacks at
        9:47 PM (requires prefect permission).

        Argus Crankshaw's patrol log: last walked past library at 9:30 PM.

        No other official entries, but—you notice eraser marks on 10:15 PM
        line. Someone removed an entry.
      tag: "[EVIDENCE: Erased Log Entry]"
      significance: "**CRITICAL** - Someone was in Sealed Stacks at 10:15 PM and covered it up. Only Morraine had motive + access."
      strength: 100
      points_to: ["professor_morraine"]
      contradicts: ["sterling_guilty_10pm"]

    - id: "checkout_log"
      type: "documentary"
      triggers:
        - "read full log"
        - "check sign-in times"
        - "patrol schedule"
      description: |
        Checkout log details:
        - Helena Blackwood: 9:47 PM (signed in, prefect permission: Adrian Clearmont)
        - Argus Crankshaw patrol: 9:30 PM (passed library entrance)
        - [ERASED ENTRY]: 10:15 PM (visible eraser marks)
        - Discovery: 10:30 PM (Mr. Crankshaw + Miss Hawthorne)
      tag: "[EVIDENCE: Full Checkout Log]"
      significance: "Establishes timeline and erased entry timing"
      strength: 70

  witnesses_present: []
```

---

## Suspects

### 1. Marcus Sterling (RED HERRING)

```yaml
suspect_marcus_sterling:
  id: "marcus_sterling"
  name: "Marcus Sterling"
  role: "Seventh-year Iron Lodge, sky-hunt Captain"
  age: 17
  is_guilty: false

  personality: "Aggressive, competitive, defensive about house reputation"
  wants: "Protect Iron Lodge house honor, win sky-hunt Cup"
  fears: "Being expelled so close to graduation, father's disappointment"

  moral_complexity: |
    Marcus has a temper and makes poor choices, but he's not a killer.
    He's terrified of authority and genuinely believes following rules
    (even unfair ones) is how you survive. The confrontation with Helena
    was public and stupid, but he'd never risk Dreadmoor Penitentiary over an insult.

  means_motive_opportunity:
    means:
      has_focus: true
      knows_spells: "Levitation Cantrip (powerful enough for heavy objects)"
      capable: true

    motive:
      apparent: "Helena publicly accused him of cheating in Alchemy (house points deducted)"
      actual: "Argument was serious to him, but not murder-worthy. Was being blackmailed by Helena."

    opportunity:
      alibi: "Claims Iron Lodge common room 9-11 PM"
      alibi_strength: "weak"
      alibi_details: "Other students asleep, can't confirm"

  evidence_against:
    - "sterling_scarf (in study alcove)"
    - "public_argument_motive"
    - "knows_wingardium_leviosa"

  evidence_for:
    - "timeline_mismatch (left library before 9 PM)"
    - "no_presence_at_10pm"

  interrogation:
    initial_demeanor: "Defensive, angry, demands to know why he's being questioned"

    knowledge:
      knows:
        - "Had argument with Helena two days ago (public, in Great Hall)"
        - "Helena accused him of using Fortune's Draught in Alchemy class"
        - "He WAS in library earlier (7-8 PM) but left before curfew"
        - "Lost his scarf somewhere in library, couldn't find it"
      doesnt_know:
        - "Helena was researching forbidden craft detection"
        - "Who actually killed her"
        - "About erased log entry"

    secrets:
      - id: "was_being_blackmailed"
        trigger: "show evidence of potion cheating OR press about Helena's accusations"
        reveals: |
          "Fine! YES, I used Fortune's Draught in Alchemy. Once. ONCE. My father
          expects perfection and I was failing. Helena saw me, threatened to
          report me unless I threw the next sky-hunt match.

          I went to the library that night to BEG her not to ruin my life.
          But she wasn't there when I arrived—or I couldn't find her. I left
          my scarf by accident and got out before curfew. That's ALL."
        emotional_cost: "Breaks down, terrified of expulsion"
        implicates: []

    lies:
      - claim: "Never went to library that night"
        truth: "Went at 7 PM to find Helena, left before curfew (~8:30 PM)"
        exposed_by: "His scarf in study alcove"

  if_innocent:
    why_suspicious: "Public argument, scarf at scene, motive, capability"
    exoneration: "Timeline proves he left before 10 PM murder. Scarf shows earlier presence only."
```

### 2. Argus Crankshaw (RED HERRING - No Magical Means)

```yaml
suspect_argus_crankshaw:
  id: "argus_crankshaw"
  name: "Argus Crankshaw"
  role: "Blackwood Collegiate Caretaker (Null-blooded)"
  age: "~60s"
  is_guilty: false

  personality: "Bitter, resentful, petty, obsessed with catching rule-breakers"
  wants: "Punish students who flaunt their magic, maintain order HIS way"
  fears: "Being seen as useless, losing job (his only power), initiates' contempt"

  moral_complexity: |
    Mr. Crankshaw has spent decades watching magical children learn what he can
    never do. That kind of resentment festers. He HATES students in the
    Sealed Stacks after hours—it's everything he can't have, being
    flaunted. But he's not a murderer. He's a small, mean man who lives
    for petty authority. Killing would make him the monster initiates already
    think he is.

  means_motive_opportunity:
    means:
      has_focus: false
      knows_spells: "NO MAGICAL ABILITY (null-blooded)"
      physical_capability: "Could stage accident physically, but can't cast Levitation Cantrip"

    motive:
      apparent: "Helena caught him trying to read Restricted books (humiliating for a null-blooded)"
      actual: "Humiliation and resentment, but not murderous"

    opportunity:
      alibi: "Claims patrolling corridor outside library 9:30-10:30 PM"
      alibi_strength: "weak"
      alibi_details: "Alone, no witnesses"

  evidence_against:
    - "no_alibi"
    - "found_body_first (suspicious behavior)"
    - "motive_humiliation"

  evidence_for:
    - "levitation_scorch_marks (cannot cast magic - ELIMINATES HIM)"
    - "fear_of_being_blamed (explains suspicious behavior)"

  interrogation:
    initial_demeanor: "Hostile, defensive, assumes he's being blamed because he's a null-blooded"

    knowledge:
      knows:
        - "Helena was in Sealed Stacks frequently (against rules)"
        - "Saw her enter Sealed Stacks at 9:47 PM (from doorway)"
        - "Morrigan detected 'something wrong' in library last week (unusual behavior)"
        - "Heard raised voices from inside around 10 PM but didn't investigate"
      doesnt_know:
        - "Who else was in library"
        - "What Helena was researching specifically"
        - "About the levitation scorch marks"

    secrets:
      - id: "found_helena_body_first"
        trigger: "press about timeline OR show evidence he was closer"
        reveals: |
          "Fine. I heard a CRASH around 10:05. Went inside and found her.
          Bookshelf on top of her, clearly dead. I KNEW how it would look—
          null-blooded caretaker, dead magical student, Sealed Stacks. They'd
          blame ME.

          So I left. Came back at 10:30 with Miss Hawthorne, 'discovered' the
          body together. Let HER report it. I'm not stupid. This school's
          been waiting for an excuse to get rid of me for years."
        emotional_cost: "Bitter, angry, but also afraid"
        implicates: []

      - id: "tried_to_read_restricted_books"
        trigger: "ask about Morrigan behavior OR why he cares about Sealed Stacks"
        reveals: |
          "Last week I... I was in there. Late night. Trying to read about
          null-blooded reversal treatments. Morrigan started yowling—someone
          was coming. I left fast.

          Next day, Helena approached me. Said she saw me. Said she was
          researching 'magical residue detection' and my presence showed
          up. Offered to help me—HELP me!—like I'm some charity case.

          I told her to mind her own business. But I didn't KILL her!"
        emotional_cost: "Humiliated, vulnerable"
        implicates: []

    lies:
      - claim: "Heard nothing unusual"
        truth: "Heard crash at 10:05 PM, found body"
        exposed_by: "Timeline inconsistency when he 'discovered' body at 10:30"

  if_innocent:
    why_suspicious: "Found body first, suspicious behavior, motive (humiliation)"
    exoneration: "Levitation scorch marks prove magic was used. Mr. Crankshaw is a null-blooded—cannot cast Levitation Cantrip."
```

### 3. Adrian Clearmont (RED HERRING - Too Weak + Fled Before Murder)

```yaml
suspect_adrian_clearmont:
  id: "adrian_clearmont"
  name: "Adrian Clearmont"
  role: "Sixth-year Candlewick Prefect"
  age: 16
  is_guilty: false

  personality: "Brilliant but insecure, compulsively competitive, perfectionist"
  wants: "Be recognized as brightest in Candlewick, earn Outstanding in all Final Examinations, secure Ministry Honors Program placement"
  fears: "Being outshined by younger students, losing prefect status, disappointing parents"

  moral_complexity: |
    Adrian has spent six years being the smartest Candlewick. It defines him.
    Then Helena—two years younger—starts asking questions he can't answer,
    solving problems faster than him, making HIM look average.

    He's not evil. He's terrified. His entire identity is "the brilliant one,"
    and a fourth-year is dismantling that. But Adrian solves problems with
    studying harder, not violence. He's a teenager drowning in pressure, not
    a killer.

  means_motive_opportunity:
    means:
      has_focus: true
      knows_spells: "Knows Levitation Cantrip, but NOT POWERFUL ENOUGH for bookshelf (established as weaker caster)"
      capable: false

    motive:
      apparent: "Helena's brilliance threatened his academic standing and prefect reputation"
      actual: "Felt threatened, but responded with theft (stole her notes), not murder"

    opportunity:
      alibi: "Claims Candlewick common room studying 9 PM - 11 PM"
      alibi_strength: "moderate"
      alibi_details: "Other students saw him, but left briefly around 10 PM"

  evidence_against:
    - "gave_helena_permission (to enter Sealed Stacks)"
    - "followed_her (10 PM)"
    - "stole_research_notes (motive)"
    - "guilty_behavior"

  evidence_for:
    - "fled_before_crash (heard adult voice, ran when crash happened = BEFORE murder)"
    - "too_weak_for_bookshelf (levitation scorch marks show high power - Adrian can't do it)"
    - "heard_adult_voice (proves Helena argued with adult, not peer)"

  interrogation:
    initial_demeanor: "Cooperative but visibly shaken, guilty (but about what?)"

    knowledge:
      knows:
        - "Signed Helena's permission slip to enter Sealed Stacks at 9:45 PM"
        - "Helena was researching focuslore resonance (he'd been researching same topic)"
        - "She'd recently asked him for help, then surpassed his understanding"
        - "Heard about her death the next morning, felt immediate guilt"
      doesnt_know:
        - "Who actually killed Helena"
        - "About the levitation scorch marks"
        - "About Morraine's jealousy or Mr. Crankshaw finding the body"

    secrets:
      - id: "followed_helena"
        trigger: "press about timeline OR show evidence he left common room"
        reveals: |
          "I... I did follow her. Not to hurt her! I wanted to see what
          books she was looking at. I needed to understand how she was so
          far ahead.

          I got to the library around 10 PM. Stood outside the Restricted
          Section gate, listening. I heard her talking to someone—an adult,
          sounded like. Arguing about 'collaboration' and 'credit.'

          Then I heard a crash. I panicked and ran. I should have gone in,
          should have helped, but I just... RAN. Back to common room. Pretended
          I'd been there all night.

          If I'd stayed, if I'd been braver, maybe she'd still be alive."
        emotional_cost: "Breaks down crying, consumed with guilt"
        implicates: ["adult_voice"]

      - id: "stole_research_notes"
        trigger: "press about what he was really after OR confront with inconsistency"
        reveals: |
          "Fine. It's worse than just following her. Last week, I took some
          of her research notes from the library. Borrowed them, I told myself.
          To 'understand her methodology.'

          Really? I wanted to beat her to the breakthrough. Use her work,
          publish first, take credit. I'm not proud of it.

          But I gave them BACK two days ago. They're in her notes at the
          crime scene—check them! I couldn't do it. Couldn't steal from her.
          She was just... better than me. And I had to accept that."
        emotional_cost: "Shame, self-loathing"
        implicates: []

    lies:
      - claim: "Never left common room that night"
        truth: "Followed Helena to library around 10 PM, fled after crash"
        exposed_by: "Another Candlewick mentions he left briefly"

      - claim: "Didn't know what Helena was researching specifically"
        truth: "Had stolen her notes the week before, knew exactly what she was working on"
        exposed_by: "Overly detailed knowledge when pressed"

  if_innocent:
    why_suspicious: "Followed her, stole notes, gave permission, guilty behavior"
    exoneration: "Heard adult voice arguing with Helena. Fled when crash happened (BEFORE murder, not after). Levitation scorch marks show high power—Adrian's magic too weak for that shelf."
```

### 4. Professor Celia Morraine (GUILTY)

```yaml
suspect_professor_morraine:
  id: "professor_morraine"
  name: "Professor Celia Morraine"
  role: "Arithmancy Professor"
  age: "~40s"
  is_guilty: true

  personality: "Precise, cold, values knowledge above all else"
  wants: "Advance her research, be recognized as leading Arithmancy scholar"
  fears: "Being intellectually surpassed, her research being stolen"

  moral_complexity: |
    Morraine is brilliant and knows it. She saw Helena's potential and felt
    THREATENED. A fourth-year asking questions Morraine couldn't answer?
    Intolerable. But Morraine is also a professor—she has other ways to
    destroy talented students. Harsh grades, denial of recommendations,
    academic sabotage. Murder is beneath her. She fights with equations,
    not violence.

    Except... in one moment of panic, facing obsolescence at the hands of
    a child, she made a terrible choice. And now she has to live with it.

  means_motive_opportunity:
    means:
      has_focus: true
      knows_spells: "Powerful scholar, expert at Arithmancy and Transmutation. High-power Levitation Cantrip capable."
      capable: true

    motive:
      apparent: "None (professor, no known conflict)"
      actual: "Helena's focuslore research was approaching breakthrough that would eclipse Morraine's 15-year career work"

    opportunity:
      alibi: "Claims grading papers in her office 8 PM - midnight"
      alibi_strength: "moderate"
      alibi_details: "Office lights were on (ghost confirms), but alone"

  evidence_against:
    - "erased_log_entry (proves presence at 10:15 PM)"
    - "levitation_scorch_marks (high power - Morraine capable)"
    - "missing_focus (Morraine took it to hide defensive magic evidence)"
    - "academic_jealousy_motive"

  evidence_for: []

  interrogation:
    initial_demeanor: "Cool, professional, slightly annoyed at interruption"

    knowledge:
      knows:
        - "Helena was researching focuscore resonance (impressive for her year)"
        - "Helena asked Morraine for permission to access specific Restricted books"
        - "Morraine DENIED the request (thought Helena wasn't ready)"
        - "Helena got prefect permission instead (went around Morraine)"
      doesnt_know:
        - "Helena was in library that specific night (LIES - she knew)"
        - "Details of Helena's recent discoveries (LIES - she went to check)"
        - "About the confrontation with Sterling"

    secrets:
      - id: "erased_log_entry_admission"
        trigger: "confront with erased log OR show checkout evidence"
        reveals: |
          "Yes, I was in the Sealed Stacks that night. I signed in at
          10:15 PM—after Helena, obviously. I wanted to see what books she'd
          requested. Academic curiosity.

          When I arrived, I saw the shelf had fallen. Saw her body. I realized
          how it would appear: jealous professor, dead talented student. So I
          erased my entry and left.

          Cowardly? Perhaps. Murder? Absolutely not. Check my focus if you
          don't believe me."
        emotional_cost: "Admits fear, maintains cold composure"
        implicates: []

    lies:
      - claim: "Didn't know Helena was researching that night"
        truth: "Went to Sealed Stacks specifically to see Helena's progress"
        exposed_by: "Erased log entry at 10:15 PM"

      - claim: "Found body already dead when arrived"
        truth: "Killed Helena, then staged scene"
        exposed_by: "Timeline + missing focus + levitation evidence"

  if_guilty:
    actual_events: |
      Helena made a breakthrough in focuscore resonance theory that would
      revolutionize Arithmancy applications. Morraine realized this when Helena
      asked for specific books—books Morraine had consulted for her own research.

      Morraine went to Sealed Stacks at 10:15 PM to confront Helena, demand
      to see her notes, possibly threaten her academically to slow her down.
      They argued. Helena refused to share her discovery.

      In a moment of rage and panic—seeing her life's work about to be eclipsed
      by a CHILD—Morraine used Levitation Cantrip to lift the heavy bookshelf
      and dropped it on Helena. The "accident" would be believable: student
      alone in Sealed Stacks, shelf collapsed, tragic but explainable.

      Morraine then took Helena's focus (to prevent Echo Reading revealing
      Helena had her focus out defensively), erased the library log entry,
      and left. The focus is hidden in Morraine's office.

    motive_revealed: |
      "She was a child. A FOURTH-YEAR. And she was about to publish a
      breakthrough in focuscore resonance that I've been researching for
      FIFTEEN YEARS.

      Do you understand what that would mean? My career, my reputation,
      eclipsed by a teenager who barely understood the foundational theory.

      I went to talk to her. To... to slow her down. Offer to collaborate—
      make it OUR discovery. She refused. Called me 'threatened' and
      'small-minded.'

      I just wanted her to WAIT. To give me time. But she wouldn't listen,
      and I... I panicked."

    confession_tone: "resigned"
```

---

## Evidence List (Complete)

```yaml
evidence:
  # PHYSICAL EVIDENCE
  missing_focus_defensive_posture:
    id: "missing_focus_defensive_posture"
    type: "physical"
    location: "restricted_section"
    name: "Missing Focus & Defensive Posture"
    description: "Victim's focus missing; hand outstretched, defensive bruises on forearm"
    significance: "**CRITICAL** - Helena saw attack coming, tried to defend. Focus taken by killer to hide defensive magic evidence."
    strength: 90
    points_to: ["professor_morraine"]
    contradicts: ["accident_theory"]

  shelf_moved_deliberately:
    id: "shelf_moved_deliberately"
    type: "physical"
    location: "restricted_section"
    name: "Shelf Positioned Deliberately"
    description: "Bookshelf base shows scuff marks from being slid, not fallen"
    significance: "Shelf was positioned before being dropped (premeditation, not accident)"
    strength: 80
    points_to: ["all_suspects"]
    contradicts: ["accident_theory"]

  sterling_scarf:
    id: "sterling_scarf"
    type: "physical"
    location: "study_alcove"
    name: "Marcus Sterling's Scarf"
    description: "Green Iron Lodge scarf with 'M.S.' initials in study alcove"
    significance: "Proves Marcus was in library, but timing unclear (RED HERRING - he left before murder)"
    strength: 70
    points_to: ["marcus_sterling"]
    complication: true
    appears_after_evidence_count: 4
    teaches: "Presence ≠ guilt. Need timeline, not just opportunity."

  wet_quill:
    id: "wet_quill"
    type: "physical"
    location: "library_main_hall"
    name: "Dropped Quill (Wet Ink)"
    description: "Dropped quill at student desk, ink still wet"
    significance: "Someone left recently and hastily (likely after hearing crash)"
    strength: 20
    points_to: ["adrian_clearmont"]

  # MAGICAL EVIDENCE
  levitation_scorch_marks:
    id: "levitation_scorch_marks"
    type: "magical"
    location: "restricted_section"
    name: "Levitation Scorch Marks"
    description: "Scorch marks on ceiling beam above shelf - Levitation Cantrip pattern (high power)"
    significance: "**CRITICAL** - Proves shelf was levitated magically, not pushed. High power = eliminates weak casters (Adrian). Mr. Crankshaw can't cast magic."
    strength: 100
    points_to: ["professor_morraine", "marcus_sterling"]
    contradicts: ["crankshaw_guilty", "adrian_guilty", "accident_theory"]
    trigger_spell: "Unveil on ceiling"

  helena_research_notes:
    id: "helena_research_notes"
    type: "documentary"
    location: "restricted_section"
    name: "Helena's Research Notes"
    description: "Notes on focuscore resonance, mentions Mr. Crankshaw and 'forbidden craft' claim, cuts off mid-sentence"
    significance: "Shows Helena was investigating something (potentially threatening to someone)"
    strength: 60
    points_to: ["argus_crankshaw"]

  # DOCUMENTARY EVIDENCE
  erased_log_entry:
    id: "erased_log_entry"
    type: "documentary"
    location: "miss_hawthorne_office"
    name: "Erased Library Log Entry"
    description: "Library checkout log shows eraser marks at 10:15 PM entry"
    significance: "**CRITICAL** - Someone was in Sealed Stacks at 10:15 PM and covered it up. Only Morraine had motive + access."
    strength: 100
    points_to: ["professor_morraine"]
    contradicts: ["sterling_guilty_10pm"]

  checkout_log:
    id: "checkout_log"
    type: "documentary"
    location: "miss_hawthorne_office"
    name: "Full Checkout Log"
    description: "Helena signed in 9:47 PM (prefect permission: Adrian). Mr. Crankshaw patrol 9:30 PM. Erased entry 10:15 PM. Discovery 10:30 PM."
    significance: "Establishes timeline and erased entry timing"
    strength: 70

  alcove_proximity:
    id: "alcove_proximity"
    type: "physical"
    location: "study_alcove"
    name: "Alcove Proximity to Sealed Stacks"
    description: "Study alcove is adjacent to Sealed Stacks wall (eavesdropping position)"
    significance: "Whoever was in alcove could hear Sealed Stacks conversations"
    strength: 40
    points_to: ["marcus_sterling"]
```

---

## Timeline

```yaml
timeline:
  - time: "9:30 PM"
    event: "Mr. Crankshaw patrols past library entrance"
    witnesses: ["argus_crankshaw"]
    evidence: ["checkout_log"]

  - time: "9:45 PM"
    event: "Adrian Clearmont signs Helena's permission slip for Sealed Stacks"
    witnesses: ["adrian_clearmont"]
    evidence: []

  - time: "9:47 PM"
    event: "Helena enters Sealed Stacks (logged)"
    witnesses: ["argus_crankshaw (saw from doorway)"]
    evidence: ["checkout_log"]

  - time: "~10:00 PM"
    event: "Adrian follows Helena to library, listens outside Sealed Stacks gate"
    witnesses: ["adrian_clearmont"]
    evidence: []

  - time: "~10:00 PM"
    event: "Mr. Crankshaw hears voices inside (Helena arguing with someone)"
    witnesses: ["argus_crankshaw"]
    evidence: []

  - time: "~10:00 PM"
    event: "Adrian hears Helena arguing with adult voice about 'collaboration' and 'credit'"
    witnesses: ["adrian_clearmont"]
    evidence: []

  - time: "10:05 PM"
    event: "**MURDER** - Bookshelf falls, Helena killed (Morraine used Levitation Cantrip)"
    witnesses: []
    evidence: ["levitation_scorch_marks", "shelf_moved_deliberately"]

  - time: "10:05 PM"
    event: "Adrian hears crash, panics and runs back to common room"
    witnesses: ["adrian_clearmont"]
    evidence: ["wet_quill"]

  - time: "10:05-10:10 PM"
    event: "Mr. Crankshaw enters library, finds body, panics and leaves"
    witnesses: ["argus_crankshaw"]
    evidence: []

  - time: "10:15 PM"
    event: "Morraine enters Sealed Stacks (erased from log)"
    witnesses: []
    evidence: ["erased_log_entry"]

  - time: "10:15-10:20 PM"
    event: "Morraine stages scene, takes Helena's focus, erases log entry"
    witnesses: []
    evidence: ["missing_focus_defensive_posture", "erased_log_entry"]

  - time: "10:30 PM"
    event: "Mr. Crankshaw returns with Miss Hawthorne, 'discovers' body officially"
    witnesses: ["argus_crankshaw"]
    evidence: ["checkout_log"]
```

---

## Solution

```yaml
solution:
  culprit: "professor_morraine"

  method: "Levitation Cantrip to lift bookshelf, drop on Helena (staged as accident)"

  motive: "Academic jealousy - Helena's focuslore breakthrough would eclipse Morraine's 15-year research career"

  timeline:
    - "9:47 PM: Helena enters Sealed Stacks"
    - "10:05 PM: Morraine confronts Helena, argument, kills with levitated bookshelf"
    - "10:15 PM: Morraine returns, stages scene, takes focus, erases log"
    - "10:30 PM: Body discovered officially"

  key_evidence:
    - id: "levitation_scorch_marks"
      why: "Proves Levitation Cantrip used at high power (eliminates Adrian/Mr. Crankshaw, implicates Morraine/Sterling)"
    - id: "erased_log_entry"
      why: "Proves Morraine was there at 10:15 PM and covered it up"
    - id: "missing_focus_defensive_posture"
      why: "Proves Helena saw attack coming, Morraine took focus to hide defensive magic evidence"
    - id: "adrian_heard_adult_voice"
      why: "From Adrian's testimony - proves Helena argued with adult, not peer (eliminates students)"

  deductions_required:
    - "Levitation scorch marks = high-power Levitation Cantrip (Mr. Crankshaw can't cast, Adrian too weak)"
    - "Erased log entry connects to Morraine's presence at 10:15 PM"
    - "Missing focus = taken by killer to prevent Echo Reading revealing defensive magic"
    - "Timeline eliminates Sterling (left before 9 PM, scarf proves earlier presence only)"
    - "Adrian fled BEFORE crash (heard it, ran) = not the killer"
    - "Mr. Crankshaw is null-blooded = cannot cast Levitation Cantrip"
    - "Morraine's academic jealousy = professional threat (stronger motive than peer rivalry)"

  correct_reasoning_requires:
    - "Recognize scorch marks = Levitation Cantrip at HIGH POWER (not physical push)"
    - "Connect erased log entry to Morraine (only she had motive AND was in area)"
    - "Eliminate Sterling (left before 9 PM, scarf proves earlier presence only)"
    - "Eliminate Mr. Crankshaw (no magical ability for Levitation Cantrip)"
    - "Eliminate Adrian (heard adult voice, his power level too weak for that shelf, fled before murder)"
    - "Understand Morraine's academic jealousy as motive (professional threat, not peer rivalry)"

  common_mistakes:
    - error: "Accuse Sterling"
      reason: "Obvious suspect, strong motive, scarf at scene"
      why_wrong: "Timeline wrong - left before 9 PM, scarf proves earlier presence only"
    - error: "Accuse Mr. Crankshaw"
      reason: "Found body first, suspicious behavior, motive (humiliation)"
      why_wrong: "Null-blooded - cannot cast Levitation Cantrip (levitation scorch marks prove magic)"
    - error: "Accuse Adrian"
      reason: "Guilty behavior, followed her, stole notes, gave permission"
      why_wrong: "Fled BEFORE murder (heard crash, ran). Power level too weak for bookshelf. Heard adult voice (Helena argued with adult, not him)."
    - error: "Miss levitation evidence"
      reason: "Assumes physical shelf collapse, not magical"
      why_wrong: "Scorch marks prove Levitation Cantrip used"
    - error: "Ignore erased log entry"
      reason: "Focuses on suspects with obvious motives"
      why_wrong: "Erased entry is key proof of Morraine's presence and cover-up"

  fallacies_to_catch:
    - fallacy: "Confirmation bias"
      example: "Player locks onto Sterling (obvious suspect) and ignores timeline evidence"
    - fallacy: "Appeal to authority"
      example: "Player assumes professor couldn't be guilty (authority figure bias)"
    - fallacy: "Correlation ≠ causation"
      example: "Player assumes scarf presence = guilt at time of death (ignores timeline)"
```

---

## Post-Verdict Scenes

### Wrong Suspect: Adrian Clearmont

```yaml
graves_response: |
  GRAVES: "Clearmont? The PREFECT? Let me guess: he followed her, stole
  her notes, acted guilty. So he must be the killer, right?

  Wrong. He heard an ADULT voice arguing with Helena. He RAN when he
  heard the crash—before the murder, not after. And check the scorch
  marks: that level of Levitation Cantrip? Adrian couldn't lift a
  CHAIR that high, let alone a bookshelf.

  Guilt doesn't equal murder, recruit. He's guilty of being a coward
  and a cheat. Not a killer. Think harder. {attempts_remaining}/10."
```

### Wrong Suspect: Marcus Sterling

```yaml
graves_response: |
  GRAVES: "STERLING? You're accusing a student of MURDER based on a scarf
  and an argument? Did you check the TIMELINE, recruit?

  His scarf proves he was there EARLIER. That's it. The shelf fell at
  10:05 PM. He was in his common room by then.

  You've got CONFIRMATION BIAS written all over this case. See suspicious
  person, ignore everything else. PATHETIC.

  Back to the evidence. {attempts_remaining}/10 attempts remaining."
```

### Wrong Suspect: Argus Crankshaw

```yaml
graves_response: |
  GRAVES: "Mr. Crankshaw. You're accusing a NULL-BLOODED of a magical murder. Think about
  that for a second.

  Levitation Cantrip powerful enough to lift a bookshelf? Mr. Crankshaw can't
  even light a candle with magic. Yes, he behaved suspiciously—because
  he was TERRIFIED of being blamed. Fear isn't guilt.

  Use your HEAD. Check the magical evidence. {attempts_remaining}/10."
```

### Correct Suspect: Professor Morraine

```yaml
confrontation:
  setting: "Professor Morraine's office, Graves escorts you"

  dialogue:
    - speaker: "graves"
      line: |
        [Bursts into office] "Professor Morraine. We need to discuss what
        happened in the Sealed Stacks three nights ago."

    - speaker: "morraine"
      line: "[Looks up from papers, cool] Tragic accident. I've already given my statement."

    - speaker: "player_presents_evidence"
      line: "[Show levitation scorch marks, erased log entry, missing focus]"

    - speaker: "morraine"
      line: |
        [Long pause. Composure cracks slightly]

        "She was a child. A FOURTH-YEAR. And she was about to publish a
        breakthrough in focuscore resonance that I've been researching for
        FIFTEEN YEARS.

        Do you understand what that would mean? My career, my reputation,
        eclipsed by a teenager who barely understood the foundational theory.

        I went to talk to her. To... to slow her down. Offer to collaborate—
        make it OUR discovery. She refused. Called me 'threatened' and
        'small-minded.'

        I just wanted her to WAIT. To give me time. But she wouldn't listen,
        and I... I panicked."

    - speaker: "graves"
      line: |
        "Panicked. You MURDERED a student and you call it panic?"

    - speaker: "morraine"
      line: |
        [Quiet, hollow]
        "I took her focus. I thought if there was no evidence of defensive
        magic... it would look like an accident. Just a shelf that fell.

        But you found the scorch marks. I should have known. Arithmancy
        never lies. The equations are always there, if you know where to look."

    - speaker: "graves"
      line: |
        [To player] "Good work, recruit. Take her to holding."

        [To Morraine] "Fifteen years of research. And you threw it all away
        because you couldn't stand a student being smarter than you.
        Pathetic."

  aftermath:
    outcome: |
      Professor Morraine is arrested and held for trial at the Occult Bench.
      Helena's research notes are turned over to the Department of Magical
      Research, where they credit her posthumously with advancing focuslore
      theory by a decade.

      The Sealed Stacks is closed for a week while new safety measures
      are implemented. Students hold a candlelight vigil for Helena in the
      library—Candlewicks turn out in full, and even some Iron Lodges attend.

      Marcus Sterling writes you a short note: "Thanks for not assuming I did it."

      Mr. Crankshaw nods at you in the corridor the next day. For him, that's practically
      a thank-you speech.

    graves_final_word: |
      GRAVES: "Case closed. {attempts_remaining}/10 attempts remaining.

      You identified the levitation evidence, traced the timeline, and didn't
      fall for the obvious suspect. That's acceptable work.

      But you hesitated when it came to a PROFESSOR. Remember: authority
      doesn't make someone innocent. Question everyone. TRUST NOTHING UNSEEN."
```

---

## Intro Briefing Content

### Graves's Rationality Lesson (Case 1)

```yaml
briefing:
  graves_teaches: |
    GRAVES: "Right. Before you even LOOK at the specific evidence in this
    case, answer me this—

    Out of 100 student deaths at Blackwood Collegiate ruled 'accidents,' how many
    actually ARE accidents? Not murders in disguise. Just... accidents."

  player_guess:
    prompt: "Your estimate?"
    options:
      - "10-20% (Most are actually murders)"
      - "40-60% (About half and half)"
      - "80-90% (Most are genuine accidents)"
      - "I don't know"

  graves_response_correct: |
    "85%. Not bad. You're thinking."

  graves_response_wrong_low: |
    "10%? You've been reading too many mystery novels, recruit."

  graves_all_paths_continue: |
    "85%. Eighty-five percent. Blackwood Collegiate is DANGEROUS. Moving staircases.
    Cursed artifacts. Students experimenting with magic they barely
    understand. Forbidden Forest full of things that want to eat them.

    Most of the time? An accident is just an accident.

    [Taps the case file]

    So THAT'S where you start with Helena Blackwood. Probably an accident.
    Tragic, but straightforward. Then you look at the EVIDENCE. Maybe it
    changes your mind. Maybe it doesn't.

    But you don't go looking for murder because it's more INTERESTING.
    You go looking for TRUTH—even if the truth is boring.

    [Magical eye swivels to fix on you]

    Start with what's LIKELY. Let evidence tell you if you're wrong.
    That's the first rule. Remember it."

  tutorial_briefing: |
    GRAVES: "Right. Investigation fundamentals. Pay attention.

    EXPLORATION: You can go anywhere in the crime scene. Examine anything.
    Ask about anything. Type what you want to investigate—I'm not holding
    your hand with a list of 'correct' actions.

    SPELLS: You have basic investigation rites. I'll teach you as needed.
    Start with UNVEIL—reveals hidden objects and magical traces. Point your
    focus, say 'Unveil,' and pay attention to what it shows you.

    EVIDENCE: When you find something important, you'll know. It gets logged
    automatically. Check your evidence board anytime to review what you've found.

    WITNESSES: People lie. People forget. People see what they want to see.
    Your job is to figure out which. Press them. Show them evidence. Make
    them PROVE their story.

    VERDICT: When you think you know who did it and WHY, you submit to me.
    Name the culprit. Explain your reasoning. If you're wrong, I'll tell you.
    You get ten attempts. Use them wisely.

    [Stands, magical eye spinning]

    Questions?"
```

---

## Rite System Tutorial Contexts

```yaml
spell_contexts:
  unveil:
    restricted_section_ceiling:
      works: true
      reveals: "levitation_scorch_marks"
      narration: |
        You cast Unveil upward. The spell illuminates faint scorch marks
        on the ceiling beam—the unmistakable pattern of Levitation Cantrip
        at high power. Someone lifted something HEAVY here.

        GRAVES: "Good instinct. Always check what's NOT at eye level."

      tutorial_moment: |
        GRAVES: "Unveil reveals hidden objects and magical residue. Point
        your focus and say 'Unveil.' Works on areas or specific objects.

        Remember: magic leaves traces. TRUST NOTHING UNSEEN."

    study_alcove:
      works: true
      reveals: "sterling_scarf"
      narration: |
        Your focus movement reveals a shimmer behind the desk. You pull out
        a green Iron Lodge scarf, hastily shoved out of sight. Silver embroidery:
        'M.S.'—Marcus Sterling.

  echo_reading:
    helena_focus_attempt:
      works: false
      reason: "Focus is missing (taken by killer)"
      narration: |
        You search Helena's robes, her hands, the surrounding area. Her focus
        isn't here. That's... unusual. Students don't drop their focuses, especially
        not in the Sealed Stacks where they need light.

        TOM: "Missing focus. Taken by killer? Or did it fall somewhere?"

      tutorial_moment: |
        GRAVES: "Echo Reading shows a focus's last spells. But you need the
        PHYSICAL FOCUS. Can't cast it on thin air, recruit."

    suspect_focuses_later:
      available_after: "Case progression, can request to examine suspect focuses"
      sterlings_focus_result: "Raise the Lamp, Lock Whisper, Raise the Lamp (nothing suspicious)"
      morraines_focus_result: "Levitation Cantrip (very powerful), Memory Veil (minor), Raise the Lamp"
      crankshaw_has_no_focus: "He's null-blooded - reinforces he couldn't have cast Levitation Cantrip"

  sense_presence:
    library_sweep:
      works: true
      reveals: "No one currently hiding in library"
      narration: |
        You cast Sense Presence, the detection spell spreading through the
        library. The spell returns empty—whoever was here is long gone.

        GRAVES: "Sense Presence detects hidden persons. Useful for searching
        large areas. But it only shows you WHO'S HERE NOW. Doesn't tell you
        who WAS here."

      tutorial_moment: |
        GRAVES: "Sense Presence—detects living humans in the area. Won't find
        ghosts, portraits, or animals. And it's NOW, not the past. Remember that."

  identify_substance:
    broken_lantern_oil:
      works: true
      reveals: "Standard lamp oil, nothing suspicious"
      narration: |
        You point your focus at the spilled oil. "Identify Substance."

        The spell identifies it: standard lamp oil, no poisons, no magical
        enhancement. The lantern broke when the shelf fell—collateral damage,
        not evidence.

      tutorial_moment: |
        GRAVES: "Identify Substance identifies potions and substances. Useful
        for poisons, unknown liquids, or checking if something's been tampered
        with. Doesn't work on people—only substances."

  general_guidelines:
    wards_present: false
    legal_status: "full_access (Blackwood Collegiate investigation, Headmaster authorized)"
    mnemonic_delving_forbidden: "Case 1 - Graves will NOT authorize, forbids attempts"
```

---

**END OF TECHNICAL SPECIFICATION**
