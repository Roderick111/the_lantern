# Code Review Findings — The Lantern

**Date:** 2026-06-20  
**Branch:** `feat/evidence-detection-natural-language`  
**Scope:** Full project (Python FastAPI backend + React/TypeScript frontend)  
**Review method:** 9 parallel focused reviews (Security, Performance, Error Handling, Concurrency, Architecture, API Ergonomics, Testability, Dead Code, API Design)

**Note:** Review objectives were adapted from a Rust/cargo template. This project uses Python/UV and Bun; tool-augmented reviews used `pip-audit`, `bun audit`, `vulture`, `ruff`, and `bun run build` instead of cargo tools.

---

## Executive Summary

The highest-severity finding appears across **6 of 9 review lenses**: removing `model_copy(deep=True)` from `load_slot_state` (`backend/src/api/helpers.py:443-447`) causes concurrent requests for the same `(player_id, case_id, slot)` to share one mutable `PlayerState`. Combined with unsynchronized `_state_cache` access from `asyncio.to_thread`, this creates data races, lost updates, and cross-request state leakage.

Secondary systemic themes:

- **Corrupt save handling** — silent swallow → `None` vs explicit `ValueError` → 400; frontend overwrites corrupt saves with default state
- **Cache vs SQLite drift** — three write paths, selective invalidation; `/api/save` and `/api/load` bypass `_state_cache`
- **Dependency CVEs** — 41 Python + 20 frontend transitive advisories from audit tools

---

## Cross-Cutting Finding

### CRITICAL — Shared mutable `PlayerState` cache (multiple reviewers)

| Field | Value |
|-------|-------|
| **File** | `backend/src/api/helpers.py:443-447` |
| **Tags** | MANUAL — Security, Concurrency, Architecture, Error Handling, API Design, Testability |
| **Change** | `load_slot_state` returns cached `PlayerState` by reference instead of `model_copy(deep=True)` |

**Impact:**

- Concurrent handlers for the same player/slot mutate one object (evidence, conversation, verdict counters)
- Cross-request leakage in `updated_state` / SSE `done` payloads
- `_state_cache` updated from event loop and `asyncio.to_thread` without locks
- TOCTOU on cache populate: two concurrent first-loads → last-write-wins
- Verdict `attempts_remaining` check-then-act race

**Recommendation:** Restore `model_copy(deep=True)` on cache hit, or add per-request isolation + optimistic concurrency versioning.

---

## 1. Security (OWASP)

**Focus:** Injection, path traversal, supply chain, information disclosure.

### Tool Output

#### `pip-audit` (backend)

```
WARNING: pip-audit audited wrong venv (hp_game) while the_lantern venv was active.
Found 41 known vulnerabilities in 11 packages.

Name              Version  ID                  Fix Versions
----------------- -------- ------------------- ------------
aiohttp           3.13.3   CVE-2026-34515      3.13.4
aiohttp           3.13.3   CVE-2026-34513      3.13.4
... (19 more aiohttp CVEs)
idna              3.11     PYSEC-2026-215      3.15
msgpack           1.1.2    GHSA-6v7p-g79w-8964 1.2.1
pip               25.3     PYSEC-2026-196      26.1.2
pydantic-settings 2.12.0   GHSA-4xgf-cpjx-pc3j 2.14.2
pygments          2.19.2   CVE-2026-4539       2.20.0
pytest            9.0.2    CVE-2025-71176      9.0.3
python-dotenv     1.2.1    CVE-2026-28684      1.2.2
requests          2.32.5   CVE-2026-25645      2.33.0
starlette         0.50.0   PYSEC-2026-161      1.0.1
starlette         0.50.0   CVE-2026-48818      1.1.0
starlette         0.50.0   CVE-2026-54283      1.3.1
urllib3           2.6.3    PYSEC-2026-142      2.7.0
```

Exit code: 1

**Fix:** Run with explicit `backend/.venv/bin/python -m pip_audit` in CI; unset conflicting `VIRTUAL_ENV`.

#### `ruff check .` (backend)

18 issues — mostly E402 (imports not at top), I001 (import sorting), F401 (unused imports). No security findings.

#### `bun audit` (frontend)

20 vulnerabilities (10 high, 9 moderate, 1 low) in dev/build tooling: vite, rollup, ws, fast-uri, flatted, @babel/plugin-transform-modules-systemjs, brace-expansion, etc.

### Findings

