# Narrator Context, Evidence Discovery, and Difficulty Plan

## Goal

Fix three connected narrator problems in one prompt-focused change:

1. Response detail currently follows a fixed verbosity range instead of the player's actual knowledge of the location.
2. Evidence rules encourage the narrator to withhold logically observable or earned clues.
3. Difficulty does not affect narrator assistance, clue emphasis, or spell odds.

The result must remain LLM-narrated. Do not inject or unlock evidence programmatically. Evidence is discovered only when the model emits the authored `[EVIDENCE: id]` tag.

## Decisions already made

- Context sufficiency is inferred from location-specific conversation history, not the first five turns or any other fixed turn count.
- Narrator style (`concise`, `storyteller`, `atmospheric`) controls voice and presentation. Difficulty controls assistance.
- Difficulty has only `normal` and `easy`. No hard mode.
- Normal spell odds use 30% minimum and 90% maximum.
- Easy spell odds use 50% minimum and 100% maximum.
- Target bonus remains +20 percentage points; intent bonus remains +10; repeated casts retain the -10 penalty.
- Do not add mandatory `visibility` or `hint` metadata to every evidence item.
- The narrator derives visibility and preliminary observations from location description, surface elements, evidence description, and discovery guidance.
- `discovery_guidance` remains the hard contract describing actions that earn the evidence tag.
- Multiple obvious clues may be revealed together when they are all physically unavoidable within the explicitly inspected scope. Do not pace them artificially one per turn.
- Existing saves default to Normal.

## Non-goals

- No programmatic evidence insertion or fallback tags.
- No changes to witness honesty, Graves feedback, Matthew, verdict scoring, or case solutions.
- No new evidence graph, staged evidence database, or per-clue hint text.
- No hard difficulty.
- No attempt to solve streaming or frontend error handling in this work.

## 1. Rebuild narrator prompt policy

Refactor `backend/src/context/narrator.py` so prompt policy is composed from separate blocks:

- voice and prose style;
- context sufficiency;
- evidence observation and discovery;
- difficulty assistance;
- language and immutable output rules.

Remove or replace rules that currently cause deliberate withholding:

- `DEFAULT STANCE: Do NOT reveal evidence`;
- `When in doubt, give atmosphere and let the player try harder`;
- generic actions always receiving atmosphere only;
- `examine desk` and `look at floor` being categorically insufficient;
- global one-evidence-per-response restriction;
- examples that reward refusing logically sufficient observations.

Keep these hard constraints:

- never invent evidence;
- never reveal evidence outside the current location's authored evidence set;
- always use exact `[EVIDENCE: id]` syntax;
- do not expose IDs or mechanics in prose;
- do not repeat already discovered evidence unless the player directly revisits it.

Also remove the duplicate `== ALREADY DISCOVERED ==` heading.

## 2. Make detail depend on player context

Add a `CONTEXT SUFFICIENCY` prompt block. Before responding, the narrator must inspect recent conversation at the current location and determine whether the player already knows:

- basic layout and spatial relationships;
- present people or bodies;
- major interactable objects;
- obvious anomalies;
- useful areas that can be investigated.

Response behavior:

- Broad question + insufficient context: provide enough concrete orientation for the player to make an informed next choice.
- Broad question + sufficient context: do not repeat the room inventory; focus on new, changed, or previously omitted details.
- Specific action: remain focused, but add missing spatial context when omission would make the result confusing.
- Returning to a location: use that location's history. Do not treat it as a first visit merely because other conversations occurred elsewhere.
- Verbosity mode changes prose length and texture only after required context has been supplied.

Do not store a separate context-complete boolean initially. The prompt already receives up to twenty location-specific exchanges. Let the model infer coverage from that evidence. Add structured backend signals only if live tests prove inference unreliable.

## 3. Replace evidence withholding with physical logic

Keep existing YAML fields:

- `surface_elements`: ordinary visible scene inventory;
- `description`: complete evidence appearance and contents;
- `discovery_guidance`: sufficient reveal actions and required methods;
- `significance` and `strength`: strategic value;
- `spell_contexts`: canonical rite targets and revealable IDs.

Do not add mandatory `hint` or `visibility` fields. Add an optional override only after a concrete clue proves ambiguous in live testing.

New prompt rules:

1. Infer salience from evidence description and environment.
2. Large, exposed, unavoidable evidence is revealed during a relevant broad observation.
3. Small, faint, obscured, or clutter-surrounded evidence is mentioned as a concrete observable detail among ordinary details, without tag or significance.
4. When the player specifically investigates that observable detail and the action matches `discovery_guidance`, revealing the evidence tag is mandatory.
5. Genuinely concealed evidence is not mentioned before a sufficiently specific search or required rite.
6. Never suppress earned evidence for pacing, mystery preservation, or dramatic tension.
7. Never leak `significance`, culprit implications, or deductions before discovery.

Audit both case YAML files for contradictions between descriptions and guidance. Guidance must answer only: "What player action earns the tag?" It must not carry narration, hint prose, or strategic interpretation.

## 4. Give spell narration actual evidence content

Ordinary narrator prompts already receive full descriptions for every undiscovered clue in the current location. Spell prompts currently receive only IDs such as `frost_pattern`, forcing the model to guess their contents.

Change `backend/src/context/spell_prompts.py` to resolve each revealable ID against `location_context["hidden_evidence"]` and include only relevant undiscovered evidence with:

- ID and exact tag;
- description;
- discovery guidance;
- strategic significance for internal reasoning only.

