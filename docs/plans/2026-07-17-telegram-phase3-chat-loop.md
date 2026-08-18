# Phase 3 — Chat-First Game Loop (delivered)

## Scope

Telegram gateway plays Case 1 via chat: onboarding, investigate/interrogate, move, witnesses, present-evidence (button mock), verdict (button mock + freeform reasoning), daily cap, reset, EN/RU.

Mini App UI = Phase 4. Phase 3 uses callback selectors as mock Mini App.

## Routing

| Mode | Text destination |
|------|------------------|
| `investigation` | `POST /api/investigate` |
| `witness` + witnessId | `POST /api/interrogate` |
| pending verdict reasoning | `POST /api/submit-verdict` |

Commands: `/start` `/casebook` `/language` `/help` `/reset` `/support` `/terms`.

## Onboarding

1. Language buttons (`lang:en` / `lang:ru`) → engine `settings/update` + `need_begin`
2. Cover copy + `Begin Investigation` → `briefing/.../complete` + `active`
3. `/start` when active → resume snapshot, no reset

## Daily cap

40 LLM turns/UTC day: investigate, interrogate, present_evidence, submit_verdict. Check before dispatch; increment on success.

## Owner SQL (existing telegram.db only)

```bash
sqlite3 /app/data/telegram.db < telegram/migrations/2026-07-17-telegram-phase3-session.sql
```

Fresh installs get columns from embedded `SCHEMA_SQL`.

## Env

- `ASSETS_PATH` — path to `frontend/public` (locations + portraits webp). Default `../frontend/public`.

## Exit gate

- Mocked engine tests: onboarding EN/RU, resume, mode routing, rites passthrough, move, evidence notice, reset, cap, verdict
- `bun test` / type-check / lint / build green