| # | Tag | Severity | Location | Finding |
|---|-----|----------|----------|---------|
| 1 | TOOL | HIGH | Dependencies | 41 known Python dependency CVEs. Most impactful for deployed API: starlette 0.50.0, aiohttp 3.13.3 (via LiteLLM), urllib3, requests, python-dotenv, pydantic-settings |
| 2 | TOOL | MEDIUM | CI/config | `uv run pip-audit` audited wrong venv (`hp_game`) while `the_lantern` was active — supply-chain signal may be stale/wrong |
| 3 | TOOL | MEDIUM | frontend deps | 20 transitive advisories (10 high) in dev/build tooling. Lower runtime exposure for static production assets |
| 4 | MANUAL | HIGH | `helpers.py:436-447` | Shared mutable in-memory `PlayerState` cache — concurrent requests interleave mutations. Integrity loss, nondeterministic saves |
| 5 | MANUAL | HIGH | `frontend/src/api/base.ts:119-151` | BYOK API keys in browser `localStorage` and `X-User-API-Key` headers — XSS exfiltration risk |
| 6 | MANUAL | MEDIUM | `witnesses.py:448` | SSE error path leaks internal exception text: `message: str(e)[:200]` on `persist_failed` |
| 7 | MANUAL | MEDIUM | `witnesses.py:425`, `investigation.py:403`, `main.py:114` | LLM/telemetry logs may capture sensitive provider errors; upstream auth errors sometimes echo key fragments |
| 8 | MANUAL | MEDIUM | `rate_limit.py:12-14` | Rate-limit key trusts `X-Forwarded-For` without trusted-proxy config — spoofing when not behind configured reverse proxy |
| 9 | MANUAL | MEDIUM | `session.py:45-57` | `POST /api/session` is public and not rate-limited — mass minting of `player_id`s and SQLite rows (DoS / disk fill) |
| 10 | MANUAL | MEDIUM | `saves.py` | Save/load endpoints lack rate limits — authenticated abuse can hammer SQLite WAL |
| 11 | MANUAL | MEDIUM | `auth.py:82-89` | Legacy player tokens never expire — stolen legacy tokens valid until `PLAYER_TOKEN_SECRET` rotation |
| 12 | MANUAL | MEDIUM | `saves.py:53-68` | Client-controlled save bootstrap — `PlayerState(**request.state)` on first save allows arbitrary field injection |
| 13 | MANUAL | LOW | `loader.py:41-45, 54-55` | Path traversal mitigated: `^[a-zA-Z0-9_]+$` + `yaml.safe_load` |
| 14 | MANUAL | LOW | `persistence.py:83-87, 120-127` | SQL injection mitigated: parameterized queries + `_validate_identifier` |
| 15 | MANUAL | LOW | App code | Command injection: none found (no `subprocess` / `shell=True`) |
| 16 | MANUAL | LOW | `main.py:74-98` | CORS: explicit origins, strips `*` with credentials |
| 17 | MANUAL | LOW | `main.py:58-70` | Request body DoS partially mitigated: `MAX_BODY_SIZE = 8 KiB` |
| 18 | MANUAL | LOW | `llm_client.py:92-96` | BYOK model validation is heuristic substring match — availability/cost risk, not RCE |
| 19 | MANUAL | LOW | `telemetry/logger.py:41-65` | File permissions good: `0o700` dir / `0o600` files. SQLite DB mode not hardened explicitly |
| 20 | MANUAL | LOW | `llm_config.py:49-50` | `/llm/verify` generic errors; tests assert no upstream leak |

**Positive controls:** HMAC session tokens with expiry (v1), IDOR fix on session reuse, `PLAYER_TOKEN_SECRET` length check, witness SSE LLM errors sanitized, OpenAPI 500 handler returns generic detail, no `dangerouslySetInnerHTML`.

### Tool Evaluation

| Tool | Recommendation |
|------|----------------|
| pip-audit | **KEEP** — CI with explicit venv path; fail on starlette/aiohttp/urllib3/requests |
| ruff check | **KEEP** — optional `S` band rules for security linting |
| bun audit | **KEEP** — track vite/rollup if dev server exposed |

---

## 2. Performance

**Focus:** Hot paths, memory, I/O efficiency, query patterns.

### Tool Output

#### `ruff check .` (backend)

18 issues (style/import only). Exit code 1.

#### `bun run build` (frontend)

```
dist/assets/index-CgCQDO_7.js         251.76 kB │ gzip: 63.76 kB
dist/assets/react-vendor-CRB3T2We.js  141.74 kB │ gzip: 45.45 kB
dist/assets/motion-DHNcsZu7.js        129.79 kB │ gzip: 42.78 kB
dist/assets/router-DYya4Q_G.js         37.65 kB │ gzip: 13.65 kB
dist/assets/radix-BNI6yzQO.js          32.75 kB │ gzip: 11.34 kB
dist/assets/index-CK8OSnVa.css         47.69 kB │ gzip:  8.74 kB

PWA precache: 32 entries (27403.32 KiB)  ← ~27 MB
```

#### Asset sizes

| File | Size |
|------|------|
| index-CgCQDO_7.js | 246K |
| motion-DHNcsZu7.js | 127K |
| react-vendor-CRB3T2We.js | 138K |
| router-DYya4Q_G.js | 37K |
| radix-BNI6yzQO.js | 32K |
| index-CK8OSnVa.css | 47K |

### Findings

