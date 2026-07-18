# Telegram Public Beta — Implementation Plan (Lantern)

**Status:** Superseded as the primary playbook  
**Date:** 2026-07-17 (Lantern ship)  
**Production host:** `bot.thelantern.institute`

## Use this instead

**Universal guidelines (new games + agents):**

→ [`docs/guides/telegram-narrative-game-client.md`](../guides/telegram-narrative-game-client.md)

That guide generalizes architecture, phases, exit gates, and **pitfalls learned shipping this project** (idempotency, media-on-begin, locale detection, DNS/webhook, disk, Mini App auth, etc.).

## Lantern worked-example notes

Phase handoffs and env fragments for this repo only:

| Doc | Content |
|-----|---------|
| [phase1-api-contract](./2026-07-17-telegram-phase1-api-contract.md) | Engine `request_id` + snapshot samples |
| [phase3-chat-loop](./2026-07-17-telegram-phase3-chat-loop.md) | Chat routing summary |
| [phase4-miniapp](./2026-07-17-telegram-phase4-miniapp.md) | Mini App routes |
| [phase5-deploy](./2026-07-17-telegram-phase5-deploy.md) | Lantern deploy, BotFather, setWebhook |
| [env fragment](../env.telegram.fragment.example) | Env keys for production |

**Package:** `telegram/`  
**Stack:** Bun + Hono + grammY + Vite Mini App → FastAPI engine  

## Original product contract (Lantern-specific, historical)

- Second client only; web game unchanged.  
- Solo private DMs; free `case_001`; EN/RU; 40 LLM turns/UTC day.  
- Investigation freeform + witness mode; Mini App casebook/evidence/witnesses/verdict.  
- Out of scope v1: Matthew, music, multi-slot saves, Stars checkout, groups.  

For new games, copy structure from the **universal guide**, not these Lantern IDs.
