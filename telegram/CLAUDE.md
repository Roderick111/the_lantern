# Telegram Gateway — Architecture

Bun + Hono + grammY. Durable SQLite jobs. FastAPI engine is source of truth.

## Run

```bash
cd telegram
~/.bun/bin/bun install
# Local long polling (never with production webhook set):
cp .env.example .env   # fill secrets
~/.bun/bin/bun run dev:poll

# Tests
~/.bun/bin/bun run test
~/.bun/bin/bun run type-check
~/.bun/bin/bun run lint
```

## Layout

```
src/server/   # Hono app, config, health, entry
src/bot/      # webhook, handlers, format, keyboards
src/db/       # bun:sqlite + repositories
src/jobs/     # durable worker + operation handlers
src/engine/   # FastAPI client + Zod schemas
src/domain/   # types, case_001 meta, callbacks
src/i18n/     # EN/RU strings
migrations/   # owner-run SQL
app/          # Mini App (Phase 4)
```

## Phase 3 play loop

- Modes: `investigation` → investigate; `witness` → interrogate
- Onboarding: language → cover → Begin Investigation
- Buttons: Casebook, Witnesses, Move, Verdict; witness Present/Change/End
- Daily cap: 40 LLM turns UTC; navigate/casebook free after cap
- Assets: `ASSETS_PATH` → `frontend/public` locations + portraits (once per player)

## Phase 4 Mini App

- SPA: `app/` → build `dist/app`, served at `/app/`
- API: `/miniapp/*` (session cookie + CSRF; initData HMAC)
- Catalogs: `src/i18n/case_catalog.ts`, `miniapp_ui.ts`
- Chat `web_app` buttons deep-link when `TELEGRAM_PUBLIC_URL` set

## Phase 5 deploy

- Image: `Dockerfile.telegram` (multi-stage, non-root, assets + dist)
- Compose service: `telegram` → `bot.thelantern.institute`
- Volume: `lantern-telegram` → `/app/data`
- Flags: `FEATURE_NEW_SESSIONS`, `FEATURE_LLM_TURNS`, `FEATURE_MINIAPP_MUTATIONS`
- Owner steps: `docs/plans/2026-07-17-telegram-phase5-deploy.md`
- Deploy: `./deploy.sh` (no auto setWebhook)

## Job states

`pending → running → engine_complete → delivered`

- Delivery failures → `failed_delivery` (retry send, no engine re-run)
- `running` + not dispatched on restart → `pending`
- `running` + dispatched on restart → `needs_manual_retry` (never auto re-run)

## Security

- Webhook: verify `X-Telegram-Bot-Api-Secret-Token` before JSON body use for state
- Engine: `X-Player-Token` only; never bot token / initData to engine
- Logs: no player prose, tokens, keys, raw initData

## Env

See `.env.example`. Owner SQL: `migrations/2026-07-17-telegram-gateway.sql`.