| # | Tag | Severity | Location | Finding |
|---|-----|----------|----------|---------|
| 1 | MANUAL | CRITICAL | `frontend/vite.config.ts:34-37` + PWA | ~27 MB SW precache. `globPatterns` pulls `public/locations` (~21 MB) and `public/portraits` (~9.6 MB) into install-time precache |
| 2 | MANUAL | HIGH | `helpers.py:456-464` | `save_slot_state` hot path: `json.dumps(state.model_dump(...))` + `model_copy(deep=True)` — two full-tree walks + large JSON string per action |
| 3 | MANUAL | HIGH | `investigation.py:108-113, 328`, `witnesses.py:473-474` | Sync blocking on async routes: `load_case_or_404`, `load_slot_state`, `resolve_location` on event loop (no `to_thread`) |
| 4 | MANUAL | HIGH | `investigation.py:444`, `witnesses.py:451` | SSE `done` ships full `updated_state` via `model_dump(mode='json')` on every stream end |
| 5 | MANUAL | HIGH | `persistence.py:198-253` | `list_player_saves` / `get_save_metadata`: up to 4 sequential queries, each `json.loads` of full `state` TEXT |
| 6 | MANUAL | HIGH | `player_state.py:482-496` | `MatthewCompanionState.conversation_history` has no cap (unlike witness 50, narrator 5/location) |
| 7 | MANUAL | MEDIUM | `helpers.py:443-447` vs `464` | Cache-hit returns aliased `PlayerState` — perf win, correctness tradeoff under concurrency |
| 8 | MANUAL | MEDIUM | `investigation.py:66-69, 560-573` | `list_locations(case_data)` called twice per investigate |
| 9 | MANUAL | MEDIUM | `investigation.py:395`, `witnesses.py:413` | Per-chunk `json.dumps({'text': chunk})` on SSE — many small allocations |
| 10 | MANUAL | MEDIUM | `spell_detection.py:534-548` | Priority 3.5: `fuzz.ratio(text_lower, phrase)` on entire player input × phrases |
| 11 | MANUAL | MEDIUM | `location/parser.py:199-211` | `_fuzzy_match`: nested loops with `SequenceMatcher` per pair — O(locations × tokens²) |
| 12 | MANUAL | MEDIUM | `helpers.py:377-403` | Post-LLM secret detection: sliding-window overlap per unrevealed secret |
| 13 | MANUAL | MEDIUM | `player_state.py:657-673, 543-548` | Dual history stores: global `conversation_history` (50) + per-location `location_chat_history` (30 each) |
| 14 | MANUAL | MEDIUM | `useWitnessInterrogation.ts:315-316` | `APPEND_LAST_RESPONSE` per SSE chunk → reducer dispatch every token → re-renders |
| 15 | MANUAL | MEDIUM | `frontend/public/music` (~180 MB) | Music excluded from precache by 5MB cap (good); runtime CacheFirst still allows large MP3 pulls |
| 16 | MANUAL | LOW | `investigation.py:54-69` | New `LocationCommandParser` per request |
| 17 | MANUAL | LOW | `witness.py:77` | Prompt uses last 20 exchanges; state retains 50 |
| 18 | MANUAL | LOW | `persistence.py:129` | `conn.commit()` on every save — correct for durability; no debounced autosave |
| 19 | TOOL | LOW | Ruff E402 | Mid-file imports in `helpers.py` — style only |

### `model_copy(deep=True)` removal impact

- **Removed on cache read:** avoids O(state size) copy on every cache hit
- **Still on every save:** `save_slot_state:464` deep-copies into cache
- **Net:** read path optimized; write path remains expensive boundary

### Tool Evaluation

| Tool | Recommendation |
|------|----------------|
| ruff | No perf signal — style only |
| bun build + ls | **KEEP** — PWA precache ~27 MB is standout signal |

### Suggested priority

1. Narrow PWA `globPatterns` / exclude heavy `public/locations` & `portraits` from precache
2. Slim SSE `done` payload (deltas or omit `updated_state`)
3. Reduce save-path double serialization
4. Cap Matthew/briefing histories
5. Metadata-only SQL for save list
6. `to_thread` for sync setup on stream endpoints

---

## 3. Error Handling

**Focus:** Panics, swallowed errors, recovery, user-facing messages.  
**Tools:** None — pure manual review.

### Findings

| # | Tag | Severity | Location | Finding |
|---|-----|----------|----------|---------|
| 1 | MANUAL | CRITICAL | `persistence.py:167-171` | `load_player_state` re-raises only `ValueError`; other failures (`JSONDecodeError`, `ValidationError`) logged and return `None`. Callers can't tell corrupt vs missing save |
| 2 | MANUAL | CRITICAL | `useInvestigation.ts:176-189` | On load failure (including HTTP 400), hook still calls `setState(createDefaultState())` — user can overwrite corrupt DB row |
| 3 | MANUAL | HIGH | `investigation.py:440-442` | Post-LLM failures caught with bare `except Exception`; SSE generator returns without `done` or structured error (unlike `witnesses.py:446-448`) |
| 4 | MANUAL | HIGH | `helpers.py:444-447` | `load_slot_state` returns cached ref — failed mutations leave inconsistent cache |
| 5 | MANUAL | HIGH | `saves.py:78-81` | Save failures return HTTP 200 + `success: false`; frontend never inspects `success` |
| 6 | MANUAL | HIGH | `investigation.py:564-565`, `witnesses.py:537-538` | All `ClaudeClientError` subclasses map to generic 503 — can't distinguish auth vs rate limit vs server down |
| 7 | MANUAL | HIGH | `briefing.py:112-117, 136-150` | `load_case` failures become empty context; `ask_briefing_question` has no LLM error handling |
| 8 | MANUAL | MEDIUM | `persistence.py:238-240` | `get_save_metadata` swallows all exceptions → corrupt slots disappear from list |
| 9 | MANUAL | MEDIUM | `saves.py:121-155` | Corrupt load split: `ValueError` → 400; swallowed errors → 200 + `null` |
| 10 | MANUAL | MEDIUM | `base.ts:413-417, 420-422` | `streamSSE` doesn't retry after 401; non-OK errors only pass `HTTP ${status}` without parsing `detail` |
| 11 | MANUAL | MEDIUM | `base.ts:109-112` | Post-401 `bootstrapSession().catch(() => {})` swallows bootstrap failures |
| 12 | MANUAL | MEDIUM | `investigation.py:396-408` | Stream LLM errors emit generic message — no auth/rate-limit/timeout distinction |
| 13 | MANUAL | MEDIUM | `persistence.py:193-195` | `delete_player_save` catches all exceptions, returns `False` (same as not found) |
| 14 | MANUAL | MEDIUM | `test_save_slots.py:327-335` | Test gap: invalid JSON / `ValidationError` integration not covered |
| 15 | MANUAL | LOW | `main.py:134-135` | Health check swallows DB errors — reports `degraded` without why |
| 16 | MANUAL | LOW | `llm_client.py:371-378` | Telemetry metric extraction uses bare `except Exception: pass` |
| 17 | MANUAL | LOW | `saves.py:80-81` | User-facing save messages may include internal exception text |
| 18 | MANUAL | LOW | `useSaveSlots.ts:77-80` | `loadFromSlot` returns `null` for both no save and any error |

