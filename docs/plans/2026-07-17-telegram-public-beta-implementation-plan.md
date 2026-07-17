# Telegram Public Beta — Implementation Plan

**Status:** Approved design, ready for implementation
**Target:** Small public beta
**Production host:** `bot.thelantern.institute`
**Core stack:** Bun + Hono + grammY + Vite + React; existing FastAPI game engine remains authoritative

## 1. Product Contract

Build a second client for The Lantern. Do not replace or redesign the existing web game.

- Solo play in private Telegram DMs only.
- One bot owns all cases. New players enter free `case_001` directly; no first-run case picker.
- Preserve Case 1 exactly: same four locations, four witnesses, evidence, rites, pacing, culprit, and verdict logic.
- Investigation and witness questions use freeform Telegram messages.
- Player explicitly enters witness mode; all text targets that witness until `End Interview`.
- One Mini App exposes four routes: Casebook, Evidence, Witnesses, Verdict.
- Menu button opens Casebook. Narrator/witness messages carry contextual inline buttons.
- Keep occult rites as natural-language actions.
- Keep only autosave. Exclude Matthew, music, manual save slots, visible trust, settings UI, groups, sharing, reminders, live-response drafts, HTML5 Games API, and Stars checkout.
- English and Russian only. Static player-facing copy is checked in for both languages; dynamic LLM narration/dialogue follows saved language.
- Use existing location and witness images once per player on first visit/contact. Do not duplicate source image files in repository.
- Server-funded LLM. Limit each player to 40 LLM turns per UTC day. Read-only views and navigation remain usable after cap.
- First future paid case uses Telegram Stars, but v1 implements entitlement data only.
- Primary beta funnel: `start -> first clue -> first interview -> first verdict -> solve`.

## 2. Required Reading Before Coding

Coding agent must read these sources in order. Do not rely on this plan alone when source code disagrees.

### Repository references

1. [`CLAUDE.md`](../../CLAUDE.md) — project limits, Bun/UV commands, TDD, Zod strictness, Git rules.
2. [`STATUS.md`](../../STATUS.md) — current branch state and pre-existing failures. Do not attribute existing failures to Telegram work.
3. [`backend/CLAUDE.md`](../../backend/CLAUDE.md) — engine architecture, state, LLM, rate-limit, error conventions.
4. [`frontend/CLAUDE.md`](../../frontend/CLAUDE.md) — React/Zod/testing conventions. Reuse patterns, not current desktop layout.
5. [`backend/src/api/schemas.py`](../../backend/src/api/schemas.py), [`backend/src/api/auth.py`](../../backend/src/api/auth.py), and [`backend/src/api/dependencies.py`](../../backend/src/api/dependencies.py) — current API/auth contracts.
6. [`backend/src/state/persistence.py`](../../backend/src/state/persistence.py) and [`backend/src/state/player_state.py`](../../backend/src/state/player_state.py) — SQLite, optimistic revisions, autosave, language state.
7. [`backend/src/api/routes/investigation.py`](../../backend/src/api/routes/investigation.py), [`backend/src/api/routes/witnesses.py`](../../backend/src/api/routes/witnesses.py), [`backend/src/api/routes/verdict.py`](../../backend/src/api/routes/verdict.py), [`backend/src/api/routes/saves.py`](../../backend/src/api/routes/saves.py), and [`backend/src/api/routes/briefing.py`](../../backend/src/api/routes/briefing.py) — endpoints gateway will call.
8. [`backend/src/case_store/case_001.yaml`](../../backend/src/case_store/case_001.yaml) and [`docs/case-files/CASE_DESIGN_GUIDE.md`](../case-files/CASE_DESIGN_GUIDE.md) — canonical case IDs/content. Never translate or alter IDs/tags.
9. [`docker-compose.yml`](../../docker-compose.yml), [`deploy.sh`](../../deploy.sh), and [`Dockerfile.backend`](../../Dockerfile.backend) — current single-server deployment and proxy network.

### External references

