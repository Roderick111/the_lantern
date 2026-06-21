# The Lantern: Critical Thinking Investigation Game

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> An AI-powered Victorian occult detective game teaching rationality and deductive reasoning through immersive investigations.

**Version:** 1.7.0 | **Type Safety:** Grade A | **Status:** Production Ready

---

## 🎯 Overview

**The Lantern** is an interactive investigation game where you play as a probationary Lantern Inspector, solving occult mysteries at Blackwood Collegiate. The game combines:

- 🔍 **AI-Powered Investigations** - Dynamic LLM narrator responds to freeform actions
- 🗣️ **Witness Interrogation** - Build trust, reveal secrets, detect lies
- 🔮 **Rite System** - Perform 7 investigation rites (Unveil, Mnemonic Delving, etc.)
- 🧠 **Critical Thinking** - Detect fallacies, avoid bias, submit verdicts
- 👻 **Spirit Companion (Matthew Croft)** - Unreliable ghost advisor; 50% helpful, 50% misleading

**Perfect for:** Educators teaching critical thinking, Victorian occult detective fans, detective game enthusiasts

---

## ✨ Core Features

### Investigation
- **Freeform Input**: Type any action—LLM narrator responds dynamically
- **Evidence Discovery**: Keyword triggers with 5+ variants per clue
- **Location Navigation**: Move between Library, Dormitory, Great Hall (clickable or natural language)
- **7 Investigation Rites**: Unveil, Sense Presence, Echo Reading, Identify Substance, Mnemonic Delving, Dispel, Ward Circle
- **Conversation History**: Full investigation transcript preserved across saves
- **Multi-LLM Provider Support**: Switch between OpenRouter, Anthropic, OpenAI, Google providers
- **Music Ambience**: Per-case background music with volume control, play/pause, mute (localStorage persistence)

### Witness System
- **Interrogation**: Question suspects, present evidence
- **Trust Mechanics**: 0-100% trust affects honesty (LA Noire-inspired)
- **Secret Revelation**: Evidence presentation unlocks hidden information
- **AI-Powered Dialogue**: Every witness responds with unique personality

### Verdict & Feedback
- **Detective Reasoning**: Submit suspect + explanation + evidence
- **Fallacy Detection**: Graves analyzes for 4 types of logical errors
- **Adaptive Hints**: Feedback scales with attempt count
- **Post-Verdict Confrontation**: Dialogue scene with culprit if correct

