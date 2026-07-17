# Phase 4 — Mini App + EN/RU presentation (delivered)

## API

| Method | Path | Notes |
|--------|------|-------|
| POST | `/miniapp/session` | initData HMAC → HttpOnly cookie + CSRF |
| GET | `/miniapp/casebook` | snapshot + rites + turns |
| GET | `/miniapp/evidence` | discovered only |
| GET | `/miniapp/witnesses` | select closes app |
| POST | `/miniapp/witnesses/:id/select` | mode change + chat job |
| POST | `/miniapp/witnesses/:id/evidence/:id` | queue present-evidence |
| GET | `/miniapp/verdict/options` | suspects + evidence |
| POST | `/miniapp/verdict` | stable request_id |

SPA: `/app/` (Vite build → `dist/app`).

## Auth

- Never trust `initDataUnsafe`
- Stale `auth_date` > 24h rejected
- Mutations: Origin/Host must match `TELEGRAM_PUBLIC_URL` + `x-csrf-token`

## Chat deep links

Investigation buttons open `web_app` URLs: `{TELEGRAM_PUBLIC_URL}/app/#/casebook|witnesses|verdict`.

## Catalogs

- `src/i18n/case_catalog.ts` — evidence/witness/rite EN+RU (IDs untranslated)
- `src/i18n/miniapp_ui.ts` — chrome strings

## Owner

Human RU review of clue wording before public beta (release gate).
