# Project Status

**Version:** 2.3.0 (Primary web game + secondary Telegram beta + EN/RU localization)
**Last Updated:** 2026-07-17
**Current Branch:** `feat/evidence-detection-natural-language`
**Current Phase:** Web primary; Telegram secondary-client beta deployment
**Type Safety Grade:** A

---

## Quick Status

| Category | Status | Notes |
|----------|--------|-------|
| Backend | ✅ Ready | Python 3.13, FastAPI, SQLite (`/app/saves`), **898 pass / 4 skip** |
| Frontend | ✅ Production Ready | React 18, TypeScript 5.6, Zod validation, 0 TS errors |
| Telegram | ✅ Secondary beta implemented | Bun + Hono + grammY gateway, durable jobs, Mini App, EN/RU, Case 001; web remains primary |
| Type Safety | ✅ Grade A | Compile-time (0 TS errors) + runtime (Zod) validation |
| LLM | ✅ BYOK + Streaming | Multi-provider via LiteLLM, SSE streaming |
| Saves | ✅ Stable | Server-authoritative SQLite, autosave + 3 manual slots, HMAC player tokens |
| Cases | ✅ Case 001 playable | Wisp redesign live; English/Russian authored localization; paragraph-safe prose rendering |
| Docs | ✅ Updated | Telegram implementation/deployment plans and current status documented |

---

## 🔄 In Progress

### Telegram secondary-client beta deployment
- Branch: `feat/evidence-detection-natural-language`
- Code is implemented and validated locally. This is an optional secondary client, not a replacement for the web game.
- Remaining owner steps: apply migration SQL, configure production secrets, build/deploy the Telegram service, set webhook, and run the production smoke test.
- Production host: `bot.thelantern.institute`

### Future Telegram product work
- Add additional authored localized cases.
- Implement paid-case entitlement purchases with Telegram Stars when a paid case exists.
- Expand Mini App polish after beta feedback.

### Lore compliance (Case 001)
- ✅ Fixed: pear kitchen gag → service bell + warded pantry hatch; `healing potion winky` → `pippa`; Graves `Restricted Section` → `Sealed Stacks`
- Remaining medium echoes: `Minerva` Whitmore, `Great Hall`, prefect/Head Boy/castle language, Hand of Glory / Moste Potente Alchemy

---

## ✅ Recent Completions

### 2026-06-20 — Matthew rename + briefing + lore fixes
- **Matthew refactor:** `tom` / `inner_voice` → `matthew` across API (`/api/matthew/*`), context modules, frontend hooks/components; backward compat for legacy save fields and `"tom"` message type
- **Briefing skip:** `SKIP_BRIEFING_CALIBRATION_AND_ENGAGEMENT = true` — dossier only, then start investigation
- **Location assets:** `iron_lodge_common_room.*`, `librarian_office.*` copied from legacy portrait names
- **Lore pass:** bound familiars (not elves), case 002 `M.S.` initials, CASE_DESIGN_GUIDE / case-file doc fixes
- **Case 001 HP leaks (critical):** kitchen access, Whitmore keyword, Graves wrong-suspect text

### 2026-07-17 — Telegram gateway, Mini App, and localization
- **Telegram gateway:** Bun/Hono/grammY webhook and local polling modes, durable SQLite update/job queue, idempotent engine mutations, serial per-player processing, retry-safe Telegram delivery, health/metrics, and secret-safe structured logs.
- **Telegram play loop:** English/Russian onboarding, freeform investigation and witness messages, inline Casebook/Evidence/Witnesses/Move/Verdict buttons, autosave, 40 LLM turns per UTC day, and Case 001 verdict flow.
- **Mini App:** authenticated Casebook, Evidence, Witnesses, and Verdict routes with Telegram `initData` validation, signed sessions, CSRF, origin checks, and feature flags.
- **Localization:** dedicated Russian Case 001 overlay with stable mechanics IDs; English and Russian names/descriptions for locations, witnesses, evidence, briefing, verdict, and Telegram UI.
- **Prose rendering:** case loader folds authored line wraps into spaces while preserving blank lines as paragraphs across web, Telegram, and case discovery.
- **Deployment:** `Dockerfile.telegram`, Compose service on `bot.thelantern.institute`, shared proxy network, Telegram data volume, and phase-specific deployment/runbook docs.

### 2026-06-19 — Medium review + deploy verification
- Model catalog lock, spell detection unified, CORS tighten, telemetry safety
- Frontend: autosave slot naming, `ensureSession` 401 recovery, location roundtrip cuts
- Location switch restores per-location `conversation_history` from `updated_state`
- Deploy verified: `lantern.db` active; legacy JSON saves are artifacts only
- Restart/save: cache invalidation on delete/reset, location localStorage cleared on restart

