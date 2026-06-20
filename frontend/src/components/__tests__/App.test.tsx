/**
 * App Integration Tests
 *
 * Tests for the main application integration including:
 * - Initial loading state
 * - Layout rendering
 * - State management
 * - Save/Load functionality
 *
 * @module components/__tests__/App.test
 * @since Phase 1
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../../App';
import { ThemeProvider } from '../../context/ThemeContext';
import { ErrorBoundary } from '../ErrorBoundary';
import * as api from '../../api/client';
import type { LocationResponse } from '../../types/investigation';

// Helper: render App at a specific URL with all providers
function renderAppAtUrl(url: string) {
  return render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[url]}>
        <App />
      </MemoryRouter>
    </ThemeProvider>,
  );
}

// ============================================
// Mocks
// ============================================

vi.mock('../../utils/playerId', () => ({
  getOrCreatePlayerId: () => 'test-player-id',
  usePlayerId: () => 'test-player-id',
}));

vi.mock('../../api/telemetry', () => ({
  logEvent: vi.fn(),
  logError: vi.fn(),
  logSessionStart: vi.fn(),
}));

// MusicContext requires audio APIs not present in jsdom — stub the provider/hook
vi.mock('../../context/MusicContext', async () => {
  const React = await import('react');
  return {
    MusicProvider: ({ children }: { children: React.ReactNode }) => children,
    MusicContext: React.createContext(null),
  };
});

vi.mock('../../hooks/useMusic', () => ({
  useMusic: () => ({
    enabled: false,
    volume: 0,
    muted: true,
    track: null,
    setEnabled: vi.fn(),
    setVolume: vi.fn(),
    setMuted: vi.fn(),
    setTrack: vi.fn(),
  }),
}));

// MusicPlayer touches HTMLAudioElement APIs — stub the whole component
vi.mock('../MusicPlayer', () => ({
  MusicPlayer: () => null,
}));

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return {
    ...actual,
    loadState: vi.fn(),
    saveGameState: vi.fn(),
    getLocation: vi.fn(),
    investigate: vi.fn(),
    investigateStream: vi.fn(),
    getWitnesses: vi.fn(),
    interrogateWitness: vi.fn(),
    presentEvidence: vi.fn(),
    getEvidenceDetails: vi.fn(),
    getLocations: vi.fn().mockResolvedValue([]),
    changeLocation: vi.fn(),
    resetCase: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
    listSaveSlots: vi.fn().mockResolvedValue([]),
    getBriefing: vi.fn(),
    checkMatthewTrigger: vi.fn(),
    checkMatthewAutoComment: vi.fn(),
    getCases: vi.fn().mockResolvedValue({
      cases: [
        {
          id: 'case_001',
          title: 'The Sealed Stacks',
          difficulty: 'beginner',
          description: 'A held in stillness student found in the library.',
        },
      ],
      count: 1,
      errors: null,
    }),
  };
});

// ============================================
// Test Data
// ============================================

const mockLocationData: LocationResponse = {
  id: 'library',
  name: 'Blackwood Collegiate Library - Crime Scene',
  description: 'You enter the library. A heavy oak desk dominates the center.',
  surface_elements: [
    'Oak desk with scattered papers',
    'Dark arts books on shelves',
  ],
};

// Unused - but keeping for reference
// const mockInvestigateResponse: InvestigateResponse = {
//   narrator_response: 'You examine the area carefully.',
//   new_evidence: [],
//   already_discovered: false,
// };

// ============================================
// Test Suite
// ============================================

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Set active session so App goes directly to "game" state
    localStorage.setItem('lantern-active-session', JSON.stringify({ caseId: 'case_001', slot: 'autosave' }));
    // Skip telemetry consent banner
    localStorage.setItem('telemetry_consent_shown', 'true');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  // ------------------------------------------
  // Loading State Tests
  // ------------------------------------------

  describe('Loading State', () => {
    it.todo('shows loading indicator on initial mount');
  });

  // ------------------------------------------
  // Routing Tests (added — converted from todo)
  // ------------------------------------------

  describe('Routing', () => {
    beforeEach(() => {
      vi.mocked(api.loadState).mockResolvedValue(null);
      vi.mocked(api.getLocation).mockResolvedValue(mockLocationData);
      vi.mocked(api.getWitnesses).mockResolvedValue([]);
    });

    it('renders LandingPage when route is "/"', async () => {
      renderAppAtUrl('/');

      // LandingPage shows the case Title in both the list and detail pane
      // → multiple matches expected. We assert at least one is present.
      await waitFor(() => {
        const matches = screen.getAllByText(/The Sealed Stacks/i);
        expect(matches.length).toBeGreaterThan(0);
      });
    });

    it('renders InvestigationView when route is "/case/case_001"', async () => {
      vi.mocked(api.getBriefing).mockResolvedValue({
        case_id: 'case_001',
        dossier: {
          title: 'x',
          victim: 'x',
          location: 'x',
          time: 'x',
          status: 'x',
          synopsis: 'x',
        },
        teaching_questions: [],
        transition: '',
        briefing_completed: true,
      });
      vi.mocked(api.getLocations).mockResolvedValue([
        { id: 'library', name: 'Library', type: 'crime_scene' },
      ]);

      renderAppAtUrl('/case/case_001');

      // InvestigationView's main header has an "Open system menu" button
      // (logo) once the initial loading screen completes
      await waitFor(
        () => {
          expect(
            screen.getByRole('button', { name: /open system menu/i }),
          ).toBeInTheDocument();
        },
        { timeout: 4000 },
      );
    });
  });

  // ------------------------------------------
  // Telemetry Consent Banner (added — converted from todo)
  // ------------------------------------------

  describe('Telemetry Consent Banner', () => {
    beforeEach(() => {
      vi.mocked(api.loadState).mockResolvedValue(null);
      vi.mocked(api.getLocation).mockResolvedValue(mockLocationData);
      vi.mocked(api.getWitnesses).mockResolvedValue([]);
    });

    it('appears on first visit (no telemetry_consent_shown in localStorage)', () => {
      localStorage.removeItem('telemetry_consent_shown');

      renderAppAtUrl('/');

      expect(
        screen.getByText(/Anonymous data collected to improve the game/i),
      ).toBeInTheDocument();
    });

    it('auto-dismisses after the timeout and sets telemetry_consent_shown', async () => {
      localStorage.removeItem('telemetry_consent_shown');

      renderAppAtUrl('/');

      expect(
        screen.getByText(/Anonymous data collected to improve the game/i),
      ).toBeInTheDocument();

      // Wait for the real 4-second auto-dismiss timer to fire
      await waitFor(
        () => {
          expect(
            screen.queryByText(/Anonymous data collected to improve the game/i),
          ).not.toBeInTheDocument();
        },
        { timeout: 5000 },
      );

      expect(localStorage.getItem('telemetry_consent_shown')).toBe('1');
    }, 8000);
  });

  // ------------------------------------------
  // ErrorBoundary (added — converted from todo)
  // ------------------------------------------

  describe('ErrorBoundary', () => {
    it('catches sync render errors and shows fallback UI', () => {
      // Suppress React's noisy error logging for this test
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {
        // intentionally empty — silence React error boundary noise
      });

      function Bomb(): never {
        throw new Error('boom');
      }

      render(
        <ErrorBoundary>
          <Bomb />
        </ErrorBoundary>,
      );

      expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /refresh page/i }),
      ).toBeInTheDocument();

      errorSpy.mockRestore();
    });
  });

  // ------------------------------------------
  // Theme Switching (added — converted from todo)
  // ------------------------------------------

  describe('Theme', () => {
    it('toggles between dark and light via ThemeProvider and updates document class', async () => {
      const { useTheme } = await import('../../context/useTheme');
      const { fireEvent } = await import('@testing-library/react');

      function ThemeProbe() {
        const { mode, toggleTheme } = useTheme();
        return (
          <div>
            <span data-testid="mode">{mode}</span>
            <button onClick={toggleTheme}>toggle</button>
          </div>
        );
      }

      render(
        <ThemeProvider>
          <ThemeProbe />
        </ThemeProvider>,
      );

      const initial = screen.getByTestId('mode').textContent;
      // Document class should reflect initial mode
      expect(
        document.documentElement.classList.contains(`theme-${initial}`),
      ).toBe(true);

      fireEvent.click(screen.getByRole('button', { name: /toggle/i }));

      await waitFor(() => {
        expect(screen.getByTestId('mode').textContent).not.toBe(initial);
      });

      // Document class should now reflect new mode
      const newMode = screen.getByTestId('mode').textContent;
      expect(
        document.documentElement.classList.contains(`theme-${newMode}`),
      ).toBe(true);
    });
  });

  // ------------------------------------------
  // Layout Tests
  // ------------------------------------------

  describe('Layout', () => {
    beforeEach(() => {
      vi.mocked(api.loadState).mockResolvedValue(null);
      vi.mocked(api.getLocation).mockResolvedValue(mockLocationData);
      vi.mocked(api.getWitnesses).mockResolvedValue([]);
    });

    it.todo('renders header with title');

    it.todo('renders save button');

    it.todo('renders load button');

    it.todo('renders LocationView component');

    it.todo('renders EvidenceBoard component');

    it.todo('renders Case Status panel');

    it.todo('renders Quick Help panel');
  });

  // ------------------------------------------
  // State Integration Tests
  // ------------------------------------------

  describe('State Integration', () => {
    it.todo('loads saved state on mount');

    it.todo('displays evidence count from loaded state');

    it.todo('starts with empty state when no saved state exists');
  });

  // ------------------------------------------
  // Save/Load Tests
  // ------------------------------------------

  describe('Save/Load', () => {
    beforeEach(() => {
      vi.mocked(api.loadState).mockResolvedValue(null);
      vi.mocked(api.getLocation).mockResolvedValue(mockLocationData);
      vi.mocked(api.getWitnesses).mockResolvedValue([]);
    });

    it.todo('calls saveGameState when save button clicked');

    it.todo('calls loadState when load button clicked');

    it.todo('shows error when save fails');

    it.todo('dismisses error when X clicked');
  });

  // ------------------------------------------
  // Evidence Discovery Flow Tests
  // ------------------------------------------

  describe('Evidence Discovery Flow', () => {
    beforeEach(() => {
      vi.mocked(api.loadState).mockResolvedValue(null);
      vi.mocked(api.getLocation).mockResolvedValue(mockLocationData);
      vi.mocked(api.getWitnesses).mockResolvedValue([]);
    });

    it.todo('updates evidence board when evidence discovered');

    it.todo('updates evidence count in case status');
  });
});
