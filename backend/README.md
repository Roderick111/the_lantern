# HP Game Backend

FastAPI backend with multi-LLM narrator for Victorian occult detective investigation game.

**Current Version**: 0.7.0 (Multi-LLM Provider Support)
- Supports OpenRouter, Anthropic, OpenAI, Google providers via LiteLLM
- Automatic fallback when primary model fails
- Configure provider/model via environment variables

**Key Features**:
- Freeform DnD-style investigation (narrator responds to any action)
- Witness interrogation (trust mechanics, secret revelation)
- Matthew Croft spirit companion LLM conversation (50% helpful / 50% misleading)
- Verdict evaluation (reasoning analysis, fallacy detection)
- Conversation history persistence (investigation log saved/loaded)
- Intro briefing system (Graves teaching + interactive Q&A)
- Magic system (7 rites, single-stage detection, programmatic Mnemonic Delving)

## Setup

### Prerequisites
- Python 3.11+
- `uv` package manager
- LLM API key (OpenRouter recommended, or Anthropic/OpenAI/Google)

### Installation

```bash
# Create venv and install deps
uv venv
uv sync

# Configure environment
cp .env.example .env
# Edit .env and configure your LLM provider:
#   DEFAULT_LLM_PROVIDER=openrouter (or anthropic/openai/google)
#   OPENROUTER_API_KEY=sk-or-v1-your-key
#   DEFAULT_MODEL=openrouter/anthropic/claude-sonnet-4
```

### Development

```bash
# Run server
uv run uvicorn src.main:app --reload --port 8000

# OpenAPI docs
open http://localhost:8000/docs
```

### Testing

```bash
# Run all tests
uv run pytest tests/ -v

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Lint
uv run ruff check .

# Auto-fix lint issues
uv run ruff check --fix .

# Type check
uv run mypy src/
```

## API Endpoints (Phase 1)

### POST /api/investigate
Freeform investigation input → narrator response with evidence discovery

**Request**:
```bash
curl -X POST http://localhost:8000/api/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "player_input": "I check under the desk for clues",
    "case_id": "case_001",
    "player_id": "default"
  }'
```

**Response**:
```json
{
  "narrator_response": "You kneel down and peer beneath the ancient oak desk...",
  "new_evidence": ["desk_scratches"],
  "case_id": "case_001",
  "player_id": "default"
}
```

### POST /api/save
Save player state to JSON file

**Request**:
```bash
curl -X POST http://localhost:8000/api/save \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "case_001",
    "player_id": "default",
    "discovered_evidence": ["desk_scratches"],
    "conversation_history": [...]
  }'
```

### GET /api/load/{case_id}
Load player state from JSON

**Request**:
```bash
curl "http://localhost:8000/api/load/case_001?player_id=default"
```

**Response**:
```json
{
  "case_id": "case_001",
  "player_id": "default",
  "discovered_evidence": ["desk_scratches"],
  "conversation_history": [...],
  "last_updated": "2026-01-05T15:30:00Z"
}
```

### GET /api/evidence
List all discovered evidence for a case

### GET /api/cases
List available cases

### GET /health
Health check endpoint

## Architecture

```
src/
├── case_store/       # YAML case files
├── context/          # LLM context builders (narrator, witness, mentor, spell_llm)
├── api/              # FastAPI routes + LLM client
├── config/           # LLM provider settings
├── spells/           # Spell definitions
└── state/            # Player state + persistence
```

See `PLANNING.md` (root) for full architecture.

## LLM Provider Configuration

The backend uses LiteLLM to support multiple LLM providers. Configure via `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `DEFAULT_LLM_PROVIDER` | Provider: anthropic, openrouter, openai, google | `openrouter` |
| `OPENROUTER_API_KEY` | OpenRouter API key | `sk-or-v1-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `DEFAULT_MODEL` | Model identifier (use aliases) | `openrouter/anthropic/claude-sonnet-4` |
| `ENABLE_FALLBACK` | Try fallback model on failure | `true` |
| `FALLBACK_MODEL` | Fallback model | `openrouter/google/gemini-2.0-flash-001` |

**Recommended Setup** (OpenRouter - one API for 400+ models):
```bash
DEFAULT_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key
DEFAULT_MODEL=openrouter/anthropic/claude-sonnet-4
ENABLE_FALLBACK=true
FALLBACK_MODEL=openrouter/google/gemini-2.0-flash-001
```

**Alternative: Direct Anthropic**:
```bash
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key
DEFAULT_MODEL=anthropic/claude-sonnet-4
```

**Troubleshooting**:
- Missing API key error: Set the API key for your chosen `DEFAULT_LLM_PROVIDER`
- Fallback triggered: Check logs for primary model failure reason
- Cost tracking: LiteLLM logs token usage and cost per request

## Recent Changes

### v0.7.0: Multi-LLM Provider Support (2026-01-23)

**New Files**:
- `src/config/llm_settings.py` - Provider configuration with Pydantic
- `src/api/llm_client.py` - Unified LLM client via LiteLLM

**Features**:
- Switch providers via `.env` (OpenRouter, Anthropic, OpenAI, Google)
- Automatic fallback when primary model fails
- Cost logging per request
- Backward-compatible `get_client()` interface

**Migration**: Replace `claude_client` imports with `llm_client`:
```python
# Old
from src.api.claude_client import get_client
# New
from src.api.llm_client import get_client
```

### v0.6.10: Spell Description Polish (2026-01-11)

**Immersive Spell Descriptions**:
- Rewrote all 7 spell descriptions with mysterious, atmospheric language
- Removed formal "RESTRICTED" warning from Mnemonic Delving
- Changed from technical descriptions to evocative narrative style
- Descriptions now read like passages from forbidden knowledge texts

**Example (Mnemonic Delving)**:
- Before: "RESTRICTED: Mind reading spell - HIGH RISK..."
- After: "Slip past the barriers of the mind... but the mind fights back..."

**Files Modified**:
- `src/spells/definitions.py` - All spell descriptions rewritten for immersion

### Phase 4.6.2: Spell Detection System (2026-01-11)

**Single-Stage Detection** (spell_llm.py):
- `SPELL_SEMANTIC_PHRASES`: Defines action phrases for all 7 rites
- `detect_spell_with_fuzzy()`: Fuzzy matching + semantic phrase detection
- `extract_target_from_input()`: Parses spell targets ("on elena")
- `extract_intent_from_input()`: Parses focused intent ("to find out about X")
- `detect_focused_mnemonic_delving()`: Determines focused vs unfocused search
- `build_mnemonic_delving_narration_prompt()`: 4 outcome templates

**Endpoints Updated**:
- `/api/investigate`: Uses new detection for all 7 rites
- `/api/interrogate`: Mnemonic Delving with programmatic outcomes

**Dependency**: rapidfuzz ^3.0.0 (fuzzy string matching)