### Architecture summary

Persistence is the weak link: broad swallow → `None` masks corruption. Upper layers treat `None` as "new game" → silent overwrite. HTTP semantics inconsistent (200 + `success: false` vs 400 vs 503). Frontend doesn't honor `success: false` on saves. LLM degradation uneven across routes.

---

## 4. Concurrency

**Focus:** Races, deadlocks, lock contention, shared state.  
**Tools:** None — pure manual review.

### Findings

| # | Tag | Severity | Location | Finding |
|---|-----|----------|----------|---------|
| 1 | MANUAL | CRITICAL | `helpers.py:443-447` | Removing `model_copy(deep=True)` on cache hit — concurrent handlers mutate one `PlayerState` |
| 2 | MANUAL | CRITICAL | `helpers.py:420-474` + routes | `_state_cache` has no lock; accessed from event loop + `asyncio.to_thread` |
| 3 | MANUAL | CRITICAL | `helpers.py:443-452` | TOCTOU on cache populate: two concurrent first-loads → last-write-wins |
| 4 | MANUAL | CRITICAL | `verdict.py:62-66, 97, 164` | Check-then-act on `verdict_state.attempts_remaining` — double-decrement possible |
| 5 | MANUAL | HIGH | `persistence.py:43-54, 119-129` | Single global SQLite connection, `check_same_thread=False`, no app mutex |
| 6 | MANUAL | HIGH | `saves.py:50-70` vs `helpers.py` | `/api/save` bypasses `_state_cache` — stale cache vs DB |
| 7 | MANUAL | HIGH | `saves.py:130` vs `helpers.py:443-447` | `/api/load` bypasses cache — mid-flight reads disagree |
| 8 | MANUAL | HIGH | `investigation.py:318-450`, `witnesses.py:463+` | Multiple SSE streams same `player_id` interleave mutations |
| 9 | MANUAL | HIGH | `conftest.py:13, 102-115` + xdist | Fixed `lantern_test.db` path; xdist workers share one DB without worker-scoped paths |
| 10 | MANUAL | MEDIUM | `helpers.py:427-433` | LRU `pop`/`del`/`assign` without synchronization |
| 11 | MANUAL | MEDIUM | `persistence.py:99-130` | No optimistic concurrency (version/`updated_at` check on write) |
| 12 | MANUAL | MEDIUM | `test_concurrency_state.py:16-19` | Async httpx tests don't reproduce SQLite connection races from thread pool |
| 13 | MANUAL | LOW | `concurrency_helpers.py:169-171` | Docstring still references `_mem_store` |
| 14 | MANUAL | LOW | `conftest.py:28-92` | Dead `_mem_store` mocks remain after SQLite migration |
| 15 | MANUAL | LOW | `rate_limit.py:7-18` | slowapi limiter process-local; multi-worker gets per-process limits |

### Deep-copy removal verdict

**Yes — concurrency bug**, not a safe performance tradeoff. Cache is a mutable singleton per key; saves refresh cache with copy but callers keep aliasing.

---

## 5. Architecture

**Focus:** Scalability, coupling, atomicity, data integrity.  
**Tools:** None — pure manual review.

### Findings

