# Frontend — Architecture & Index

> Keep this file up to date when making significant structural changes.

## Stack

React 18 · TypeScript 5.6 · Vite 6 · Tailwind 3.4 · React Router 7 · Zod 4 · Framer Motion

**Run:** `cd frontend && ~/.bun/bin/bun run dev` (port 5174)
**Build:** `~/.bun/bin/bun run build` · **Test:** `~/.bun/bin/bun run test` · **Lint:** `~/.bun/bin/bun run lint`

---

## Directory Map

```
src/
├── main.tsx                     # Vite entry point
├── App.tsx                      # Router: / (landing) and /case/:caseId (game)
│
├── api/                         # API client layer — all backend calls + Zod validation
│   ├── base.ts                  # apiCall(), streamSSE(), API_BASE_URL, error types
│   ├── schemas.ts               # All Zod schemas (.strict()) matching backend Pydantic models
│   ├── client.ts                # Barrel re-export of all domain modules
│   ├── investigation.ts         # investigate(), investigateStream(), getLocations(), resetCase()
│   ├── witnesses.ts             # interrogateWitness(), interrogateStream(), presentEvidenceStream()
│   ├── briefing.ts              # getBriefing(), askBriefingQuestion(), markBriefingComplete()
│   ├── verdict.ts               # submitVerdict()
│   ├── matthew.ts               # checkMatthewAutoComment(), sendMatthewChat()
│   ├── saves.ts                 # saveGameState(), loadGameState(), listSaveSlots(), deleteSaveSlot()
│   ├── settings.ts              # setNarratorVerbosity(), getSettings()
│   └── telemetry.ts             # logSessionStart() — anonymous usage tracking
│
├── types/                       # TypeScript interfaces mirroring backend models
│   ├── investigation.ts         # Core types: InvestigateRequest/Response, WitnessInfo, VerdictRequest, etc.
│   ├── game.ts                  # Static case data types (legacy)
│   ├── enhanced.ts              # Deprecated stubs
│   └── spells.ts                # Spell type definitions
│
├── hooks/                       # Custom hooks — all state management lives here
│   ├── useInvestigation.ts      # Location loading, evidence tracking, state persistence
│   ├── useWitnessInterrogation.ts # useReducer — witness list, conversation, trust, secrets
│   ├── useVerdictFlow.ts        # useReducer — submission, feedback, confrontation, attempts
│   ├── useBriefing.ts           # Briefing content, Q&A conversation, choice selection
│   ├── useLocation.ts           # Available locations, current location, visited set
│   ├── useMatthewChat.ts        # Matthew auto-comments (30% chance) + direct chat
│   ├── useSaveSlots.ts          # Slot operations: save, load, list, delete, import
│   ├── useGameModals.ts         # Centralized modal open/close state (prevents prop drilling)
│   ├── useGameActions.ts        # All event handlers extracted from InvestigationView
│   ├── useMainMenu.ts           # Main menu state
│   └── useInnerVoice.ts         # Matthew companion triggers (advanced, not actively used)
│
├── components/
│   ├── layout/
│   │   └── InvestigationLayout.tsx  # 2-pane grid: 70% main + 30% sidebar (responsive)
│   │
│   ├── ui/                      # Reusable primitives
│   │   ├── Button.tsx           # Variants: primary, secondary, ghost, terminal
│   │   ├── Modal.tsx            # ESC-close, backdrop click, variant support
│   │   ├── Card.tsx             # Container card
│   │   ├── TerminalPanel.tsx    # ASCII-styled collapsible panel
│   │   ├── Toast.tsx            # Auto-dismiss notifications (success/error/info)
│   │   ├── SidebarPanel.tsx     # Quick stats + modal trigger buttons
│   │   ├── EvidenceCard.tsx     # Evidence display card
│   │   └── ContradictionPanel.tsx # Evidence contradiction highlights
│   │
│   ├── LandingPage.tsx          # Main menu: start new case / load game
│   ├── LocationView.tsx         # Core gameplay: player input → narrator streaming → evidence discovery
│   ├── WitnessInterview.tsx     # Dual-pane: conversation + profile/trust/secrets
│   ├── VerdictSubmission.tsx    # Form: suspect + reasoning + evidence selection
│   ├── MentorFeedback.tsx       # Post-verdict: score, fallacies, critique, praise
│   ├── ConfrontationDialogue.tsx # Final confrontation scene with culprit
│   ├── BriefingModal.tsx        # 3-step initiate: dossier → teaching questions → engagement
│   ├── BriefingDossier.tsx      # Case details + persons of interest
│   ├── BriefingQuestion.tsx     # A/B/C choice + Graves feedback
│   ├── BriefingEngagement.tsx   # Q&A recap + start investigation
│   ├── BriefingConversation.tsx # Briefing chat history
│   ├── EvidenceModal.tsx        # Evidence detail view
│   ├── EvidenceListModal.tsx    # All discovered evidence list
│   ├── WitnessesModal.tsx       # Witness quick-access list
│   ├── MainMenu.tsx             # In-game menu: restart, save, load, settings
│   ├── SettingsModal.tsx        # Narrator verbosity, hints toggle
│   ├── SaveLoadModal.tsx        # Multi-slot save/load UI
│   ├── LanternCompendium.tsx        # In-game help/tips
│   ├── MusicPlayer.tsx          # Background music controls
│   ├── LocationHeaderBar.tsx    # Sticky location tabs for navigation
│   ├── LocationSelector.tsx     # Location change UI
│   ├── ConfirmDialog.tsx        # Reusable confirmation modal
│   └── ErrorBoundary.tsx        # Global error boundary with reload fallback
│
├── context/                     # React context for global state
│   ├── ThemeContext.tsx          # Dark/light mode — persists to localStorage
│   ├── MusicContext.tsx          # Volume, mute, tracks — persists to localStorage
│   ├── useTheme.ts              # Theme context consumer hook
│   └── useMusic.ts              # Music context consumer hook
│
├── styles/
│   └── terminal-theme.ts        # Design tokens: colors, fonts, character colors, ASCII helpers
│
├── utils/
│   ├── playerId.ts              # UUID generation + localStorage persistence
│   ├── renderInlineMarkdown.tsx # Markdown → JSX (bold, italic, links)
│   └── evidenceRelevance.ts     # Evidence-to-suspect relevance calc (unused)
│
└── test/
    ├── setup.ts                 # Vitest + jsdom config
    ├── render.tsx               # Custom render with all providers
    └── providers.tsx            # Provider wrapper for tests
```

