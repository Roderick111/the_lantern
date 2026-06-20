# Project Status

**Version:** 2.2.0 (Matthew rename + lore compliance)
**Last Updated:** 2026-06-20
**Current Branch:** `feat/evidence-detection-natural-language`
**Current Phase:** Phase 7 (Production Readiness)
**Type Safety Grade:** A

---

## Quick Status

| Category | Status | Notes |
|----------|--------|-------|
| Backend | 🔄 Near ready | Python 3.13, FastAPI, SQLite (`/app/saves`), **858 pass / 11 fail / 4 skip** on branch |
| Frontend | ✅ Production Ready | React 18, TypeScript 5.6, Zod validation, 0 TS errors |
| Type Safety | ✅ Grade A | Compile-time (0 TS errors) + runtime (Zod) validation |
| LLM | ✅ BYOK + Streaming | Multi-provider via LiteLLM, SSE streaming |
| Saves | ✅ Stable | Server-authoritative SQLite, autosave + 3 manual slots, HMAC player tokens |
| Cases | 🔄 Lore pass in progress | Case 001 Wisp redesign live; critical HP leaks fixed; medium echoes remain |
| Docs | 🔄 Consolidated | Legacy PRPs/archive purged; case design docs under `docs/case-files/` |

---

## 🔄 In Progress

### Natural-language evidence detection
- Branch: `feat/evidence-detection-natural-language`
- Extend `LocationCommandParser`-style matching to evidence discovery triggers
- **11 backend test failures** on branch (routes, save corruption, mnemonic delving) — fix before merge

### Witness evidence reaction system
- `witness_reactions` data in `case_001.yaml` for every evidence piece
- **No UX/mechanic yet** — show-evidence button vs automatic vs conversational TBD

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

**Known issues:**
- 11 failing backend tests on current branch
- Frontend tests: ~377/565 (pre-existing infrastructure gaps)
- Case 001 medium lore echoes not yet scrubbed
- `check_secret_triggers()` exists but unused in live witness flow

---

## What's Next

**Before merge:**
1. Fix 11 backend test failures on branch
2. Run full validation (`validate.md` gates)

**Immediate:**
1. Design witness evidence reaction UX
2. Natural-language evidence trigger matching (branch goal)
3. Case 001 lore pass (medium HP echoes) + optional grammar cleanup (`bind in stillness`, `the the undercroft`)

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
| Backend Tests | 858 pass / 11 fail / 4 skip (branch, 2026-06-20) |
| Frontend Tests | ~377/565 (~67%) |
| TypeScript Errors | 0 |
| License | MIT |