| # | Tag | Severity | Location | Finding |
|---|-----|----------|----------|---------|
| 1 | MANUAL | CRITICAL | `helpers.py:443-447` | `load_slot_state` returns same mutable `PlayerState` instance |
| 2 | MANUAL | CRITICAL | `saves.py:130-138` | `GET /load` never calls `invalidate_state_cache` — stale autosave after named-slot load |
| 3 | MANUAL | HIGH | `saves.py:39-70` | `POST /save` bypasses `save_slot_state` / cache entirely |
| 4 | MANUAL | HIGH | `saves.py:55-66` | Autosave merge only patches thin client slice — partial saves possible |
| 5 | MANUAL | HIGH | `verdict.py:47-97` | Read-modify-write with no versioning/locking |
| 6 | MANUAL | HIGH | `persistence.py:46-54` | Single process-global sqlite3 connection shared across `asyncio.to_thread` |
| 7 | MANUAL | HIGH | `base.ts:103-110` + `session.py:54-56` | 401 clears `player_id` → new anonymous player → orphaned saves |
| 8 | MANUAL | HIGH | `loader.py:27-59` vs `461-616` | `load_case()` doesn't run `validate_case()` — invalid YAML at runtime |
| 9 | MANUAL | MEDIUM | `loader.py:116-120` | `get_location()` mutates cached case dicts in-place |
| 10 | MANUAL | MEDIUM | `helpers.py:681-691` | `find_witness_for_mnemonic_delving` iterates dict; witnesses are a list |
| 11 | MANUAL | MEDIUM | `helpers.py:641` | `from backend.src.spells.definitions` — deployment-path smell |
| 12 | MANUAL | MEDIUM | `persistence.py:281-286` | `migrate_old_save()` is no-op despite `PlayerState.version` |
| 13 | MANUAL | MEDIUM | `persistence.py:218-220` | `get_save_metadata` hardcodes `total_evidence = 15` |
| 14 | MANUAL | MEDIUM | `evidence.py:50-60` | `get_evidence_details` scans all hidden evidence — O(locations × evidence × discovered) |
| 15 | MANUAL | MEDIUM | `matthew.py:32-38` | Full-case evidence scan on each Matthew context build |
| 16 | MANUAL | MEDIUM | `investigation.py:108-142` | Route slice grew into orchestration monolith (~587 lines) |
| 17 | MANUAL | MEDIUM | `witnesses.py` (~741 lines) | Witness prep, streaming, trust, mnemonic redirect in one module; layering cycle with `mnemonic_delving` |
| 18 | MANUAL | MEDIUM | `investigation.py:411-442` | Stream sends `done` after in-memory mutation; if `save_slot_state` fails, client shows discoveries not durable |
| 19 | MANUAL | MEDIUM | `types/investigation.ts` vs `schemas.py` | Frontend documents optional `player_id`; backend uses `X-Player-Token` only |
| 20 | MANUAL | MEDIUM | `schemas.ts` vs backend | Duplicate/overlapping save response schemas |
| 21 | MANUAL | MEDIUM | `App.tsx` (~711 lines) | Orchestration remains component-adjacent |
| 22 | MANUAL | MEDIUM | `telemetry.ts:136-139` | `session_end` sendBeacon without auth headers; server requires auth |
| 23 | MANUAL | LOW | `helpers.py:464` | Asymmetric defensive copying: deep copy on save, shared ref on load |
| 24 | MANUAL | LOW | `telemetry/logger.py:69-78` | Fire-and-forget telemetry; no backpressure with SQLite save volume |
| 25 | MANUAL | LOW | `loader.py:143` | `get_first_location_id` uses `next(iter(locations))` — YAML key order defines spawn |
| 26 | MANUAL | LOW | `useInvestigation.ts:280-291` | `updated_state` merges fixed field subset only |

### Architecture strengths

- Clear vertical slices under `api/routes/`
- SQLite + WAL + upsert for single-row atomic writes
- Case YAML with mtime cache and path sanitization
- Session hardening prevents naive `existing_player_id` takeover
- Frontend `api/` with Zod `.strict()` on responses
- Hooks decomposition moves logic out of presentation

### Systemic risks

| Risk | Nature |
|------|--------|
| Dual store without coherence | In-memory LRU + SQLite with three write paths, selective invalidation |
| Shared mutable session state | One cached `PlayerState` per key without copy-on-read or optimistic concurrency |
| Authoritative server / thin client | Manual save + cache breaks merge story |
| LLM-bound transactions | Long awaits between load and save with no row version |
| Case content as live cache | YAML cache + in-place mutation + no validate-on-load |
| Identity ↔ persistence | Token expiry clears `player_id` → saves not recoverable |
| Scale ceiling | Per-request full evidence/witness scans; monolithic route modules |

---

## 6. API / CLI Ergonomics

**Focus:** User experience, discoverability, output format.  
**Tools:** None — pure manual review.

### Findings

