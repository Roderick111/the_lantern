# Phase 5 — Hardening, Deployment, Public Beta

## Architecture (prod)

```
Telegram → https://bot.thelantern.institute
           ├── POST /telegram/webhook
           ├── GET  /health
           ├── /miniapp/*  (session cookie API)
           └── /app/       (Mini App SPA)

lantern-telegram  ──HTTP──►  lantern-backend:8000
                  volume: lantern-telegram → /app/data

thelantern.institute  unchanged (frontend + backend)
```

## Env (server `.env.production`)

Add alongside existing backend keys. **Never commit live values.**

```bash
# Telegram gateway
TELEGRAM_BOT_TOKEN=          # from BotFather
TELEGRAM_WEBHOOK_SECRET=     # random ≥16 chars; must match setWebhook secret_token
MINIAPP_SESSION_SECRET=      # random ≥16 chars
TELEGRAM_PUBLIC_URL=https://bot.thelantern.institute
LANTERN_ENGINE_URL=http://backend:8000
TELEGRAM_MODE=webhook
PORT=8080
TELEGRAM_DB_PATH=/app/data/telegram.db
ASSETS_PATH=/app/assets

# Kill switches
FEATURE_NEW_SESSIONS=true
FEATURE_LLM_TURNS=true
FEATURE_MINIAPP_MUTATIONS=true

RETENTION_DAYS=7
ENGINE_TIMEOUT_MS=60000
```

Also keep: `LETSENCRYPT_EMAIL`, LLM keys, backend settings.

Template fragment: `docs/env.telegram.fragment.example`

## Owner SQL (do not auto-run)

```bash
# Backend engine DB (if Phase 1 not applied)
sqlite3 /app/saves/lantern.db < backend/migrations/2026-07-17-idempotency-records.sql

# Telegram gateway (fresh volume auto-creates schema; migrate if upgrading Phase 2→3)
sqlite3 /app/data/telegram.db < telegram/migrations/2026-07-17-telegram-gateway.sql
sqlite3 /app/data/telegram.db < telegram/migrations/2026-07-17-telegram-phase3-session.sql
```

Inside container examples:

```bash
docker compose exec backend sh -c 'sqlite3 /app/saves/lantern.db' < backend/migrations/...
docker compose exec telegram sh -c 'sqlite3 /app/data/telegram.db' # or copy SQL in
```

## BotFather checklist

1. Create bot → copy token into `TELEGRAM_BOT_TOKEN`.
2. Description / about: “The Lantern public beta — occult investigation, EN/RU”.
3. Commands:
   ```
   start - Begin or resume
   casebook - Dossier summary
   language - English / Русский
   help - Commands
   reset - Reset case progress
   support - Support contact
   terms - Beta terms
   ```
4. Menu Button / Main Mini App URL: `https://bot.thelantern.institute/app/`
5. Domain: set for Mini App if BotFather requires allowlist.

## setWebhook (owner-run only)

Do **not** put the bot token in `deploy.sh` or shell history. Prefer env file on a trusted machine:

```bash
# On owner laptop (example — fill from password manager)
export BOT_TOKEN='…'
export SECRET='…same as TELEGRAM_WEBHOOK_SECRET…'
curl -sS "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=https://bot.thelantern.institute/telegram/webhook" \
  -d "secret_token=${SECRET}" \
  -d 'allowed_updates=["message","callback_query","my_chat_member"]' \
  -d "drop_pending_updates=false"

curl -sS "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
unset BOT_TOKEN SECRET
```

Never long-poll production while webhook is set.

## Deploy

```bash
./deploy.sh
# or: ./deploy.sh 188.34.196.228
```

Verify:

```bash
curl -sS https://bot.thelantern.institute/health
docker compose ps
docker compose logs -f telegram
```

Web must still work: `https://thelantern.institute`

## Kill switches

Edit server `.env.production`, then:

```bash
docker compose up -d telegram --force-recreate
```

| Flag | Effect |
|------|--------|
| `FEATURE_NEW_SESSIONS=false` | Block fresh engine sessions at onboarding |
| `FEATURE_LLM_TURNS=false` | Block investigate/interrogate/present/verdict LLM |
| `FEATURE_MINIAPP_MUTATIONS=false` | Mini App read-only (no select/present/verdict POST) |

## Rollback (Telegram only)

```bash
cd /opt/the-lantern
docker compose stop telegram
docker compose rm -f telegram
# Optional: comment telegram service out of compose, then up -d
# Volume lantern-telegram keeps player state for re-attach
```

Web stack untouched.

## Observability

`GET /health` returns:

- `status`, `db`, `engine`
- `flags` kill switches
- `worker.pending_jobs`, `running_jobs`, `failed_delivery`, `needs_manual_retry`, `oldest_pending_age_sec`
- `funnel.*` aggregate counters (no prose, hashed user short form in logs)

Structured log `msg=funnel` events: onboarding_started/completed, first_clue, first_interview, first_verdict, case_solved, daily_cap, engine_error, delivery_error.

Retention: terminal jobs + orphan updates purged opportunistically after `RETENTION_DAYS` (default 7).

## Staging acceptance (owner)

Separate staging bot + empty DB when possible.

1. EN: start → language → begin → investigate → clue → move → witness → present → wrong verdict → correct.
2. RU: same path; check clue wording and IDs unchanged.
3. Restart with pending / running-undispatched / engine_complete / failed_delivery.
4. Replay same update_id + request_id → one mutation.
5. Cap at 40 LLM turns → casebook/nav still work.
6. Bad webhook secret + bad initData → reject, no state change.
7. Web game at thelantern.institute unchanged.
8. TLS, volume, health, rollback.

## Human RU review (release gate)

Review case_catalog clue names, suspect names, verdict UI chrome before public share.

## Non-goals still blocked

Case 2, Stars, admin dashboard, Redis, multiplayer.
