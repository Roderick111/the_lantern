# Telegram Client for Narrative / Investigation Games — Universal Guidelines

**Status:** Living guide (derived from shipping a full public-beta Telegram client beside an existing web game engine)
**Audience:** Product owners + coding agents adding a **second client** (Telegram) without rewriting the game engine
**Assumes:** Solo narrative or mystery game, freeform player text, server-side LLM, existing HTTP game API, optional web frontend

Use this document as the playbook. Replace bracketed placeholders with your game. Do not treat any single repo path as required.

---

## 1. When this pattern fits

**Good fit**

- Authoritative game state already lives on a backend (not only in the browser).
- Play is mostly freeform text (investigate, talk, cast abilities) plus a few structured panels (dossier, inventory, verdict).
- You want Telegram as **another client**, not a fork of game logic.
- Private solo DMs are enough for v1 (no multiplayer, no groups).

**Bad fit / defer**

- Game requires continuous low-latency canvas, voice, or multiplayer sessions.
- State is only localStorage with no server API.
- You need full desktop UI fidelity inside chat.

**Core product decision (do not reverse mid-build)**

> The **game engine API remains source of truth**.
> The **Telegram gateway owns Telegram identity, delivery, chat mode, presentation, caps, and entitlements**.

Never reimplement progression, evidence discovery, or verdict logic inside the bot.

---

## 2. Product contract template

Write this first. Freeze before coding.

| Topic | Recommended default | Notes |
|--------|---------------------|--------|
| Audience | Private DMs only | Ignore groups/channels for v1 |
| Entry | One free case/start scenario | No case marketplace in v1 |
| Input | Freeform text for play | Unsupported media → one short instruction |
| Structured UI | Mini App for dossier / inventory / select / submit | Chat stays primary for natural language |
| Saves | Autosave only | Drop multi-slot UX unless engine already needs it |
| Languages | Explicit allowlist (e.g. EN + one more) | Static copy checked in; LLM follows saved language |
| Media | Location/character images once per player first show | Reuse existing assets; cache Telegram `file_id` |
| LLM cost | Server-funded + daily turn cap | Navigation/read-only remain after cap |
| Payments | Entitlement table only until Stars | Digital goods on Telegram must use Stars later |
| Out of scope | Music, companions, trust meters, live drafts, HTML5 Games API, push campaigns | Cut hard |

**Funnel to instrument (no player prose in logs)**

`start → first meaningful progress → first structured interaction → first resolution attempt → win/lose`

---

## 3. Target architecture

```text
Telegram client
  ├── messages / callbacks  →  Gateway (webhook)
  │                              ├── durable job queue (SQLite or equivalent)
  │                              ├── Telegram session (mode, language, usage)
  │                              └── Engine HTTP client (player token)
  │
  └── Mini App WebView      →  Gateway Mini App API
                                 ├── validate initData → session cookie
                                 ├── serve SPA
                                 └── same Engine HTTP client

Gateway  ──►  Game engine API  ──►  LLM provider
                  │
                  └── game autosave DB (authoritative)
```

| Layer | Owns | Must not own |
|--------|------|----------------|
| Engine | Progress, discovery, dialogue, verdicts, language in save | Bot tokens, chat delivery, Mini App cookies |
| Gateway | Telegram user ↔ internal player, jobs, chat mode, i18n chrome, caps, media receipts | Hidden case solutions, LLM keys in Mini App |
| Mini App | Read models + a few mutations with stable request IDs | Bot token, raw player tokens, secrets |

### 3.1 Game adapter contract

Every new game needs an explicit adapter between its engine and this gateway. Do not make bot handlers learn game-specific endpoint shapes one by one.

The adapter must expose these capabilities, even when a game implements some as unsupported:

| Capability | Required contract | Gateway use |
|------------|-------------------|-------------|
| Identity | Create/resume player and return server-side token | `/start`, resume, reset |
| Snapshot | Current scene/location, progress, language, revision, available actions | Chat replies, Mini App reads |
| Freeform action | Accept text plus `request_id` and return sanitized result | Investigation mode |
| Conversation | Accept NPC/companion ID, text, and `request_id` | Interview mode |
| Navigation | Accept canonical destination ID plus `request_id` | Move buttons |
| Evidence/content | Return discovered-only records keyed by stable IDs | Dossier/inventory |
| Resolution | Accept accusation/verdict plus `request_id` | Ending flow |
| Localization | Load locale overlay without changing mechanics | Language selection |