| # | Tag | Severity | Location | Finding |
|---|-----|----------|----------|---------|
| 1 | MANUAL | CRITICAL | `persistence.py:169-171` | Corrupted SQLite JSON → `None` → 200 + `null` — indistinguishable from no save |
| 2 | MANUAL | CRITICAL | `saves.py:50-53` | Named-slot save snapshots autosave only, ignoring `request.state` |
| 3 | MANUAL | CRITICAL | `base.ts:45-52` + `session.py:54-56` | Session bootstrap without `current_token` always mints new `player_id` — orphaned saves |
| 4 | MANUAL | HIGH | `useInvestigation.ts:182-189` | Load failure sets default state — playable overwrite of corrupt saves |
| 5 | MANUAL | HIGH | `useSaveSlots.ts:54-56` + `saves.py:71-77` | Save `success: false` treated as success in frontend |
| 6 | MANUAL | HIGH | `base.ts:420-422` | SSE errors show `HTTP ${status}` without parsing `detail` |
| 7 | MANUAL | HIGH | `investigation.py:440-442` | SSE persistence failure → "Connection lost" with no "not saved" message |
| 8 | MANUAL | HIGH | `useGameActions.ts:108-117` + `App.tsx` | Briefing errors never rendered — silent skip of first-run tutorial |
| 9 | MANUAL | HIGH | `useGameActions.ts:121-123` + `App.tsx:449` | Closing briefing modal always marks complete — no resume path |
| 10 | MANUAL | MEDIUM | `verdict.py:63-65` | Exhausted-attempts message wording easy to misread |
| 11 | MANUAL | MEDIUM | `saves.ts`, witnesses, briefing, investigation | Dead `player_id` query params still appended |
| 12 | MANUAL | MEDIUM | `base.ts:188-198` | 422 validation arrays produce useless error messages |
| 13 | MANUAL | MEDIUM | `settings.ts:59-65` + `SettingsModal.tsx` | BYOK saved without successful verify |
| 14 | MANUAL | MEDIUM | `base.ts:145-151` vs SettingsModal | Runtime LLM calls send only key + model; provider used for verify only |
| 15 | MANUAL | MEDIUM | `saves.py:121-133` | Missing save returns 200 + `null` rather than 404 |
| 16 | MANUAL | MEDIUM | `playerId.ts` vs `base.ts` | `usePlayerId()` can expose UUID before `ensureSession()` overwrites |
| 17 | MANUAL | MEDIUM | `investigation.py:396-408` | Stream LLM errors all return same generic string |
| 18 | MANUAL | LOW | `main.py:49-52` | OpenAPI title still "HP Game Backend" |
| 19 | MANUAL | LOW | `saves.py:158-166` | DELETE only removes autosave, not manual slots |
| 20 | MANUAL | LOW | `types/investigation.ts` vs `base.ts` | Duplicate `isApiError` with different strictness |
| 21 | MANUAL | LOW | `base.ts:86-88` | Session refresh toast doesn't mention in-flight streams won't retry |
| 22 | MANUAL | LOW | `SaveLoadModal.tsx:279-298` | Import shows generic error on server `success: false` |
| 23 | MANUAL | LOW | `main.py:58-70` | 8 KB body cap may reject long verdict reasoning with 413 |

**Summary:** 23 findings — 3 Critical, 6 High, 8 Medium, 6 Low.

---

## 7. Testability

**Focus:** Untestable code, missing coverage, coupling.  
**Tools:** None — pure manual review.

### Findings

| # | Tag | Severity | Location | Finding |
|---|-----|----------|----------|---------|
| 1 | MANUAL | HIGH | `conftest.py:102-115` + `helpers.py:420-447` | `_state_cache` not cleared between tests — only DB truncated; order-dependent flakes |
| 2 | MANUAL | HIGH | `concurrency_helpers.py:166-171` | `bypass_state_cache` docstring says `_mem_store`; helper unused |
| 3 | MANUAL | HIGH | `conftest.py:28-88` + `test_save_slots.py:317-337` | Orphan `_mem_store` mocks after SQLite migration |
| 4 | MANUAL | HIGH | `test_save_slots.py:361-394` | Corrupt-row silent path not integration-tested (`JSONDecodeError` → `None`) |
| 5 | MANUAL | HIGH | `witnesses.py:24`, `mnemonic_delving.py:14`, `test_routes.py` | Dual `patch` for `get_client` at two import sites — fragile |
| 6 | MANUAL | HIGH | `test_concurrency_state.py:344-361` | Race tests scheduler-dependent with weak assertions |
| 7 | MANUAL | MEDIUM | `test_concurrency_state.py:14-19` | References non-existent `*_real_db` tests |
| 8 | MANUAL | MEDIUM | `helpers.py:436-464` | No test that two `load_slot_state` calls after save are isolated |
| 9 | MANUAL | MEDIUM | `mnemonic_delving.py:67-79` | `random` not patched in route tests |
| 10 | MANUAL | MEDIUM | `test_llm_byok.py:142-144` | Fixture docstring inaccurate after real SQLite |
| 11 | MANUAL | MEDIUM | `saves.py:130` vs `helpers.load_slot_state` | No integration test for cache vs `/api/load` consistency |
| 12 | MANUAL | MEDIUM | `persistence.py:43-48` + xdist | Single SQLite connection + shared DB path — xdist isolation gap |
| 13 | MANUAL | LOW | `reproduce_issue.py`, `reproduce_persistence.py` | Stale patches; brittle if executed |
| 14 | MANUAL | LOW | `useWitnessInterrogation.test.ts:34` | `isApiError` mocked to always `false` |
| 15 | MANUAL | LOW | `SaveLoadModal.test.tsx` | No tests for corrupt load, empty slot, concurrent save |
| 16 | MANUAL | LOW | `player_state.py:19-21` | `_utc_now()` — no injectable clock |

### Concurrency tests after SQLite migration

| Area | Valid? | Notes |
|------|--------|-------|
| `seed_state` / `load_state_direct` | Yes | Real SQLite on test DB |
| Shared `_state_cache` races | Yes | Primary signal in concurrency tests |
| investigate vs interrogate dual load paths | Yes | SQLite doesn't fix clobber |
| SQLite connection/thread races | No | Documented; no `*_real_db` tests |
| `bypass_state_cache` | Unused | Would mean cache off, SQLite on |