### 2026-05/06 — 5-wave refactor (50 items)
- Auth: HMAC player tokens, IDOR fix — all routes require `X-Player-Token`
- State: SQLite + bounded LRU cache, slot semantics (autosave snapshots)
- SSE: keepalives, post-LLM try/except, witness history cap (50)
- Baseline after waves: 867 pass, 4 skip

### 2026-04-07 — Case 001 redesign + save system
- Culprit: Wisp (layered magic twist); three-phase misdirection Elena → Cassian → Wisp
- Raw evidence descriptions; `witness_reactions` per evidence
- Per-player UUID saves, JSON → SQLite, slot-aware API

---

## Architecture

**Backend:** Python 3.13 + FastAPI + LiteLLM
- **State:** `PlayerState` in SQLite (`saves/lantern.db`), 4 slots per `(player_id, case_id)`
- **Pattern:** Load → mutate → save per action; LLM prose + programmatic extractors (`[EVIDENCE:]`, `[TRUST_DELTA:]`, secret text scoring)
- **Secrets:** LLM decides whether to reveal (trust/pressure prompt); server detects revelation via `score_secret_revelation` — YAML `trigger` fields parsed but **not enforced** in witness routes
- Start: `cd backend && uv run uvicorn src.main:app --reload`

**Telegram secondary client:** Bun + Hono + grammY + Vite/React
- Gateway owns Telegram identity, modes, durable jobs, daily usage, localization presentation, and Mini App sessions.
- FastAPI remains source of truth for both clients. The web client is the primary full-featured player experience; Telegram is a constrained chat-first surface.
- Start locally: `cd telegram && ~/.bun/bin/bun run dev:poll`

**Frontend:** React 18 + TypeScript + Vite + Tailwind
- Thin client state; full progress on server
- Zod `.strict()` schemas mirror Pydantic responses
- Start: `cd frontend && ~/.bun/bin/bun run dev`

---

## What's Working

- Investigation (LLM narrator, evidence tags, spells, location nav)
- Witnesses (interrogation, trust deltas, programmatic secret detection, present evidence)
- Verdict (fallacy detection, confrontation, wrong-suspect feedback)
- Briefing (dossier; calibration/engagement skippable via feature flag)
- Matthew spirit companion (auto-comments + chat)
- Save/load (autosave + 3 slots, export/import JSON)
- Music, BYOK, SSE streaming, case landing page
- Primary web game: full investigation, rites, witnesses, verdict, saves, music, Matthew, and multi-provider LLM support
- Secondary Telegram bot and Mini App beta path (Case 001, English/Russian)

**Known issues:**
- Web remains the primary product; Telegram intentionally supports a smaller Case 001 surface and omits several web features.
- Telegram production deployment still requires owner-run SQL migrations, production secrets, webhook registration, and smoke testing.
- Telegram currently exposes Case 001; additional cases need authored locale overlays before Russian release.
- Frontend suite still contains 134 todo tests; no current type errors.
- `check_secret_triggers()` exists but remains unused in live witness flow.

---

## What's Next

**Before public Telegram secondary-client beta:**
1. Apply `backend/migrations/2026-07-17-idempotency-records.sql` and Telegram gateway migrations.
2. Configure production env values and deploy with `./deploy.sh`.
3. Register Telegram webhook and verify `/health`, onboarding, first clue, first interview, first verdict, and solved-case funnel.
4. Run full validation (`backend`, `frontend`, and `telegram` suites) after deployment.

**Immediate:**
1. Collect Telegram beta feedback and fix onboarding/play-loop friction.
2. Add authored locale overlays for future cases.
3. Decide witness evidence reaction UX for richer Telegram interactions.

**Phase 7 — Production:**
1. Key manager (Infisical or similar)
2. Security headers, CORS hardening, error sanitization

**Future:**
- Additional cases (003+)
- Meta-narrative / Argent Veil arc
- Bayesian probability tracker (optional teaching tool)

---

## Key Documents

| Doc | Purpose |
|-----|---------|
| `CLAUDE.md` | Dev guide (root) |
| `backend/CLAUDE.md` | Backend architecture index |
| `frontend/CLAUDE.md` | Frontend architecture index |
| `docs/case-files/CASE_DESIGN_GUIDE.md` | Case authoring |
| `docs/case-files/STORY_DESIGN_METHOD.md` | Narrative design method |
| `README.md` | Setup and run instructions |

---

## Metrics

| Metric | Value |
|--------|-------|
| Backend Tests | 898 pass / 4 skip (2026-07-17) |
| Frontend Tests | 332 pass / 2 skip / 134 todo |
| Telegram Tests | 55 pass (2026-07-17) |
| TypeScript Errors | 0 |
| License | MIT |
