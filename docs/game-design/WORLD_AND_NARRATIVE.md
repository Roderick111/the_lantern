# The Lantern — World Design & Narrative

Canonical world bible for writers, case designers, and prompt authors.

**Design north star:** Sherlockian deduction + Lovecraftian cosmic dread + European folklore residue. Victorian London fog, gaslight, and industrial grit. Rational investigation against things that should not be — without a licensed wizard school, without handholding.

---

## Table of Contents

1. [Core Premise](#core-premise)
2. [The Vibe](#the-vibe)
3. [Setting](#setting)
4. [What “Magic” Means](#what-magic-means)
5. [Factions](#factions)
6. [Threats](#threats)
7. [Tone](#tone)
8. [The Lantern Institute](#the-lantern-institute)
9. [How Cases Work](#how-cases-work)
10. [Investigation Rites](#investigation-rites)
11. [Key Characters](#key-characters)
12. [Mechanics ↔ World](#mechanics--world)
13. [Sanity & Rationality](#sanity--rationality)
14. [Overarching Narrative](#overarching-narrative)
15. [Writer Guidelines](#writer-guidelines)
16. [Canonical Decisions](#canonical-decisions)

---

## Core Premise

**When:** 1890s alternate London.

**What:** The **Lantern Order** trains investigators to expose “impossible” cases — spiritualist frauds, occult cults, forbidden experiments, and rare **eldritch incursions** where something from outside ordinary reality has left traces in the world.

**The tension:** The player applies **reason, evidence, and falsification** in a universe where the irrational is sometimes real. Not every horror is a hoax. Not every hoax is harmless. The job is to tell the difference before the difference costs lives — or minds.

**Player role:** Probationary Lantern Investigator, **1890s present**. Cases are live assignments — real crime scenes, real witnesses, real stakes — supervised by Inspector Graves. You are watched. You are measured.

**Matthew Croft** (spirit companion) is bound to your Lantern resonance — a cautionary ghost from parlour fraud who died at Candlewick (1886) when a genuine ward-circle was performed as theatre.

---

## The Vibe

Three literary currents, one investigation:

| Current | What it gives the game |
|--------|-------------------------|
| **Sherlock** | Observation, chains of inference, base rates, eliminating impossibilities, the desk covered in facts |
| **Lovecraft** | Cosmic wrongness, limits of human understanding, dread that is intellectual before it is visceral |
| **Folklore** | Grounded regional texture — old European myth echoes, not a unified “monster manual” |

**Not this:** cosy whimsy, chosen-one power fantasy, spell-duel action, lore dumps in narrator voice.

**This:** A lamplight held steady while the fog tries to think its way inside your skull.

---

## Setting

### London, gaslit and layered

- **Streets:** Fog, cobbles, hansom clatter, factory smoke, charity sermons, gin shops
- **Hidden strata:** Occult salons behind respectable facades, East End slums where folk beliefs survive modernization, crumbling manors in the home counties, **secret libraries** that should not catalogue what they catalogue
- **Social order:** Class, empire, scientific optimism, and spiritualist fashion collide — séances are entertainment until they are not

### Atmosphere anchors

Use concrete period detail: lamplight, soot, wool coats, ink-stained fingers, ward-marks chalked where servants will not look, the smell of nightshade or ozone after a working gone wrong.

### Case locations

Cases may be set anywhere the dossier demands — a collegiate library wing, a patron’s town house, a riverside warehouse, a candlewick séance parlour. **Location is per-case**, defined in YAML (`setting`, `crime_scene`, `world_context`). The Institute is home base; the city is the field.

---

## What “Magic” Means

There is no single “magic system” in the setting. There are **overlapping explanations**, and the investigator’s job is to determine which layer is active.

| Layer | In-world reality | Investigator’s lens |
|-------|------------------|---------------------|
| **Psychology & fraud** | Suggestion, grief, performance, planted evidence | Hoax, motive, means |
| **Occult craft** | Wards, bindings, focused instruments, trained practitioners | Technique, access, timeline |
| **Cosmic bleed** | Entities, geometries, cognition-warping presence | Containment, pattern, what rationality can and cannot model |

**Graves’s rule:** *“The lamp shows what’s there. Your mind decides what it means.”*

Rites (see below) are **Lantern methodology** — formalized procedures with occult trappings and reproducible results. They are tools of inquiry, not combat powers. Misapplied, they attract attention from things that prefer not to be noticed.

---

## Factions

### Crown Occult Bureau

**Government body.** Regulates the Lantern Order, occult practitioners, classified materials, and public disclosure of impossible incidents.

- Interfaces with police, Home Office, and respectable science
- Issues mandates, licenses, and **suppression orders** when panic is deemed worse than truth
- Not synonymous with the Lantern Order — it **oversees** them
- Source of institutional-corruption pressure in the meta-arc (see [Overarching Narrative](#overarching-narrative))

### Lantern Order

Field investigators. Trained at the Institute. Bureau mandate: separate fraud from harm, document the inexplicable, prevent public panic.

- **Public face:** Serious, procedural, faintly dull
- **Private reality:** They have seen enough to know cosmic incursions are not all allegory
- **Internal tension:** Method vs. morale; Bureau orders vs. what the evidence demands

### The Argent Veil

**Named antagonist order** — the recurring Veil Society behind the meta-arc. Not every cult in a case file; the **network** attentive players trace across investigations.

- Hermetic society chasing contact “beyond the veil” through stolen ward-diagrams, patronage, and compromised officials
- Blends pseudoscience with genuine craft — often opens doors they interpret as metaphor
- Primary driver of **cosmic-suppression** plot: knowledge buried, witnesses silenced, incidents reclassified as fraud

Other small occult clubs and fraud rings exist case-by-case. The Argent Veil is the through-line.

### The Establishment

Skeptical police, scientists, press, and respectable society.

- Default stance: fraud, hysteria, or crime with mundane explanation
- Useful allies when evidence is physical; obstacles when it is not
- **Base rates matter:** Most reported hauntings are nonsense. The Lantern Order exists for the remainder.

### Folk remnants

European myth echoes — not a unified pantheon, but **regional residue**:

- Slavic forest spirits (leszy-like watchers in old woodlands)
- Germanic wild-hunt motifs (processions that are not quite human on winter roads)
- Local parish stories, cunning folk, charms that work often enough to survive ridicule

Use sparingly. Folklore **textures** a case; it rarely solves one. The investigator still needs evidence.

---

## Threats

Four threat types map to case design:

| Threat | Example case engine | Player skill tested |
|--------|---------------------|---------------------|
| **Cosmic entities** | Wrong geometry, shared delusions, books that should not be read | Holding inference steady under dread; not “explaining” what cannot be fully explained |
| **Cults & veil societies** | Summoning via pseudoscience, stolen ward-diagrams, charismatic leaders | Timeline, motive, chain of custody, undercover fraud patterns |
| **Frauds & hoaxes** | Phosphor ghosts, slate tricks, insurance schemes | Base rates, mechanism, replication of trick |
| **Human malice** | Murder dressed as accident, institutional cover-up | Evidence board, interrogation, falsification |

A strong case often stacks two layers — e.g. a fraud concealing a genuine binding, or a cult accidentally opening a door they thought was metaphor.

---

## Tone

**Gothic mystery:** dread in the architecture, not splatter for its own sake.

**Hopeful rationalism vs. despair:** The lamp is the symbol. Investigation is an act of stubborn hope — that truth can be approached, that minds can be disciplined, that some horrors can be **named and bounded** even when they cannot be “solved” like a parlour puzzle.

**Player fantasy:** Uncover truth without losing your mind or your integrity.

**Voice split (by design):**

| Voice | Role | Temperature |
|-------|------|-------------|
| **Narrator** | Scene, evidence gating, atmosphere | Immersive third-person present |
| **Graves** | Briefing, verdict feedback, rationality lessons | Gruff, procedural, guarded |
| **Witnesses** | Character, secrets, lies | In-world, motivated |
| **Matthew** | Spirit companion, 50/50 helpful/misleading | Carnival patter vs. rare honesty |

Do not blend these roles in prompts. One voice owner per channel.

---

## The Lantern Institute

**HQ:** A grim academy on the edge of respectable London — part **science laboratory**, part **archive of closed horrors**, part **field operations centre**.

- Probationary investigators deploy to **live cases** under Graves’s supervision
- Archives hold seized texts, redacted Bureau files, and instruments the Establishment pretends do not exist
- Graves’s briefing room: brass lamp fixtures, chalkboard base rates, smell of old paper and carbolic

The Institute is not a boarding school for child prodigies. It is where the Order prepares adults for work that would break casual observers.

---

## How Cases Work

### Present-tense investigations (1890s)

Every playable case is a **real, active investigation** in the 1890s — fresh bodies, living witnesses, Bureau pressure, stakes that do not reset when the player leaves the scene. No “training exercise” frame. No historical reconstruction. No closed-file replay.

**Blackwood Collegiate** remains a canonical case location — a prestigious occult college in London where several investigations unfold.

### Per-case YAML contract

Writers supply:

- `setting` — short atmospheric label for prompts
- `crime_scene` — where the body / incident is
- `world_context` — era facts, social tension, **no spoiler dumps in narrator voice**
- `locations`, `witnesses`, `evidence`, `solution` — standard schema

See `docs/case-files/CASE_DESIGN_GUIDE.md` for craft; this doc is **world**, not schema reference.

### Case priority (story design)

1. **Character stories** — people with motives, shame, loyalty
2. **Mystery structure** — red herrings, hypothesis shifts, earned reveals
3. **Rationality lessons** — emerge from mistakes, reinforced at verdict

---

## Investigation Rites

Seven **Lantern investigation rites** (implemented in code as `SPELL_DEFINITIONS`):

| Rite | Narrative function |
|------|-------------------|
| **Unveil** | Reveal concealed physical evidence |
| **Sense Presence** | Detect hidden persons |
| **Identify Substance** | Analyse residues, compounds, enchanted materials |
| **Raise the Lamp** | Forensic illumination — traces, patterns |
| **Echo Reading** | Recover recent workings from a focus instrument |
| **Mend** | Reconstruct broken objects; read breakage pattern |
| **Mnemonic Delving** | Restricted — memory / surface thoughts; legal and trust risk |

**Narrator rule:** Never tell the player which rite to use. Describe phenomena; let them choose.

**Matthew’s rule:** May suggest rites confidently and be wrong — carnival expertise, not Order training.

---

## Key Characters

### Player — Probationary Lantern Investigator

Minimal backstory. Fresh eyes. Measured by Graves through investigation quality, not combat stats.

### Inspector Alastor Graves

Veteran field supervisor. Paranoid, procedural, educational. Guards case details in briefing — investigators must **work** for specifics. Teaches base rates and fallacy awareness. Brass lantern-eye, gruff affection disguised as contempt.

**Function:** Briefing Q&A, verdict analysis, rationality framing.

### Matthew Croft — Spirit Companion

Unreliable ghost bound to Lantern resonance. Former circus medium; died at the **Candlewick séance (1886)** when a genuine ward-circle was performed as theatre. Something **noticed** him.

**Function:** `Matthew,` prefixed questions — verification prompts (helpful) vs. carnival heuristics (misleading). Trust arc unlocks honesty about Candlewick.

Full profile: `MATTHEW_CROFT_CHARACTER.md`

---

## Mechanics ↔ World

| Game system | World expression |
|-------------|------------------|
| Freeform narrator | Player actions at live crime scenes and locations |
| `[EVIDENCE: id]` tags | Lantern evidence custody — facts entering the board |
| Evidence board | Investigator’s working hypothesis surface |
| Witness interrogation + trust | Social inference under pressure; LA Noire-style honesty gates |
| Present evidence | Confrontation with contradictions |
| Verdict + fallacy detection | Graves as rationality examiner |
| Briefing engagement | Graves assigns live case facts before deployment |
| Rites | Formalized Lantern methodology |
| Matthew companion | Spirit resonance — not an inner voice, a bound witness |
| Saves / slots | Case dossier progress in Institute records |

---

## Sanity & Rationality

**Implicit only** — no sanity meter UI. Mental steadiness is expressed through play and feedback:

- **Good practice:** Base rates before theories, falsification, one hypothesis at a time, evidence before accusation → narrator stays controlled; Graves approves
- **Bad practice:** Availability bias, confirmation bias, ad hominem, jumping to culprit → Graves names the fallacy at verdict; Matthew may **reinforce** the mistake with confident patter
- **Cosmic cases:** Some truths are incomplete by nature — “winning” means **bounded understanding**, not full cosmic comprehension

---

## Overarching Narrative

Two intertwined arcs — **primary:** Argent Veil / cosmic suppression; **secondary:** Crown Occult Bureau corruption.

```
PHASE 1 — FIELD CASES (Cases 1–N)
├─ Real investigations at Blackwood Collegiate and across London
├─ Graves measures reasoning, not lore knowledge
└─ Self-contained mysteries; human stakes first

PHASE 2 — PATTERN (optional attentive play)
├─ Argent Veil fingerprints: shared ward-marks, suppressed witnesses, “accident” rulings
├─ Bureau redactions that protect panic — or protect the Veil
└─ Player notices; Graves deflects until pressed

PHASE 3 — THE TEST
├─ Primary: Expose Argent Veil’s cosmic-suppression network — or quiet the file
├─ Secondary: Bureau officials who buried Cases X/Y/Z for embezzlement or career cover
└─ No single “correct” ending — reasoning skill vs. institutional courage

PHASE 4 — EXPANSION
├─ Field Investigator status; Veil retaliation or Bureau hostility depending on choices
└─ Corruption thread and Veil thread can reinforce or contradict each other
```

**Principle:** Correct **deduction** is the core lesson. What you **do** with truth — Veil exposure, Bureau confrontation, quiet resolution — is the harder exam.

---

## Writer Guidelines

### Do

- Ground scenes in **period sensory detail** (fog, lamp, soot, paper, cold stone)
- Let **class and institution** create friction (collegians, servants, Bureau men, slum witnesses)
- Distinguish **fraud layer** vs. **genuine craft** vs. **cosmic residue** in evidence design
- Keep `world_context` as **facts for the model**, not prose to recite to the player
- Parameterize setting per case — no hardcoded “one school” in prompts

### Don’t

- Reference other IP franchises, “wizard schools”, or modern slang
- Dump `significance` fields into undiscovered evidence (spoiler leak)
- Use narrator as GM commentary (“clever move!”) in atmospheric mode — wry tone is `storyteller` verbosity only
- Hand-hold rites or locations in narrator text
- Make every case cosmic — **base rates**: most incidents are fraud or human malice

### Narrator voice target

Victorian investigative prose: precise observation, wrongness at the edges, restraint. Lovecraftian **dread** through implication; Sherlockian **clarity** in what is physically observed.

### Witness voice target

Character-first. They know their slice of truth — not the full case YAML. Secrets are **filtered** by trust and confrontation, not pre-loaded.

---

## Canonical Decisions

| Topic | Decision |
|-------|----------|
| **Blackwood Collegiate** | Keep — canonical occult college for case locations |
| **Timeline** | 1890s present only; all cases are live investigations |
| **Crown Occult Bureau** | Government regulator; oversees Lantern Order and occult affairs |
| **Lantern Order** | Field investigators (Institute-trained) |
| **Antagonist order** | **The Argent Veil** — named recurring Veil Society |
| **Sanity** | Implicit via rational play + fallacy feedback; no meter |
| **Meta-arc** | Primary: Argent Veil / cosmic suppression. Secondary: Bureau corruption |
| **Spirit companion** | Matthew Croft (`MATTHEW_CROFT_CHARACTER.md`) |

---

*Living document.*