# Telegram Phase 1 — Engine API Contract

Optional `request_id` on mutations. Missing value = legacy behavior (no idempotency).

## `request_id` rules

| Rule | Value |
|------|--------|
| Optional | yes |
| Max length | 128 |
| Charset | printable ASCII `[\x21-\x7E]` (no spaces) |
| Key | `(player_id, operation, request_id)` |

### Duplicate handling

| Stored status | Response |
|---------------|----------|
| `completed` | Original HTTP status + body (no LLM / no re-mutation) |
| `in_progress` | `409` with `{"code":"request_in_progress",...}` |
| `failed_before_mutation` | Retry allowed (re-claim) |

## Sample: investigate with request_id

```http
POST /api/investigate
X-Player-Token: <token>
Content-Type: application/json

{
  "player_input": "examine the desk",
  "case_id": "case_001",
  "location_id": "library",
  "slot": "autosave",
  "request_id": "tg-job-abc-001"
}
```

```json
{
  "narrator_response": "Dust lies thick on the ledger...",
  "new_evidence": ["library_ledger"],
  "evidence_names": {"library_ledger": "Library Ledger"},
  "already_discovered": false,
  "location_changed": null,
  "updated_state": {
    "case_id": "case_001",
    "current_location": "library",
    "discovered_evidence": ["library_ledger"],
    "visited_locations": ["library"],
    "save_revision": 2
  }
}
```

Second identical request returns the same JSON; LLM is not called again.

## Sample: 409 in progress

```json
{
  "detail": {
    "code": "request_in_progress",
    "message": "Identical request already in progress"
  }
}
```

## Covered mutation operations

| Endpoint | Operation key |
|----------|---------------|
| `POST /api/investigate` | `investigate` |
| `POST /api/interrogate` | `interrogate` |
| `POST /api/present-evidence` | `present_evidence` |
| `POST /api/submit-verdict` | `submit_verdict` |
| `POST /api/case/{case_id}/change-location` | `change_location` |
| `POST /api/briefing/{case_id}/complete` | `briefing_complete` |
| `POST /api/settings/update` | `settings_update` |

Streaming SSE routes are **not** idempotent keys for Telegram. Gateway must use non-streaming endpoints.

## Briefing complete (body optional)

Legacy (query only):

```http
POST /api/briefing/case_001/complete?slot=autosave
X-Player-Token: <token>
```

With body:

```http
POST /api/briefing/case_001/complete
X-Player-Token: <token>
Content-Type: application/json

{
  "slot": "autosave",
  "request_id": "tg-brief-1"
}
```

## Session (reuse)

```http
POST /api/session
Content-Type: application/json

{}
```

```json
{
  "player_id": "a1b2c3...",
  "token": "<signed-token>"
}
```

Gateway stores `token`; Mini App / browser never sees internal token.

## Telegram snapshot

```http
GET /api/telegram/snapshot/case_001?slot=autosave
X-Player-Token: <token>
```

```json
{
  "case_id": "case_001",
  "current_location": "library",
  "visited_locations": ["library"],
  "discovered_evidence": ["library_ledger"],
  "briefing_completed": true,
  "language": "en",
  "save_revision": 3,
  "available_witnesses": [
    {"id": "elena", "name": "Elena Voss"},
    {"id": "cassian", "name": "Cassian Drake"}
  ],
  "verdict_attempts_remaining": 10,
  "case_solved": false
}
```

Never includes solution, hidden evidence, secrets, prompts, or API keys.

## Migration (owner-run)

```bash
sqlite3 /path/to/lantern.db < backend/migrations/2026-07-17-idempotency-records.sql
```

Coding agents do not execute this SQL.
