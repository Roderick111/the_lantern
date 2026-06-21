# Backend — Architecture & Index

> Keep this file up to date when making significant structural changes.

## Stack

Python 3.13 · FastAPI · LiteLLM · Pydantic v2 · SQLite · slowapi

**Run:** `cd backend && uv run uvicorn src.main:app --reload` (port 8001)
**Test:** `uv run pytest` · **Lint:** `uv run ruff check .` · **Types:** `uv run mypy src/`

---

## Directory Map

```
src/
├── main.py                  # FastAPI app, CORS, rate limiting, body size limit, health check
│
├── api/
│   ├── schemas.py           # All Pydantic request/response models (~15 models)
│   ├── llm_client.py        # LiteLLM wrapper: async completion, streaming (SSE), BYOK, fallback
│   ├── helpers.py            # Shared route utils: state loading, unified secret scorer, evidence extraction
│   ├── rate_limit.py         # slowapi config (10/min LLM, 100/min standard)
│   └── routes/
│       ├── __init__.py       # Mounts all sub-routers
│       ├── investigation.py  # POST /api/investigate — narrator + spell detection + evidence discovery
│       ├── witnesses.py      # POST /api/interrogate, /api/present-evidence — trust mechanics
│       ├── mnemonic_delving.py    # POST /api/cast-mnemonic_delving — programmatic success formula
│       ├── verdict.py        # POST /api/submit-verdict — scoring + fallacy detection + confrontation
│       ├── briefing.py       # GET /api/briefing, POST /api/briefing/{case_id}/question — Graves Q&A
│       ├── matthew.py        # POST /api/matthew/* — spirit companion auto-comments + chat
│       ├── saves.py          # Save/load/list/delete — multi-slot system
│       ├── cases.py          # Case discovery + location info
│       ├── evidence.py       # GET /api/evidence — list discovered evidence
│       ├── llm_config.py     # GET /api/llm-config — expose model info to frontend
│       └── telemetry.py      # POST /api/telemetry — client-side event logging
│
├── config/
│   └── llm_settings.py      # Pydantic settings from .env: provider, model, API keys, fallback
│
├── context/                  # LLM prompt builders (one per feature)
│   ├── narrator.py           # Investigation narration — victim humanization, evidence significance
│   ├── witness.py            # Witness interrogation — personality, trust-aware responses
│   ├── mentor.py             # Graves feedback — template + LLM-powered verdict response
│   ├── briefing.py           # Rationality teaching Q&A prompts
│   ├── matthew_llm.py        # Matthew Croft — 50/50 helpful/misleading, evidence-aware
│   ├── matthew_triggers.py   # Legacy YAML trigger selection (fallback for Matthew)
│   ├── spell_detection.py    # Multi-priority: exact → fuzzy → semantic spell matching
│   ├── spell_prompts.py      # Spell effect narration builders
│   ├── spell_llm.py          # LLM-based spell success calculation
│   └── rationality_context.py # Bayesian thinking, confirmation bias principles
│
├── case_store/
│   └── loader.py             # YAML case loading, path traversal protection, case discovery
│
├── location/
│   └── parser.py             # Natural language location parsing (SequenceMatcher, 75% threshold)
│
├── spells/
│   └── definitions.py        # 7 spell definitions (Unveil, Sense Presence, Mnemonic Delving, etc.)
│
├── state/
│   ├── player_state.py       # PlayerState dataclass — conversation, evidence, witnesses, trust
│   └── persistence.py        # SQLite storage — 4 slots (autosave + 3 manual), per-player UUID
│
├── utils/
│   ├── evidence.py           # Evidence extraction from LLM text, dedup, hallucination prevention
│   └── trust.py              # Witness trust mechanics — LLM trust delta, natural warming, evidence detection
│
├── verdict/
│   ├── evaluator.py          # Verdict checking — harsh 0-100 scoring
│   ├── fallacies.py          # Logical fallacy detection (5 types)
│   └── llm_evaluator.py      # LLM-based reasoning quality evaluation
│
└── telemetry/
    └── logger.py             # Fire-and-forget JSONL event logging
```

### Tests

```
tests/
├── conftest.py               # Shared fixtures: mock DB, disable rate limits, sample state
├── test_routes.py            # Main integration tests (~85KB, covers all endpoints)
├── test_narrator.py          # Narrator context builder
├── test_witness.py           # Witness interrogation + trust
├── test_evidence.py          # Evidence extraction + dedup
├── test_persistence.py       # Save/load SQLite
├── test_briefing.py          # Briefing Q&A
├── test_mentor.py            # Graves feedback
├── test_verdict_evaluator.py # Verdict scoring
├── test_fallacies.py         # Fallacy detection
├── test_spell_*.py           # Spell detection + LLM integration
├── test_matthew_*.py         # Matthew spirit companion
├── test_location.py          # Location parsing
├── test_case_*.py            # Case loading, discovery, context
└── test_trust.py             # Trust mechanics
```

---

## Key Conventions

**LLM calls** — Always go through `api/llm_client.py`. Never call LiteLLM directly from routes. Supports BYOK (user passes `api_key` + `model` in request body) and server-side keys from `.env`.

**Prompt building** — Each feature has its own context builder in `context/`. Routes call the builder, then pass the result to `llm_client`. Builders return message lists (`[{"role": "system", "content": ...}, ...]`).

**Evidence discovery** — YAML-driven. LLM narration includes `[EVIDENCE: evidence_id]` tags. `utils/evidence.py` extracts and deduplicates them against player state. Case YAML defines all valid evidence IDs + discovery guidance.

**State management** — `PlayerState` is loaded from SQLite (with bounded LRU cache) at request start, mutated in the route handler, then saved back. Always pass `player_id` + `slot` from frontend. `"default"` slot maps to `"autosave"`.

**Spell detection** — Three-tier priority: exact match → fuzzy match (rapidfuzz) → semantic phrases. Defined in `spells/definitions.py`, detected in `context/spell_detection.py`.

**Witness trust** — Two-axis system: Trust (rapport, 0-100) + Pressure (evidence weight, 0-500). LLM emits `[TRUST_DELTA: N]` tags (-15 to +15), natural warming (+0-5) as fallback. Secret revelation detected by unified fuzzy scorer in `helpers.py` (keyword token overlap + content sliding window + denial/evasion filters).

**Rate limiting** — slowapi on all LLM-hitting endpoints (10/min). Standard endpoints get 100/min. Configured in `api/rate_limit.py`.

**Error pattern** — Routes raise `HTTPException` for client errors. LLM failures use custom exceptions in `llm_client.py` (`LLMClientError`, `RateLimitExceededError`, `AuthenticationFailedError`).

---

## Env Config (.env)

```
LANTERN_DB_PATH=           # Optional SQLite path (default: saves/lantern.db or /app/saves/lantern.db in Docker)
DEFAULT_LLM_PROVIDER=      # anthropic | openrouter | openai | google
DEFAULT_MODEL=             # e.g. openrouter/x-ai/grok-4.1-fast
FALLBACK_MODEL=            # e.g. openrouter/google/gemma-4-26b-a4b-it
OPENROUTER_API_KEY=        # Server-side key (free tier)
ANTHROPIC_API_KEY=         # Optional
OPENAI_API_KEY=            # Optional
GOOGLE_API_KEY=            # Optional
CORS_ORIGINS=              # Comma-separated, defaults to localhost:5173,5174,3000
```