1. [Telegram Bot API](https://core.telegram.org/bots/api) — updates, webhooks, callback queries, buttons, message limits.
2. [Telegram Mini Apps](https://core.telegram.org/bots/webapps) — `initData` validation, launch modes, theme variables, safe areas, Back/Main buttons.
3. [Telegram webhook guide](https://core.telegram.org/bots/webhooks) — HTTPS and webhook setup.
4. [Telegram digital-goods payments](https://core.telegram.org/bots/payments-stars) — future entitlement boundary; digital goods must use Stars.
5. [grammY deployment guide](https://grammy.dev/guide/deployment-types.html) — long polling locally, Hono webhook adapter in production.
6. [Hono on Bun](https://hono.dev/docs/getting-started/bun) — Bun server and static-file serving.

## 3. Target Architecture

```text
Telegram client
  |-- message/callback update --> Hono + grammY webhook
  |                               |-- durable SQLite job queue
  |                               |-- Telegram mode/usage/entitlement state
  |                               `-- internal FastAPI client
  |
  `-- Mini App WebView ---------> Hono Mini App API
                                  |-- validates Telegram initData
                                  |-- serves Vite/React build
                                  `-- calls same FastAPI client

Hono/grammY gateway -----------> existing FastAPI API -----------> LiteLLM
                                           |
                                           `-- existing Lantern SQLite autosave
```

FastAPI remains source of truth for case progress, evidence, witnesses, trust, locations, briefing, verdict, and LLM output. Gateway owns Telegram identity, chat mode, delivery jobs, daily allowance, localization presentation, and future case entitlements.

## Phase 1 — Engine Contracts and Idempotency Foundation

### Goal

Make existing FastAPI safe for durable Telegram jobs without changing current web behavior.

### Implementation

1. Add optional `request_id` to these mutation contracts:
   - `InvestigateRequest`
   - `InterrogateRequest`
   - `PresentEvidenceRequest`
   - `SubmitVerdictRequest`
   - `ChangeLocationRequest`
   - briefing completion request; replace current query-only mutation with body model while keeping old call compatible
   - settings language update used during onboarding
2. Validate `request_id` as opaque ASCII, maximum 128 characters. Missing value preserves current behavior.
3. Add backend idempotency service keyed by `(player_id, operation, request_id)`:
   - `in_progress`: duplicate returns `409 request_in_progress`.
   - `completed`: duplicate returns original status/body without rerunning LLM or state mutation.
   - `failed_before_mutation`: request may retry.
   - Keep records for 7 days; cleanup occurs opportunistically with a bounded delete, not a background scheduler.
4. Make completion atomic with autosave mutation where practical. At minimum, never automatically retry an ambiguous request after dispatch. Gateway treats transport timeout after dispatch as `unknown`, reloads state, and asks player to retry manually.
5. Add internal-only endpoint `GET /api/telegram/snapshot/{case_id}` returning one compact Telegram snapshot:
   - case ID, current location, visited locations, discovered evidence IDs
   - briefing completion, language, save revision
   - available witness IDs with canonical names
   - verdict attempts remaining and solved state
   - never expose hidden evidence, secrets, solution, internal prompts, or API keys
6. Reuse existing `POST /api/session` for fresh internal identity. Gateway stores returned player token; browser never sees it.
7. Confirm non-streaming endpoints remain fully functional. Telegram gateway must use `/investigate`, `/interrogate`, `/present-evidence`, and `/submit-verdict`; do not consume SSE because Telegram sends final replies only.
8. Add migration SQL file for idempotency records. Do not run it. Hand SQL to repository owner for execution.
9. Update Pydantic models first. Update existing frontend Zod schemas/types only where strict response validation would otherwise break; optional request-only fields must remain backward-compatible.

### Tests

- Duplicate completed request returns byte-equivalent domain response and performs one LLM call/save.
- Duplicate in-progress request returns deterministic 409 code.
- Same `request_id` from different players does not collide.
- Same ID on different operations does not collide.
- Requests without `request_id` retain existing behavior.
- Snapshot excludes undiscovered/solution data.
- Existing web route, save, witness, verdict, briefing, and schema tests still pass at baseline.

### Validation commands

```bash
cd backend
uv run pytest tests/test_routes.py tests/test_persistence.py tests/api
uv run pytest
uv run ruff check .
uv run mypy src/

cd ../frontend
~/.bun/bin/bun run type-check
~/.bun/bin/bun run test --run
~/.bun/bin/bun run build
```

### Exit gate and handoff

- API contract documented with sample request/response JSON.
- Migration SQL delivered but not executed by coding agent.
- Web client remains unchanged in behavior.
- No Telegram package work starts until idempotency and snapshot tests pass.

## Phase 2 — Durable Hono/grammY Gateway

### Goal

Create secure Telegram runtime, durable job processing, and engine adapter before gameplay polish.

### Planned structure

```text
telegram/
  package.json
  bun.lock
  tsconfig.json
  vite.config.ts
  src/server/                 # Hono entry, config, middleware, health
  src/bot/                    # grammY bot and handlers
  src/db/                     # bun:sqlite connection and repositories
  src/jobs/                   # durable queue and worker
  src/engine/                 # typed FastAPI client + Zod schemas
  src/domain/                 # modes, entitlements, usage, jobs
  src/i18n/                   # shared EN/RU bot strings
  app/                        # Vite/React Mini App, implemented Phase 4
  tests/
Dockerfile.telegram
```

Keep files below repository limits. Split handlers by concern; do not create one bot god-file.

### Implementation

1. Scaffold Bun package using only `~/.bun/bin/bun`. Add minimum dependencies:
   - runtime: `hono`, `grammy`, `zod`, `react`, `react-dom`, `react-router-dom`
   - dev: Vite React plugin, TypeScript, Vitest/testing-library equivalents already used by repository, ESLint
   - do not add grammY conversations plugin, Redis, BullMQ, ORM, Axios, Redux, or Telegram UI wrapper unless native WebApp API proves insufficient
2. Define validated environment config:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_WEBHOOK_SECRET`
   - `TELEGRAM_PUBLIC_URL=https://bot.thelantern.institute`
   - `TELEGRAM_DB_PATH=/app/data/telegram.db`
   - `MINIAPP_SESSION_SECRET`
   - `LANTERN_ENGINE_URL=http://backend:8000`
   - feature flags: new sessions enabled, LLM turns enabled
3. Create gateway migration SQL for:
   - users: Telegram ID, chat ID, internal player ID/token, language, timestamps
   - sessions: current case and `investigation | witness`, selected witness
   - usage: UTC date and LLM turn count
   - updates: Telegram update ID dedupe
   - jobs: update ID, request ID, payload, state, engine response, delivery metadata, attempts
   - entitlements: `(telegram_user_id, case_id, free|owned|locked)`
   - media receipts: first-seen location/witness image IDs
   Do not run SQL; give it to owner.
4. Webhook route:
   - production `POST /telegram/webhook`
   - verify `X-Telegram-Bot-Api-Secret-Token` before JSON parsing
   - allow only `message`, `callback_query`, and `my_chat_member`; add payment updates only when payments exist
   - store update/job transactionally, return 2xx quickly, process asynchronously
   - duplicate `update_id` returns 2xx without new job
5. Local entry uses grammY long polling and same middleware/handlers. Never run polling while production webhook is set.
6. Durable worker:
   - one active mutation per Telegram user; preserve arrival order
   - `pending -> running -> engine_complete -> delivered`
   - store engine response before Telegram delivery
   - retry Telegram delivery without repeating engine mutation
   - jobs left `running` before engine dispatch return to `pending` on restart
   - jobs marked dispatched with unknown result never auto-rerun; reload snapshot and notify player
7. Engine client:
   - create/refresh internal session token
   - send `X-Player-Token`; never forward bot token or Mini App data
   - Zod `.strict()` response schemas matching Pydantic
   - one refresh attempt on 401, no retry loop
   - explicit timeout and typed errors for 400/401/409/429/5xx/transport failure
8. Add `/health` with gateway DB, worker status, and engine reachability. Do not expose secrets or counts tied to individuals.
9. Add structured logs with update ID, request ID, operation, duration, and status. Never log player prose, raw prompts, bot token, internal player token, LLM key, or raw Mini App `initData`.

### Tests

- Invalid/missing webhook secret rejected before body handling.
- Duplicate Telegram update creates one job.
- Two messages from one user execute serially; different users can progress independently.
- Restart recovery follows job-state rules.
- Engine-complete response survives Telegram send failure and delivers without second engine call.
- Token refresh happens once.
- Daily usage increment is atomic.
- Entitlement defaults: `case_001=free`, every other case `locked` unless owned.
- Logs redact all listed secrets and prose.

### Validation commands

```bash
cd telegram
~/.bun/bin/bun install
~/.bun/bin/bun run test
~/.bun/bin/bun run type-check
~/.bun/bin/bun run lint
~/.bun/bin/bun run build
```

### Exit gate and handoff

- Synthetic Telegram updates can traverse webhook -> durable job -> mocked engine -> mocked Telegram delivery.
- Restart test proves no duplicate engine mutation.
- SQL and required environment variables handed to owner.
- No player-facing gameplay beyond `/start` placeholder required yet.

## Phase 3 — Chat-First Game Loop

### Goal

Deliver complete Case 1 through Telegram chat using existing engine behavior.

### State and routing rules

```ts
type ChatMode =
  | { kind: "investigation" }
  | { kind: "witness"; witnessId: string };
```

- `/start` resumes existing Telegram autosave. Fresh users choose `English` or `Russian`, receive free entitlement, create engine session, save language, receive cover/briefing, then tap `Begin Investigation`.
- Normal text in investigation mode calls `/api/investigate` with canonical `case_001`, current location, `autosave`, and stable job `request_id`.
- Normal text in witness mode calls `/api/interrogate` with selected canonical witness ID.
- Unsupported media receives one localized instruction: text actions/questions only.
- Commands and callbacks bypass LLM allowance unless they call an LLM endpoint.

### Implementation

1. Register commands: `/start`, `/casebook`, `/language`, `/help`, `/reset`, `/support`, `/terms`.
2. Implement onboarding as deterministic callbacks, not freeform conversation:
   - language buttons
   - case cover and briefing
   - `Begin Investigation`
   - no case picker
3. Add contextual inline actions under final replies:
   - investigation: `Casebook`, `Witnesses`, `Move`, `Verdict`
   - witness: `Present Evidence`, `Change Witness`, `End Interview`
4. Always call `answerCallbackQuery` immediately, before engine/network work.
5. Movement uses callback buttons from canonical location list. Call engine change-location endpoint, then send localized location name/description and image only on first visit.
6. Witness selector shows canonical available witnesses. Selection updates durable mode, closes Mini App if initiated there, sends witness header/portrait only on first contact, then accepts text questions.
7. `Present Evidence` opens Mini App evidence route filtered for current witness. Selected evidence creates durable present-evidence job; resulting witness reply returns to Telegram chat.
8. Rites require no bot-specific parser. Forward player text unchanged to investigation endpoint; existing engine performs spell detection.
9. Reply behavior:
   - send `typing` action while job runs
   - send one final reply; no `sendMessageDraft`, topics, or edit-loop streaming
   - escape Telegram formatting before send
   - split at paragraph boundaries below 4096 characters; preserve order and put buttons only on final chunk
   - send separate localized evidence discovery notice using response `new_evidence` and `evidence_names`
10. Daily cap:
    - count investigate, interrogate, present-evidence, briefing LLM question if later enabled, and verdict evaluation
    - reserve before dispatch; commit on engine success; release on known pre-mutation failure
    - at 40, show localized reset timestamp in UTC
11. `/reset` uses confirm/cancel buttons. Confirm resets FastAPI autosave plus Telegram mode/media receipts/usage tied to case; it does not delete user identity or entitlements.
12. `/language` changes bot language and FastAPI state language. Existing generated history stays unchanged.
13. Reuse assets during Docker build:
    - location IDs: `library`, `iron_lodge_common_room`, `third_floor_corridor`, `kitchens`
    - witness IDs: `elena`, `cassian`, `whitmore`, `wisp`
    - prefer AVIF only if Telegram upload accepts it reliably; otherwise use existing WebP/PNG variants
    - cache returned Telegram `file_id` after first upload to avoid repeated binary uploads

### Failure behavior

- 401: refresh engine token once.
- 409 `request_in_progress`: keep job pending briefly, then fetch snapshot; never create new request ID.
- Save conflict/unknown dispatch: explain progress may already exist, refresh snapshot, ask player to resend only if needed.
- LLM/provider failure before mutation: restore turn, show localized retry button.
- Telegram delivery failure after engine success: retain stored response and retry delivery.
- Concurrent player message: queue it and send one localized `Queued` acknowledgement, not one per retry.

### Tests

- Fresh EN and RU onboarding.
- `/start` resumes rather than resets.
- Mode routes identical text to correct endpoint.
- End/change witness changes durable mode correctly.
- Rites pass through unchanged.
- Navigation and media-once behavior.
- Evidence discovery notice and evidence presentation.
- Reset confirmation/cancel.
- 39th, 40th, and 41st LLM-turn behavior at UTC boundary.
- Long reply splitting, escaping, button placement.
- Every callback is acknowledged even when downstream call fails.

### Exit gate and handoff

- Case 1 can be played from briefing through correct/incorrect verdict using mocked Mini App selectors.
- Container restart preserves player identity, mode, queue, and image receipts.
- Existing case content and hidden mechanics remain unchanged.

## Phase 4 — Mini App and English/Russian Presentation

### Goal

Add focused Telegram-native panels without moving natural-language play out of chat.

### Mini App authentication

1. Client reads raw `window.Telegram.WebApp.initData` and posts it to `POST /miniapp/session`.
2. Server validates Telegram HMAC and rejects missing, malformed, or stale `auth_date`. Never trust `initDataUnsafe` for identity.
3. Server issues short-lived `Secure`, `HttpOnly`, same-origin session cookie. Regenerate session from fresh `initData` after expiry.
4. Require expected `Origin`/`Host`, CSRF protection for state-changing endpoints, and private-chat user identity.
5. Mini App never receives bot token, internal player token, LLM key, hidden case data, or solution data.

### Hono Mini App API

- `POST /miniapp/session`
- `GET /miniapp/casebook`
- `GET /miniapp/evidence`
- `GET /miniapp/witnesses`
- `POST /miniapp/witnesses/:id/select`
- `POST /miniapp/witnesses/:id/evidence/:evidenceId`
- `GET /miniapp/verdict/options`
- `POST /miniapp/verdict`

All responses use canonical IDs and localized display fields. Validate request and response with strict Zod schemas.

### UI implementation

1. Mobile-first routes:
   - `/casebook`: briefing dossier, current location, visited locations, rite reference, remaining daily turns
   - `/evidence`: discovered evidence cards and detail view only
   - `/witnesses`: witness cards; select witness and close Mini App after successful mode change
   - `/verdict`: suspect selection, discovered evidence multi-select, reasoning textarea, confirmation, result state
2. Use Telegram theme CSS variables. Respect viewport, safe area, content safe area, BackButton, MainButton/BottomButton semantics, and reduced motion.
3. Handle direct deep links/start parameters so chat buttons open correct route.
4. Loading, empty, expired-session, offline, validation, engine-conflict, and cap states require explicit UI.
5. Verdict submission disables duplicate taps and uses one stable request ID until terminal response.
6. After present-evidence or witness selection, close Mini App only after server confirms queued action. Bot sends result in chat.
7. Do not reuse existing desktop modals/layout. Reuse domain/API patterns and visual assets only.

### Localization

1. Shared UI catalog: `en` and `ru`; English key set is source of truth.
2. Case overlay keyed by canonical IDs and fields for:
   - case title/description/briefing
   - location names/descriptions/surface elements shown to player
   - witness names/bios
   - evidence names/descriptions/types/location labels
   - rite names/help
   - fixed verdict/confrontation copy rendered outside LLM response
3. Never translate evidence IDs, witness IDs, location IDs, spell tags, trust tags, JSON keys, callback payloads, or request IDs.
4. Add completeness test: Russian catalog must contain every English player-facing key and no unknown IDs.
5. Add release gate for human Russian review of clue meaning, suspect names, evidence terminology, and verdict wording.

### Tests

- Valid, invalid, tampered, and stale `initData`.
- Session cookie expiry/renewal and CSRF/origin rejection.
- All four routes at narrow/mobile widths.
- Telegram light/dark theme variables and safe-area padding.
- BackButton/MainButton registration cleanup.
- Empty evidence, no witness selected, cap reached, offline, conflict, and expired-session states.
- Verdict form validation and duplicate-submit prevention.
- EN/RU catalog parity and canonical-ID preservation.
- API schemas reject extra/missing fields.

### Validation commands

```bash
cd telegram
~/.bun/bin/bun run test
~/.bun/bin/bun run type-check
~/.bun/bin/bun run lint
~/.bun/bin/bun run build
```

### Exit gate and handoff

- Mini App works in Telegram iOS, Android, and Desktop test clients.
- Chat buttons deep-link to correct route.
- No hidden case data appears in browser network responses.
- Russian static content passes completeness and human meaning review.

## Phase 5 — Hardening, Deployment, and Public Beta

### Goal

Ship observable, reversible beta on existing Docker server without disrupting web game.

### Deployment changes

1. Add `Dockerfile.telegram` multi-stage build:
   - install/build with Bun
   - copy Hono server, Vite build, migration files, and selected existing location/witness assets
   - run as non-root where practical
   - writable `/app/data` only
2. Add `telegram` service to `docker-compose.yml`:
   - `restart: unless-stopped`
   - durable `lantern-telegram` volume
   - depends on healthy backend
   - joins `lantern-network` and external `proxy`
   - `VIRTUAL_HOST=bot.thelantern.institute`
   - `VIRTUAL_PORT=<gateway port>`
   - `LETSENCRYPT_HOST=bot.thelantern.institute`
3. Update `.env.production.example`, deploy file list, health reporting, and rollback notes. Never commit live tokens.
4. Update `deploy.sh` to deploy/build Telegram service, but do not set webhook automatically with token in shell history. Provide owner-run BotFather/webhook steps.
5. Owner-run prerequisites:
   - create/configure bot in BotFather
   - set name, description, commands, profile art
   - enable Main Mini App and menu button URL
   - apply backend and gateway SQL migrations
   - supply production secrets
   - set HTTPS webhook with secret token and allowed updates
6. Do not push Git changes without explicit owner approval.

### Observability and controls

- Structured events: onboarding started/completed, first clue, first interview, first verdict, solve, daily cap, engine error, Telegram delivery error, queue age.
- Metrics: job queue depth/oldest age, engine latency/error rate, Telegram delivery retries, active users, daily LLM turns, funnel conversion.
- Feature flags:
  - disable new sessions
  - disable LLM turns while preserving casebook/evidence access
  - disable Mini App mutations
- `/support` gives owner contact path. `/terms` explains beta, AI-generated content, usage cap, data handling. Add `/paysupport` only with Stars.
- Define retention before launch: processed updates/jobs/idempotency records 7 days; aggregated funnel metrics may persist; no player prose in gateway analytics.

### Staging and acceptance run

Use separate staging bot and database.

1. Fresh English player: start -> briefing -> investigate -> clue -> move -> witness -> present evidence -> wrong verdict -> correct verdict.
2. Fresh Russian player repeats same critical path; verify clue meaning and canonical IDs.
3. Restart gateway with pending, running-before-dispatch, engine-complete, and failed-delivery jobs.
4. Replay same Telegram update and same engine request ID; verify one mutation and one LLM charge.
5. Hit 40-turn cap; verify read-only Mini App and navigation remain available.
6. Tamper webhook secret and Mini App `initData`; verify rejection and no state change.
7. Verify existing `thelantern.institute` web journey remains unchanged.
8. Verify container health, logs, volume persistence, TLS, webhook status, and rollback.

### Final validation

```bash
cd backend
uv run pytest
uv run ruff check .
uv run mypy src/

cd ../frontend
~/.bun/bin/bun run test --run
~/.bun/bin/bun run type-check
~/.bun/bin/bun run lint
~/.bun/bin/bun run build

cd ../telegram
~/.bun/bin/bun run test
~/.bun/bin/bun run type-check
~/.bun/bin/bun run lint
~/.bun/bin/bun run build
```

### Public-beta exit gate

- All new tests pass; pre-existing failures are documented separately.
- Staging acceptance run passes on Telegram iOS, Android, and Desktop.
- Owner has executed SQL and configured BotFather/webhook/secrets.
- Kill switches and rollback tested.
- Funnel events visible without raw player prose.
- Public beta starts capped; Case 2 and Stars work remain blocked until progression data supports investment.

## 4. Explicit Non-Goals

- Rewriting FastAPI engine in Hono.
- Replacing or redesigning existing web frontend.
- Group/multiplayer investigations.
- Cross-platform save linking.
- Telegram live draft streaming or threaded topics.
- HTML5 Games/high scores.
- Voice/photo investigation input.
- Push reminders or broadcast campaigns.
- Full case marketplace, subscriptions, Stars checkout, refunds, or paid support flow.
- Admin dashboard, Redis, distributed workers, or Kubernetes.
- New Case 1 content, shorter pacing, changed evidence, or changed solution.

## 5. Coding-Agent Handoff Rules

- Work phase by phase. Do not start next phase before current exit gate passes.
- TDD: add failing focused test, implement minimum change, then run phase validation.
- Preserve unrelated dirty-worktree changes. Current modified files belong to owner.
- Never execute SQL. Add migration files and provide exact owner instructions.
- Never use `npm`, `npx`, Yarn, or pnpm. Use Bun commands only for TypeScript work and UV for Python.
- Never push without asking owner.
- Keep generated assets, coverage, databases, logs, tokens, and build output out of commits.
- Update `backend/CLAUDE.md`, add `telegram/CLAUDE.md`, and update root deployment documentation when architecture lands.
- At each phase handoff report: files changed, migration required, commands run, exact pass/fail counts, remaining risks, next phase gate.

## 6. Unresolved Questions

None.