### Educational Components
- **Briefing System**: Graves teaches rationality concepts (base rates, evidence strength)
- **Matthew's Guidance**: Spirit companion provides 50% helpful, 50% misleading advice
- **Critical Thinking**: Learn to evaluate evidence objectively

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** with [uv](https://github.com/astral-sh/uv)
- **Bun** (not npm/yarn — use `~/.bun/bin/bun` if `bun` is not on your PATH)
- **LLM API Key** — OpenRouter recommended ([Get key](https://openrouter.ai/)), or Anthropic/OpenAI/Google

### First-time setup

```bash
git clone https://github.com/Roderick111/the-lantern.git
cd the-lantern

# Backend
cd backend
uv venv
uv sync
cp .env.example .env
# Edit .env — see backend/README.md
# Recommended: DEFAULT_LLM_PROVIDER=openrouter, OPENROUTER_API_KEY=sk-or-v1-...

# Frontend (from repo root)
cd ../frontend
bun install
```

### Run locally (two terminals)

Use **two terminal tabs**. Start the backend first, then the frontend.

**Terminal 1 — backend** → `http://localhost:8000`
```bash
cd backend
uv run uvicorn src.main:app --reload --port 8000
```

**Terminal 2 — frontend** → `http://localhost:5173`
```bash
cd frontend
~/.bun/bin/bun run dev
```

Open **http://localhost:5173** in your browser. In dev, the Vite proxy forwards `/api` to `http://127.0.0.1:8000`.

**Troubleshooting:** If you see the wrong app or stale content, another process may be bound to `:8000` or `:5173`. Stop it and restart both servers.

### Optional: music

Add MP3 files to `frontend/public/music/` — naming: `case_{id}_default.mp3` (e.g. `case_001_default.mp3`). Format: MP3, 128–192 kbps, 30–120s loop.

### Play

1. Open `http://localhost:5173`
2. Select a case from the landing page
3. Complete Graves's briefing
4. Start investigating

---

## 🎮 How to Play

### 1. Briefing Phase
- Graves explains the case (WHO/WHAT/WHERE/WHEN)
- Ask follow-up questions to clarify details
- Learn a rationality concept (e.g., base rates, evidence strength)

### 2. Investigation Phase
- **Navigate**: Click locations or type "go to dormitory"
- **Investigate**: Type freeform actions ("search the desk", "examine the focus")
- **Perform Rites**: "unveil hidden objects", "mnemonic delving on Elena"
- **Consult Matthew**: Prefix with `Matthew,` — e.g. "Matthew, should I trust this witness?" (carnival instincts, not Bureau training — he's sometimes wrong)
- **Evidence Board**: Automatically tracks discovered clues

### 3. Interrogation Phase
- **Question Witnesses**: Ask anything, AI responds in character
- **Build Trust**: Empathetic questions (+5%), aggressive (-10%)
- **Present Evidence**: Show contradictions to reveal secrets

### 4. Verdict Phase
- **Submit Accusation**: Choose suspect + reasoning + evidence
- **Graves's Analysis**: Fallacy detection and scoring (0-100)
- **Confrontation**: Dialogue scene with culprit if correct
- **10 Attempts**: Educational focus—learn from mistakes

### Controls
- **ESC**: Open main menu (New Game, Save, Load, Settings, Exit)
- **1-3**: Quick-select locations
- **Ctrl+Enter**: Submit investigation action
- **Cmd+H**: View Lantern Compendium (rite reference)
- **Settings → Audio**: Control music volume, play/pause, mute

---

## 🏗️ Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | Python + FastAPI | 3.13.3 |
| **Frontend** | React + TypeScript + Vite | 18.3 / 5.6 / 6.0 |
| **LLM** | Multi-provider via LiteLLM (OpenRouter/Anthropic/OpenAI/Google) | 1.57+ |
| **Validation** | Pydantic v2 (backend) + Zod (frontend) | 4.3.5 |
| **Styling** | Tailwind CSS | 3.4 |
| **Testing** | pytest / Vitest | - |
| **Package Mgmt** | uv / Bun | - |

---

## 📖 Documentation

### Getting Started
- [Game Design Document](docs/game-design/LANTERN_GAME_DESIGN.md) - Complete game design
- [Case Design Guide](docs/CASE_DESIGN_GUIDE.md) - Create your own cases
- [Developer Guide](CLAUDE.md) - Coding standards & agent orchestration

### Project Status
- [Current Status](STATUS.md) - Phase completion, metrics, recent activity
- [Planning & Roadmap](PLANNING.md) - What's next, priorities, backlog
- [Changelog](CHANGELOG.md) - Version history

### Technical Details
- [Type System Audit](docs/TYPE_SYSTEM_AUDIT.md) - TypeScript architecture
- [Validation Report](VALIDATION-GATES-ZOD-REPORT.md) - Zod implementation

---

## 🧪 Development

### Run Tests
```bash
# Backend (154 tests, 100% coverage)
cd backend && uv run pytest

# Frontend (377/565 tests)
cd frontend && bun test
```

### Type Checking
```bash
# Backend
cd backend && uv run mypy src/

# Frontend
cd frontend && bun run type-check
```

### Linting
```bash
# Backend
cd backend && uv run ruff check .

# Frontend
cd frontend && bun run lint
```

### Build
```bash
# Frontend (production build)
cd frontend && bun run build
```

---

## 🚢 Production Deployment

**Live site:** https://thelantern.institute

### Deploy

From the repo root (requires SSH access to the server):

```bash
./deploy.sh              # default: root@188.34.196.228
./deploy.sh <server-ip>  # override target
```

The script rsyncs backend/frontend + Docker configs to `/opt/the-lantern`, copies `backend/.env` → `.env.production` on the server, then runs `docker compose build --no-cache && docker compose up -d`.

**Stack:** `nginx-proxy` (TLS) → `lantern-frontend` (nginx, SPA + `/api` proxy) → `lantern-backend` (FastAPI). Game saves live in the `lantern-saves` Docker volume (`/app/saves/lantern.db`).

### Required production env vars

Copy `.env.production.example` → `backend/.env` and fill in API keys before deploying. Minimum:

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | Default LLM provider |
| `PLAYER_TOKEN_SECRET` | HMAC signing for `X-Player-Token` (32+ chars) |
| `CORS_ORIGINS` | e.g. `https://thelantern.institute` |
| `TRUSTED_PROXY` | **Set to `1` when behind nginx/Cloudflare** (see below) |

### `TRUSTED_PROXY=1` (rate limiting)

When the API sits behind a reverse proxy, FastAPI only sees the proxy’s IP—not the browser’s. Without `TRUSTED_PROXY`, unauthenticated rate limits (e.g. `POST /api/session`) can bucket all users together.

Set `TRUSTED_PROXY=1` in `backend/.env` (deployed as `.env.production`) when:

1. Traffic passes through nginx-proxy / Cloudflare / a load balancer, **and**
2. The backend is not exposed directly to the internet.

The backend then reads the client IP from `X-Forwarded-For` (set by `nginx.conf` on `/api/`). **Do not enable this** on a dev machine where clients can reach the API directly—otherwise anyone could spoof that header.

Authenticated requests are keyed by `player_id`; `TRUSTED_PROXY` mainly affects IP-based limits on session creation and similar endpoints.

### Post-deploy smoke test

```bash
curl -sS https://thelantern.institute/health
# → {"status":"ok","db":true}

curl -sS -X POST https://thelantern.institute/api/session \
  -H 'Content-Type: application/json' -d '{}'
# → {"player_id":"...","token":"v1...."}
```

**Server ops:**

```bash
ssh root@188.34.196.228 'cd /opt/the-lantern && docker compose ps'
ssh root@188.34.196.228 'cd /opt/the-lantern && docker compose logs -f backend'
```

---

## 📊 Project Metrics

**Current Version:** 1.7.0 (Multi-LLM Provider Support)

| Metric | Status |
|--------|--------|
| Type Safety | ✅ Grade A (compile-time + runtime) |
| Security | ✅ 0 vulnerabilities (audited 2026-01-18) |
| Backend Tests | ✅ 154/154 (100%) |
| Frontend Tests | ⚠️ 377/565 (66.7% - pre-existing) |
| Bundle Size | ✅ 104.83 KB gzipped |
| Cases Complete | ✅ 2 playable cases |
| Production Ready | ✅ Yes |

See [STATUS.md](STATUS.md) for detailed current state.

---

## 🗂️ Project Structure

```
lantern_game/
├── backend/                # Python FastAPI + Claude LLM
│   ├── src/
│   │   ├── case_store/     # YAML case files + loader
│   │   ├── context/        # LLM context builders (narrator, witness, mentor)
│   │   ├── api/            # FastAPI routes + Claude client
│   │   └── state/          # Player state + persistence
│   ├── tests/              # pytest tests (154, 100% coverage)
│   └── pyproject.toml
├── frontend/               # React + Vite + TypeScript
│   ├── src/
│   │   ├── components/     # UI components
│   │   │   └── layout/     # Layout orchestration (InvestigationLayout)
│   │   ├── hooks/          # React hooks
│   │   ├── api/            # Backend client + Zod schemas
│   │   └── types/          # TypeScript types
│   ├── tests/              # Vitest tests
│   └── package.json
├── docs/                   # Documentation
│   ├── game-design/        # Game design documents
│   ├── case-files/         # Case specifications
│   └── research/           # Research & analysis
├── PLANNING.md             # Roadmap & priorities
├── STATUS.md               # Current status & metrics
├── CLAUDE.md               # Developer guide
└── README.md               # This file
```

---

## 🤝 Contributing

This is an educational project. Contributions welcome!

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

**Coding Standards:** See [CLAUDE.md](CLAUDE.md)

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

- Built with [Anthropic Claude](https://www.anthropic.com/)
- Victorian occult detective universe 
- Inspired by *Return of the Obra Dinn*, *LA Noire*, and rationality education

---

**Questions?** See [STATUS.md](STATUS.md) or open an issue.