Publish a capability matrix before implementation:

```text
has_npcs: true/false
has_companions: true/false
has_abilities: true/false
has_verdict: true/false
has_media: true/false
supported_locales: [en, ...]
```

The adapter owns translation from gateway operations to engine endpoints, response normalization, error mapping, and schema validation. The gateway never branches on hidden case logic.

Use a small versioned error envelope across engines. At minimum distinguish `auth`, `validation`, `conflict`, `not_found`, `unsupported`, `rate_limited`, `transient`, and `unknown`. Each error needs a safe player-facing message, a retry policy, and an operator-facing correlation ID; never expose raw engine or provider errors to Telegram.

**Stack that worked well**

- Runtime: **Bun + Hono + grammY**
- Mini App: **Vite + React** (mobile-first, Telegram theme CSS variables)
- Gateway DB: **SQLite** (one volume, simple ops)
- Engine: whatever you already have (FastAPI, etc.) — keep it

Avoid for v1: Redis/BullMQ, ORM, conversation plugins, reusing desktop layout, proxying Mini App to engine with player tokens in the browser.

---

## 4. Work in phases (exit gates)

Ship phase-by-phase. Do not start the next phase until the exit gate passes.

| Phase | Goal | Exit gate |
|-------|------|-----------|
| **0 — Contract** | Product table + out-of-scope list | Written and approved |
| **1 — Engine** | Idempotent mutations + compact snapshot API | Tests green; web client unchanged without `request_id` |
| **2 — Gateway shell** | Webhook, queue, engine client, health, secrets | Synthetic update → job → mock engine → mock delivery; restart rules proven |
| **3 — Chat loop** | Onboarding, modes, investigate/talk/move, caps, reset | Full happy path with mocks; restart preserves identity/queue |
| **4 — Mini App** | Auth + 3–4 mobile routes + EN/locale catalogs | initData tests; no secrets in network responses |
| **5 — Ship** | Docker, DNS/TLS, flags, retention, owner runbooks | Staging acceptance; kill switches; disk/DNS/webhook checklist |

Coding agents: hand off SQL/migrations and production secrets to the human. **Never set webhook with bot token in deploy scripts.**

---

## 5. Phase 1 — Engine prerequisites

### 5.1 Idempotency

Telegram will retry. Workers will crash mid-request. Without idempotency you double-spend LLM and corrupt state.

- Add optional `request_id` (opaque ASCII, max ~128) on **every mutation** the gateway will call.
- Missing `request_id` = old web behavior (backward compatible).
- Key: `(player_id, operation, request_id)`.
- States: `in_progress` → `409`; `completed` → return stored body; `failed_before_mutation` → retry allowed.
- TTL ~7 days; opportunistic bounded cleanup (no mandatory scheduler).

**Gateway rule after dispatch**

- Transport **timeout after** calling engine → treat as **unknown**. Do **not** auto-retry with a new ID. Reload snapshot; ask player to resend only if needed.
- Restart: job `running` + not dispatched → re-queue; dispatched → manual/unknown path.

### 5.2 Snapshot endpoint

One compact read for Telegram (and Mini App casebook):

- Current location, visited locations, discovered evidence IDs
- Briefing/tutorial done, language, save revision
- Available NPCs/witnesses (id + display name)
- Attempts remaining / solved flags

**Never** return: solution, hidden evidence, internal prompts, API keys, trust internals unless product explicitly shows them.

Snapshot responses should include a monotonic `revision` (or equivalent save version). The gateway sends that revision back on mutations when the engine supports optimistic concurrency. A stale revision must produce a typed conflict, not a second mutation.

### 5.3 Auth for gateway

- Gateway creates engine sessions with existing session endpoint.
- Stores `player_id` + player token server-side only.
- Engine calls use `X-Player-Token` (or your equivalent). Browser never sees that token for Telegram users.

Encrypt player tokens at rest or store an encrypted refreshable credential instead. Define rotation, revocation, backup handling, and what happens when the engine rejects a token permanently. Telegram user IDs must use a 64-bit-safe representation; do not assume a 32-bit integer.

### 5.4 Idempotency hardening

The idempotency key is not enough by itself. Store a canonical payload hash with each `(player_id, operation, request_id)` record.