### Coverage gaps summary

| Gap | Severity |
|-----|----------|
| Autouse `_state_cache` clear with DB truncate | HIGH |
| Behavioral corrupt JSON → silent `None` + route behavior | HIGH |
| Single dependency seam for `get_client` | HIGH |
| Cache vs `load_player_state` / invalidation integration | MEDIUM |
| `bypass_state_cache` + post-deep-copy cache semantics | MEDIUM |
| Multi-worker / per-test DB path for xdist | MEDIUM |
| Deterministic mnemonic detection/trust (inject `random`) | MEDIUM |
| Frontend: corrupt load, save-during-action, hook API errors | LOW |
| Injectable time for `PlayerState` timestamps | LOW |
| Race tests as strict CI gates | HIGH (flakiness risk if promoted) |

---

## 8. Dead Code & Dependencies

**Focus:** Unused code, stale imports, dependency bloat.

### Tool Output

#### `vulture src/ --min-confidence 80`

```
src/api/helpers.py:356: unused variable 'lookback_chars' (100% confidence)
```

#### `ruff check . --select F401,F841`

```
F401: asyncio imported but unused → saves.py:3, telemetry.py:3
F841: evil_id assigned but never used → test_auth_baseline.py:217
F401: _mem_store imported but unused → test_save_slots.py:337
```

#### `bun run lint` (frontend)

Exit code 0 — no ESLint issues.

#### `bun pm ls` (repo root)

Only lists root `vite-imagetools@9.0.2` — not useful for frontend dep audit.

### Findings

| # | Tag | Severity | Location | Finding |
|---|-----|----------|----------|---------|
| 1 | MANUAL | HIGH | `gameFeatures.ts:6`, `BriefingModal.tsx:91-144` | `SKIP_BRIEFING_CALIBRATION_AND_ENGAGEMENT = true` — dead briefing UI paths |
| 2 | MANUAL | MEDIUM | `helpers.py:356` | `is_affirmative_mention()` never referenced; unused `lookback_chars` |
| 3 | TOOL | MEDIUM | `saves.py:3` | Unused `asyncio` import |
| 4 | TOOL | MEDIUM | `telemetry.py:3` | Unused `asyncio` import |
| 5 | MANUAL | MEDIUM | `pyproject.toml:57` | Ruff excludes `routes_old.py` — file not in repo (ghost exclude) |
| 6 | MANUAL | MEDIUM | root + frontend | Duplicate `vite-imagetools` (root ^9.0.2 vs frontend ^9.0.3) |
| 7 | MANUAL | MEDIUM | `package-lock.json` + `bun.lock` | Dual lockfiles; npm pins older framer-motion |
| 8 | MANUAL | LOW | `HypothesisRelevanceBadge.tsx` | Deprecated stub; no imports |
| 9 | MANUAL | LOW | `frontend/CLAUDE.md:37` | Documents `enhanced.ts` stubs; file removed |
| 10 | MANUAL | LOW | `investigation.ts:461-468`, `schemas.ts:329-331` | Deprecated briefing fields; no app usage |
| 11 | TOOL | LOW | `test_auth_baseline.py:217` | Unused `evil_id` |
| 12 | TOOL | LOW | `test_save_slots.py:337` | Unused `_mem_store` import |

**Heavy deps (justified):** litellm (core BYOK), rapidfuzz (spell_detection), framer-motion (5 UI modules).

**Not found:** `routes_old.py`, `frontend/src/types/enhanced.ts` (already gone).

### Tool Evaluation

| Tool | Recommendation |
|------|----------------|
| vulture | **KEEP** — caught unused symbol Ruff missed |
| ruff F401/F841 | **KEEP** |
| eslint | **KEEP** — slow (~2 min); consider scoped runs |
| bun pm ls | **SKIP** for dead-code review |

### Quick wins

- Remove `asyncio` imports (ruff `--fix`)
- Drop or implement `lookback_chars` / remove `is_affirmative_mention`
- Delete `HypothesisRelevanceBadge.tsx` or wire it
- Remove `routes_old.py` from `pyproject.toml`
- Consolidate `vite-imagetools` to frontend only
- Delete or gitignore stale `package-lock.json` if Bun is canonical

---

## 9. API Design

**Focus:** Public interfaces, abstraction quality, consistency.  
**Tools:** None — pure manual review.

### Findings