---

## Key Conventions

**API layer** — Every backend call goes through `api/`. All responses validated with Zod `.strict()` schemas matching backend Pydantic models. If backend adds a field, the Zod schema must be updated or it will throw at runtime.

**Streaming** — LLM-powered endpoints use SSE via `streamSSE()` in `api/base.ts`. Components accumulate chunks and handle partial `[EVIDENCE: id]` tags during stream.

**State management** — No Redux. Complex flows use `useReducer` (witnesses, verdict). Simple state uses `useState` in custom hooks. Global state (theme, music) uses React Context.

**Modal management** — All modal state centralized in `useGameModals`. Action handlers centralized in `useGameActions`. Prevents InvestigationView from becoming a god component.

**Theming** — Two modes: dark (CRT terminal) and light (LCARS sci-fi). All colors/fonts come from `styles/terminal-theme.ts`. Components use `useTheme()` to get current tokens. Never hardcode colors.

**Player identity** — Anonymous UUID stored in localStorage (`lantern_game_player_id`). Passed with every API call as `player_id`.

**Save system** — 4 slots: `autosave` (continuous) + 3 manual (`slot_1`, `slot_2`, `slot_3`). Manual save snapshots autosave state. All operations via `useSaveSlots` hook.

**Component patterns:**
- `ui/` — Reusable, theme-aware primitives. No domain logic.
- Root `components/` — Feature components. Can use hooks and API calls.
- `layout/` — Structural wrappers (grid, sticky positioning).

**Testing** — Vitest + Testing Library. Custom `render()` from `test/render.tsx` wraps all providers. Tests colocated in `__tests__/` directories.

---

## Data Flow

```
Player input → api/investigation.ts (SSE stream)
            → LocationView accumulates chunks
            → Extract [EVIDENCE: id] tags
            → useInvestigation.handleEvidenceDiscovered()
            → Check Matthew auto-comment (30% chance)
            → Render conversation timeline
```

```
Verdict: VerdictSubmission → api/verdict.ts
       → MentorFeedback (score + fallacies)
       → Correct? → ConfrontationDialogue
       → Wrong?   → Retry (if attempts remain)
```

---

## localStorage Keys

| Key | Purpose |
|-----|---------|
| `lantern-theme` | Dark/light mode |
| `hp-detective-music-*` | Volume, mute, enabled, track per case |
| `lantern_game_player_id` | Anonymous player UUID |
| `lantern_llm_settings` | BYOK provider config |
| `telemetry_consent_shown` | Telemetry banner dismissed |
| `lantern_game_location_{caseId}` | Current location per case (reload persistence) |

---

## Env Variables

```
VITE_API_URL=    # Backend URL (defaults to http://localhost:8000)
```