- Same key + same payload → return the stored result.
- Same key + different payload → return a deterministic conflict; never execute either request again.
- Mutation and creation of the `in_progress` record must be transactionally ordered by the engine.
- A timeout after dispatch creates an `unknown` outcome. The gateway reloads snapshot and does not retry with a new key.
- Apply the same rules to callback mutations, verdicts, reset confirmation, NPC selection, and Mini App submits.
- Retain completed records for the replay window and clean them with bounded, observable retention work.

---

## 6. Phase 2 — Gateway shell

### 6.1 Tables (minimum)

| Table | Purpose |
|-------|---------|
| `users` | telegram_user_id, chat_id, player_id, player_token, language |
| `sessions` | case_id, mode (`investigation` \| `npc`/`witness`), selected npc id, onboarding_step, pending_json |
| `usage` | UTC date + LLM turn count |
| `updates` | Telegram `update_id` dedupe |
| `jobs` | durable work: request_id, operation, payload, state, engine_response, delivery fields, engine_dispatched |
| `entitlements` | free/owned/locked per case |
| `media_receipts` | first-seen location/npc media + Telegram file_id cache |

### 6.2 Job states

```text
pending → running → engine_complete → delivered
                 ↘ failed_delivery (retry send only)
                 ↘ needs_manual_retry (ambiguous engine)
```

Rules:

- One active mutation **per Telegram user** (FIFO).
- Store engine response **before** Telegram send.
- Delivery failure: retry send, never re-run LLM.
- Dedupe Telegram `update_id` with 2xx.

### 6.3 Webhook

- Production: HTTPS webhook + `secret_token` header check **before** trusting body for side effects.
- Local: long polling; never both at once.
- Ack quickly; process async.
- Allowed updates v1: `message`, `callback_query`, `my_chat_member` (add payments only when you ship payments).

### 6.4 Logging

Structured logs with update_id, request_id, operation, duration, status.

**Never log:** player prose, bot token, player token, LLM keys, raw Mini App `initData`.

### 6.5 Health

`/health`: gateway DB ok, engine reachability, queue depth, oldest pending age, feature flags. No PII.

### 6.6 Telegram transport limits and retry policy

Treat Telegram as an at-least-once, rate-limited transport.

- Keep `callback_data` short and versioned: current Bot API allows 1–64 bytes. Store large state server-side and send an opaque ID.
- Split messages at the current 4096-character text limit and 1024-character caption limit, counting entity markup rather than only JavaScript string length.
- Respect `429` responses and Telegram's `retry_after`; retry only safe delivery operations.
- Enforce per-chat and global send budgets. A single player must not receive a burst of queued replies after a restart.
- Bound callback answer text and answer every callback promptly, even when the actual operation is queued.
- Treat expired, duplicated, or unknown callback payloads as harmless user-facing notices.
- Log Telegram method, status, retry delay, and request ID without logging message text or tokens.