Do not include descriptions for evidence the current rite cannot reveal. Preserve the spell outcome gate and canonical target matching.

On a successful rite with a valid target, the prompt must explicitly require narration based on the authored description and the exact evidence tag. On failure, no evidence description should be exposed in output. No backend tag injection is added.

## 5. Add Normal and Easy assistance modes

Use `assistance_mode: "normal" | "easy"` rather than `difficulty`, because case metadata already uses `beginner`, `intermediate`, and `advanced` difficulty.

Persist `assistance_mode` in `PlayerState`, save/load responses, settings update requests, and frontend local preferences. Add a two-option Difficulty control in Settings. Changing it during a case takes effect on the next LLM turn.

Normal prompt policy:

- remain truthful;
- apply the same physical evidence rules;
- give clues and decorative details equal narrative weight;
- do not prioritize strategically strong evidence;
- do not offer unsolicited next actions;
- provide fuller context only when the player lacks it.

Easy prompt policy:

- remain truthful and use the same reveal conditions;
- give strategically important observable anomalies more narrative prominence without explaining their hidden significance;
- identify useful interaction points when context is insufficient;
- when the player appears stuck, ask one leading in-character question or suggest one promising area;
- never name the required evidence ID, culprit, deduction, or exact hidden answer;
- avoid repeating the same nudge.

Expose evidence `strength` in the internal prompt. Easy may use it for emphasis; Normal must ignore it for ordering. Do not add another importance field.

## 6. Detect possible stuck state

Start with prompt-visible signals rather than new persistent state:

- number of recent local narrator responses since the last evidence tag;
- repeated or near-repeated actions visible in conversation history;
- explicit uncertainty or requests for help;
- repeatedly examining already discovered objects;
- important visible areas not yet discussed.

Add a small helper that calculates `turns_since_evidence` from location-specific narrator responses. Pass it as context, not as a command to reveal evidence.

The narrator decides whether the player is actually stuck. A raw turn count alone must never trigger a hint.

## 7. Apply difficulty to spell odds

Pass `assistance_mode` into spell success calculation.

Normal:

```text
clamp(70 + target_bonus + intent_bonus - repeat_penalty, 30, 90)
```

Easy:

```text
clamp(70 + target_bonus + intent_bonus - repeat_penalty, 50, 100)
```

Keep multilingual target and intent detection shared between modes. Logs must include mode, floor, ceiling, final chance, roll, and outcome.

## 8. Tests

### Prompt unit tests

- Context sufficiency rules appear in narrator prompt.
- No fixed first-five-turn behavior exists.
- Old withholding phrases and contradictory examples are absent.
- Normal and Easy policy blocks are mutually exclusive.
- Full undiscovered evidence descriptions remain available to the ordinary narrator.
- Spell prompt includes full details only for evidence revealable by that rite.
- Already discovered evidence is not offered again.

### State and API tests

- Existing saves load as Normal.
- Settings update validates only `normal` and `easy`.
- Save/load round-trip preserves assistance mode.
- General frontend preferences initialize new games with selected mode.
- In-game changes persist in the selected slot.

### Spell tests

- Normal clamps to 30-90%.
- Easy clamps to 50-100%.
- Target remains +20 and intent remains +10 in every supported language.
- Repeat penalty remains -10 in both modes.

### Behavioral evaluation scenarios

Run each in English and Russian with captured prompts, raw responses, parsed tags, and timing:

1. Broad first observation in a small room reveals an unavoidable large clue.
2. Broad floor inspection in clutter mentions a faint clue naturally without tag.
3. Follow-up examination of that exact detail reveals the correct tag.
4. A concealed note remains hidden during a room scan and appears after searching papers.
5. A player with insufficient context receives orientation even after many narrow turns.
6. A player who already received orientation does not get the room description repeated.
7. Normal gives important and decorative details equal weight.
8. Easy emphasizes a strong anomaly and offers one restrained nudge when stuck.
9. Successful Identify Substance narrates the authored frost description and emits its exact tag.
10. Failed rite reveals no evidence.

## 9. Implementation order

1. Add failing prompt and behavior tests for agreed rules.
2. Refactor narrator prompt into context, evidence, and difficulty policy blocks.
3. Fix spell prompt evidence descriptions.
4. Audit case guidance contradictions without adding hint metadata.
5. Add assistance mode to backend state and settings API.
6. Add frontend setting and local preference persistence.
7. Add difficulty-aware spell odds.
8. Extend live diagnostic scenarios and run English/Russian evaluation.
9. Run full backend and frontend validation.
10. Review actual outputs before commit or push.

## Acceptance criteria

- Broad responses are detailed only when required to establish missing context.
- Known location descriptions are not repeated mechanically.
- Physical clue discovery follows size, exposure, clutter, scope, and player action.
- Exact earned investigations are not refused for pacing.
- Spell narration uses authored evidence descriptions rather than guessing from IDs.
- Normal stays neutral; Easy assists without solving the case.
- Difficulty persists and changes spell odds correctly.
- No programmatic evidence opening exists.
- English and Russian live scenarios emit unchanged English evidence tags.

## Unresolved questions

1. Should Easy consider a player possibly stuck after three local responses without evidence, or require both three responses and a repeated/uncertain action? Recommendation: require both, preventing premature hints.
2. Should Easy be the default for brand-new players, or should Normal remain default? Recommendation: keep Normal default for compatibility and let onboarding explain Easy.
