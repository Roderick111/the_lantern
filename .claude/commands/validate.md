---
description: Quick validation — lint, types, tests, build
---

Run these checks and report results. Fix simple issues (imports, formatting) and re-run. Don't spawn agents.

## Backend
!`cd /Users/danielmedina/Documents/claude-projects/lantern_game/backend && uv run ruff check . 2>&1 | tail -5`
!`cd /Users/danielmedina/Documents/claude-projects/lantern_game/backend && uv run pytest --tb=no -q 2>&1 | tail -5`

## Frontend
!`cd /Users/danielmedina/Documents/claude-projects/lantern_game/frontend && ~/.bun/bin/bun run typecheck 2>&1 | tail -5`
!`cd /Users/danielmedina/Documents/claude-projects/lantern_game/frontend && ~/.bun/bin/bun run lint 2>&1 | tail -5`
!`cd /Users/danielmedina/Documents/claude-projects/lantern_game/frontend && ~/.bun/bin/bun run build 2>&1 | tail -5`

## Your task

Summarize results in a compact table:
| Check | Result |
Report any failures concisely. Fix trivial issues (imports, formatting) directly without asking.
