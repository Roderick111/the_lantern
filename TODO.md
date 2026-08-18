# TODO

- [ ] Verify rite detection and outcomes end to end; live evidence path confirmed, but production random rite outcomes still need audit. Russian inflected targets now canonicalize (`столе` -> `desk`).
- [ ] Unify streaming errors: location view sometimes finishes with no reply or retry, while witness dialogue can show a stale false connection/incomplete-output error after success.
- [ ] Diagnose intermittent streaming near one token per second; capture model, provider, first-token latency, chunk cadence, and total latency.
- [ ] Replace Matthew fallback/mock reply: `Seems straightforward. Sometimes the obvious answer is the answer.`
- [ ] Add Compendium guidance: “Be specific and creative for better results” beside spoken-formula instructions.
- [x] Refactor narrator prompt around context sufficiency, logical evidence discovery, and difficulty; context depends on what the player knows, not turn count. See `docs/plans/2026-08-17-narrator-context-evidence-difficulty-plan.md`.
- [x] Add difficulty modes:
  - Easy: narrator is fuller and candid, points toward important details, and nudges a stuck player with questions or suggestions.
  - Normal: narrator stays candid but gives real leads and decorative details equal weight.
  - No hard mode.
  - Easy spell odds: 100% maximum chance, 50% minimum chance.