| # | Tag | Severity | Location | Finding |
|---|-----|----------|----------|---------|
| 1 | MANUAL | CRITICAL | `helpers.py:436-447` | `load_slot_state` returns shared ref — undocumented ownership semantics |
| 2 | MANUAL | CRITICAL | `saves.py:130-138` vs `helpers.py` | Dual persistence paths; cache not part of public contract |
| 3 | MANUAL | HIGH | `schemas.py:54,234,365,432,494` + `schemas.ts` | `updated_state` is untyped `dict[str, Any]` — no shared DTO or versioning |
| 4 | MANUAL | HIGH | `schemas.py:112-121` | Two incompatible state shapes: `StateResponse` subset vs full `updated_state` |
| 5 | MANUAL | HIGH | `saves.ts:27-30`, investigation, types | Dead `player_id` in frontend; server uses auth header only |
| 6 | MANUAL | HIGH | `schemas.py:33-36` vs `persistence.py:26-27` | Slot validation mismatch: API accepts any pattern; persistence only `VALID_SLOTS` |
| 7 | MANUAL | HIGH | Save response schemas | Pydantic↔Zod drift: `message`/`slot` optional vs required; wrong schema used in `saveGameState` |
| 8 | MANUAL | HIGH | `types/investigation.ts:48-55` | TS `InvestigateResponse` omits `evidence_names`, `location_changed`, `updated_state` |
| 9 | MANUAL | MEDIUM | `player_state.py:530-565` | `PlayerState` is god struct on API boundary |
| 10 | MANUAL | MEDIUM | `helpers.py:419, 566-580, 602-612` | Tuple aliases hide semantics; 11-param `save_conversation_and_return` |
| 11 | MANUAL | MEDIUM | `helpers.py:580` | `resolve_location` bogus `player_id` fallback `"default"` |
| 12 | MANUAL | MEDIUM | Route layout | REST inconsistent: flat verbs vs case-scoped paths |
| 13 | MANUAL | MEDIUM | Slot placement | Body vs query param inconsistently across routes |
| 14 | MANUAL | MEDIUM | `witnesses.py:304, 358` | Misleading return types; `Any` for witness state |
| 15 | MANUAL | MEDIUM | `schemas.py:447-460` | Legacy InnerVoice names on live Matthew endpoints |
| 16 | MANUAL | MEDIUM | `schemas.py:564-569` | `ChangeLocationResponse.location: dict[str, Any]` vs typed `LocationResponse` |
| 17 | MANUAL | MEDIUM | `schemas.py:62-70` + `saves.py:55-68` | `SaveRequest` merge semantics implicit; frontend `InvestigationState` tiny subset |
| 18 | MANUAL | LOW | `llm_client.py:397-409` | Module singleton `get_client()` — no injectable interface |
| 19 | MANUAL | LOW | `investigation.py:28-29` | `ClaudeClientError` alias confusing |
| 20 | MANUAL | LOW | `routes/__init__.py:34-48` | Re-export blurs HTTP package vs test convenience |
| 21 | MANUAL | LOW | Timestamp shapes | int ms vs string timestamps across wire formats |

### API design strengths

- Central contract modules: `schemas.py` + `schemas.ts` with `.strict()` Zod
- Auth dependency keeps player identity out of request bodies
- BYOK as typed `UserLLMConfig` dependency
- Workflow DTOs: `InvestigationContext`, `WitnessPrep`
- Domain-split frontend clients mirror backend route groupings
- `LLMClient` consistent interface with classified errors
- Input bounds on player text across endpoints
- `SaveSlotMetadata` purposeful list DTOs for slot picker UI

---

## Priority Action List

| Priority | Action | Reviews affected |
|----------|--------|------------------|
| P0 | Restore `model_copy(deep=True)` on `load_slot_state` cache hit | Concurrency, Security, Architecture, Error Handling, API Design, Testability |
| P0 | Unify corrupt-save handling — surface corruption to client; frontend refuse default state on 4xx load | Error Handling, Ergonomics, Testability |
| P1 | Cache coherence — `invalidate_state_cache` on `/api/load` and `/api/save` | Architecture, Concurrency, API Design |
| P1 | Upgrade dependencies — starlette, aiohttp, urllib3, requests; vite/rollup | Security |
| P1 | Fix save UX — check `success: false`; align named-slot save semantics with UI | Ergonomics, Error Handling |
| P2 | Narrow PWA precache — exclude heavy `public/locations` and `portraits` | Performance |
| P2 | Autouse `_state_cache.clear()` in conftest | Testability |
| P3 | Dead-code cleanup — unused imports, orphan files, stale `_mem_store` refs | Dead Code |

---

## Tool Summary (adapted for this stack)

| Tool | Install | Speed | Value this run | Keep? |
|------|---------|-------|----------------|-------|
| pip-audit | `uv add --dev pip-audit` | instant | 41 real CVEs | YES (fix venv path) |
| bun audit | built-in | instant | 20 dev-dep advisories | YES |
| vulture | `uv add --dev vulture` | ~1s | 1 unused symbol | YES |
| ruff | built-in | ~3s | Style + unused imports | YES |
| eslint | built-in | ~2 min | Clean | YES |
| bun build | built-in | ~53s | 27 MB precache signal | YES |
| bun pm ls | built-in | instant | Not useful at root | SKIP |

**Key insight:** Tools caught dependency CVEs and hygiene issues. All actionable logic, architecture, and semantic findings (cache aliasing, corrupt-save paths, dual-store drift, save semantics) came from manual LLM review across multiple lenses.

---

## Uncommitted Diff Reviewed

```
backend/src/api/helpers.py           — removed deep copy on cache hit
backend/tests/concurrency_helpers.py — SQLite instead of _mem_store
backend/tests/test_llm_byok.py       — model name user/model
backend/tests/test_routes.py         — dual mnemonic_delving patches
backend/tests/test_save_slots.py     — corrupt save via SQLite INSERT
```