Do not hard-code undocumented flood limits as product guarantees. Keep limits configurable and verify them against the current [Bot API](https://core.telegram.org/bots/api) and [Bot FAQ](https://core.telegram.org/bots/faq).

### 6.7 Identity and chat lifecycle

Define these transitions before launch:

- user blocks the bot, then unblocks it;
- user deletes Telegram account or asks to delete game data;
- user opens the bot from multiple devices;
- chat ID changes or a group update reaches a private-DM-only bot;
- player token is revoked by the engine;
- user starts a second game/case while the first has queued jobs.

Keep Telegram identity, engine player identity, and case/save identity separate. `/reset` clears case progress only; `/delete_my_data` removes gateway identity, tokens, jobs, media receipts, and engine data according to the documented retention policy.

---

## 7. Phase 3 — Chat game loop

### 7.1 Modes

```ts
type ChatMode =
  | { kind: "investigation" }           // freeform → investigate / act endpoint
  | { kind: "npc"; npcId: string };     // freeform → interrogate / talk endpoint
```

- Explicit enter NPC mode; explicit end interview.
- Same text must hit **different endpoints** by mode — test this.

### 7.2 Onboarding (deterministic, not freeform)

1. Language buttons (if multi-locale)
2. Cover / briefing (static or engine)
3. “Begin” → mark briefing complete in engine
4. `/start` on existing user **resumes**, never silent reset

### 7.3 Commands (minimal)

`/start`, dossier summary, `/language`, `/help`, `/reset` (confirm), `/support`, `/terms`

### 7.4 Inline actions

Under final replies:

- Investigation: dossier, NPCs, move, resolve/verdict
- NPC: present item/evidence, change NPC, end interview

Always `answerCallbackQuery` **immediately**, before engine work.

### 7.5 Movement & media (common bugs)

| Bug | Prevention |
|-----|------------|
| Starting location image never sent | On “Begin”, send current location image if no media receipt — do not rely only on “move” |
| Image only when engine “first visit” | Gate on **gateway media_receipt**, not only engine visited list (start location is often already visited) |
| RU UI shows EN location blurbs | **Never** show engine case YAML descriptions as player copy for non-EN; keep localized blurbs in gateway catalog |
| Re-upload every time | Cache Telegram `file_id` after first successful upload |

Prefer WebP/PNG unless you have proven AVIF reliability on Telegram clients.

### 7.6 Rites / natural-language abilities

- Pass player text **unchanged** to engine detection.
- Catalog must list **real** ability IDs from the engine — no invented “helper” rites.
- If you support non-English play: **detection dictionaries must include that language**. English-only phrase lists will silently fail for RU/ES/etc.
- Show example cast lines that match detection phrases.

### 7.7 Replies

- `typing` while job runs
- One final reply (no edit-loop streaming for v1)
- Escape HTML/Markdown for Telegram
- Split under 4096 at paragraph boundaries; buttons only on last chunk
- Separate short notice for newly discovered evidence IDs/names

### 7.8 Daily LLM cap

- Count only LLM-bearing ops (investigate, talk, present, verdict evaluation, …).
- Check before dispatch; increment on success.
- At cap: localized message with UTC reset; navigation/dossier still work.

### 7.9 Failure behavior (player-facing)

| Situation | Behavior |
|-----------|----------|
| 401 engine | Refresh player token once |
| 409 in progress | Wait briefly, same request_id, snapshot; never new ID |
| Timeout after dispatch | Unknown progress; no auto re-run |
| Delivery fail after engine success | Keep stored response; retry delivery |
| Concurrent messages | Queue; **one** “Queued” ack, not spam |

---

## 8. Phase 4 — Mini App

### 8.1 Auth (non-negotiable)

1. Client sends raw `Telegram.WebApp.initData` to gateway.
2. Server validates HMAC per Telegram docs; reject missing/malformed/stale `auth_date`.
3. **Never** trust `initDataUnsafe` for identity.
4. Issue short-lived **HttpOnly, Secure, SameSite** session cookie + CSRF for mutations.
5. Check Origin/Host against public bot URL.
6. Mini App must never receive bot token, engine player token, LLM keys, or solution data.

### 8.2 Typical routes

| Route | Role |
|-------|------|
| Casebook / dossier | Location, progress, turns left, ability reference |
| Inventory / evidence | Discovered only |
| NPCs | Select → close Mini App → chat continues |
| Resolution / verdict | Form + stable `request_id` until terminal |

Use Telegram theme CSS variables, safe-area padding, BackButton cleanup. Do not port desktop modals.

### 8.3 Localization catalogs

- UI chrome: EN + each locale, EN keys source of truth, parity test.
- Content overlay: names/descriptions keyed by **canonical IDs**.
- Never translate IDs, tags, JSON keys, callback payloads, request IDs.
- Human review gate for non-EN clue wording before public launch.

### 8.4 Deep links

Chat buttons should open Mini App with correct path (`web_app` URL with hash/query). Menu button → dossier. Prefer **subdomain** for the bot gateway (e.g. `bot.yourgame.com`) so the marketing/web game host stays clean.

### 8.5 Mini App launch contexts and stale actions

Test each supported launch source separately: menu button, inline keyboard, keyboard button, direct link with `startapp`, and attachment menu. Their init data and available Telegram methods differ.

- Treat `startapp` as untrusted routing input; validate allowed destinations and never encode secrets in it.
- Send raw `Telegram.WebApp.initData` to the gateway. Never derive identity from browser storage or `initDataUnsafe`.
- Close the Mini App only after the gateway confirms the mutation or queues it with a stable request ID.
- If a user taps a keyboard from an older revision, show a stale-action notice and refresh snapshot.
- Handle two open Mini Apps, expired cookies, network loss, Telegram BackButton, and app reload without duplicating mutations.
- Set CSP, HSTS, frame/origin policy, and an explicit public-host allowlist.

---

## 9. Phase 5 — Deploy & operate

### 9.1 Containers

- Separate gateway image/service; depends on healthy engine.
- Writable volume only for gateway DB.
- Non-root where practical.
- Copy **selected** assets only (locations/portraits you need), not entire web `public/`.

### 9.2 Reverse proxy / TLS

- `VIRTUAL_HOST` / ACME companion (or equivalent) on the **gateway** service.
- DNS **A/AAAA** for bot host before webhook.
- Health URL must answer publicly on HTTPS before `setWebhook`.

### 9.3 Secrets

| Secret | Role |
|--------|------|
| `TELEGRAM_BOT_TOKEN` | BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Must match `setWebhook` secret_token |
| `MINIAPP_SESSION_SECRET` | Cookie signing |
| Engine URL | Internal network (`http://backend:8000`) |

Generate webhook/session secrets with `openssl rand -hex 32`. Never commit live values.
`setWebhook` 404 almost always means **invalid bot token** (including placeholder strings left in the command).

### 9.4 Kill switches

| Flag | Effect |
|------|--------|
| New sessions off | Block fresh engine identity |
| LLM turns off | Block costly mutations; keep read-only |
| Mini App mutations off | Casebook/inventory still readable |

### 9.5 Disk / ops pitfalls

| Pitfall | Prevention |
|---------|------------|
| `no space left on device` on Docker build | Prune unused images/cache regularly; avoid eternal `--no-cache` without cleanup |
| `docker compose` “no configuration file” | Always `cd` to compose project dir (or use container name with `docker exec`) |
| `sqlite3` missing in slim images | Apply SQL via language runtime already in image (Python/Bun) |
| Compose fails locally for missing `.env.production` | Production commands run **on server** with real env file |
| Placeholder setWebhook | Use real token/secret; verify with `getMe` first |

### 9.6 Owner checklist (human)

1. DNS for bot host → server IP
2. Secrets in production env; recreate gateway container
3. Engine migration for idempotency (once)
4. Gateway schema (boot or migrate)
5. `curl https://bot…/health`
6. `setWebhook` + `getWebhookInfo` (token not in deploy history)
7. BotFather commands + menu Mini App URL
8. Smoke: `/start` → language → begin → act → Mini App

### 9.7 Backups, migrations, and rollback

- Pin gateway and engine versions as a compatible release pair.
- Apply schema migrations before code that requires them; keep migrations forward-compatible during rolling deploys.
- Back up the gateway database and test restore into an isolated environment.
- Define rollback behavior for code, schema, content catalogs, and webhook configuration.
- Monitor disk usage, SQLite lock time, queue age, failed deliveries, token refresh failures, and LLM spend.
- Document the scale ceiling for one SQLite writer. Move to a managed database/queue when that ceiling is reached; do not silently add replicas against one local database file.

### 9.8 LLM reliability and abuse controls

- Set request, provider, and queue timeouts separately.
- Bound input characters, context size, output tokens, and total spend per user/case/day.
- Treat player text, evidence descriptions, uploaded media, and engine responses as untrusted prompt content.
- Keep system instructions and hidden solutions outside player-visible responses.
- Validate structured LLM output against a schema before applying game state.
- Provide deterministic fallback prose for provider outage, malformed output, and safety refusal.
- Add per-user, per-IP, and global concurrency limits; daily caps alone do not stop burst abuse.
- Record model, latency, token counts, failure class, and cost without storing player prose.

### 9.9 Staging acceptance

- Fresh EN and second locale happy path
- Restart with pending / mid-dispatch / engine_complete / failed_delivery
- Replay same update_id and same request_id → one mutation
- Cap behavior
- Bad webhook secret / bad initData → no state change
- Existing web game still works

---

## 10. Testing strategy

| Layer | What to test |
|-------|----------------|
| Engine | Idempotency, snapshot redaction, no web regression without request_id |
| Gateway unit | Secret verify, update dedupe, serial per user, delivery retry without second engine call, cap, mode routing, 429 backoff, stale callbacks |
| Adapter contract | Every capability maps to a typed engine request/response; unsupported capabilities fail cleanly |
| Locale | Catalog parity; ability detection phrases for each language; stable IDs; human-review snapshots |
| Mini App | initData valid/invalid/stale/tampered; every launch source; CSRF/origin; empty/cap/offline/session expired; stale revision |
| LLM | Timeout, malformed output, provider failure, prompt-injection fixture, token/cost budget |
| Data lifecycle | Token rotation, delete/export, backup restore, migration forward/rollback |
| Ops | Health flags; retention purge; funnel counters without prose; queue-age and spend alerts |

Prefer **mock engine + mock Telegram** for gateway CI. Real bot only for human staging.

---

## 11. Pitfalls checklist (experience-backed)

Copy into every new game kickoff.

### Architecture

- [ ] Engine is authoritative; gateway is presentation + delivery
- [ ] No game logic duplicated in bot handlers
- [ ] Web API stays backward compatible without `request_id`

### Durability

- [ ] Idempotency on all LLM/state mutations
- [ ] Payload hash rejects same request_id with different payload
- [ ] Never auto-retry ambiguous post-dispatch timeouts
- [ ] Jobs store engine result before Telegram send
- [ ] Restart rules implemented and tested
- [ ] Stale revision and callback behavior is defined

### Product / UX

- [ ] `/start` resumes, does not wipe identity
- [ ] Reset is confirm + clears progress, not entitlements/identity
- [ ] Unsupported media handled once, clearly
- [ ] Cap does not brick navigation
- [ ] Queued, offline, expired-session, and blocked-bot states are localized
- [ ] `/delete_my_data` behavior is documented and tested

### Localization

- [ ] Static chrome + content catalogs with parity tests
- [ ] Ability/spell detection includes each supported language
- [ ] Location/NPC blurbs not taken from EN-only case files for other locales
- [ ] Human review of non-EN clue names before launch

### Media

- [ ] Starting location image on first enter (Begin), not only on move
- [ ] Media receipt + file_id cache
- [ ] Asset paths exist in container (`ASSETS_PATH`)

### Mini App

- [ ] HMAC initData; no initDataUnsafe
- [ ] CSRF + origin on mutations
- [ ] Stable request_id for verdict/submit
- [ ] Close Mini App only after server confirms queue/select
- [ ] All supported launch contexts have auth and routing tests
- [ ] CSP/HSTS/host allowlist are configured

### Deploy

- [ ] Bot on dedicated host/subdomain
- [ ] DNS before webhook
- [ ] Webhook secret matches env
- [ ] Disk headroom; prune policy
- [ ] Backup restore tested
- [ ] Migration rollback documented
- [ ] Telegram 429/retry_after behavior tested
- [ ] Kill switches documented
- [ ] SQL applied once; re-run is IF NOT EXISTS safe

### Security / privacy

- [ ] No secrets in Mini App responses
- [ ] No player prose in analytics logs
- [ ] Player tokens encrypted/rotatable at rest
- [ ] Telegram IDs stored 64-bit safely
- [ ] Terms/support text exists for beta

---

## 12. Suggested repo layout (gateway package)

```text
telegram/                 # or bot/
  package.json            # Bun
  src/
    server/               # Hono entry, config, health, metrics
    bot/                  # webhook verify, routing, keyboards, format
    jobs/                 # worker + operation handlers
    engine/               # typed client + Zod schemas
    db/                   # SQLite schema, repos, retention
    domain/               # modes, case meta (IDs), callbacks
    i18n/                 # UI + content catalogs
    miniapp/              # auth + API routes
  app/                    # Vite Mini App
  migrations/             # owner-run SQL
  tests/
Dockerfile.telegram
```

Keep files under ~500 lines; split handlers by concern.

---

## 13. Mapping: your game terms

| This guide | Example mapping |
|------------|-----------------|
| Investigation mode | Freeform explore / act |
| NPC mode | Witness interview / dialogue |
| Evidence | Inventory / clues |
| Rites / abilities | Spells, skills, tools |
| Casebook | Dossier / journal |
| Verdict | Accusation / ending submit |
| Case ID | Scenario / chapter id |

---

## 14. What not to build in v1

- Multiplayer / groups / sharing
- Full case store + Stars checkout (unless product is ready)
- Live message drafts / streaming edits
- Port of entire web UI
- Admin dashboard, Redis workers, K8s
- Voice/photo as primary investigation input
- Cross-platform save linking

---

## 15. Handoff template (for agents)

At end of each phase report:

1. Files changed
2. Migrations required (owner-run)
3. Commands run + pass/fail counts
4. Remaining risks
5. Next phase exit gate

Also report the adapter capability matrix, data-retention assumptions, supported Telegram launch contexts, and known Bot API limits for that game.

**Never:** execute production SQL without owner; push without ask; put bot token in deploy scripts; log player prose.

---

## 16. Related Lantern-specific notes (optional)

Historical implementation for The Lantern lived under `docs/plans/2026-07-17-telegram-*.md` and the `telegram/` package. Prefer **this guide** for new games; use those docs only as a worked example of one codebase.
