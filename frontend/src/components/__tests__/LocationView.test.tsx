
/**
 * LocationView Component Tests
 *
 * Tests for the main investigation interface including:
 * - Rendering location data
 * - Freeform input handling
 * - API integration (mocked)
 * - Loading and error states
 * - Conversation history
 * - Terminal shortcuts
 *
 * @module components/__tests__/LocationView.test
 * @since Phase 1, updated Phase 2.5
 */

import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from 'vitest';
import { render } from '../../test/render';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LocationView } from '../LocationView';
import * as api from '../../api/client';
import type { LocationResponse, InvestigateResponse } from '../../types/investigation';

// ============================================
// Mocks
// ============================================

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return {
    ...actual,
    investigate: vi.fn(),
    investigateStream: vi.fn(),
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
    'Frost-covered window',
  ],
};

const mockInvestigateResponse: InvestigateResponse = {
  narrator_response: 'You carefully examine the area under the desk and find a crumpled note.',
  new_evidence: ['hidden_note'],
  already_discovered: false,
};

const defaultProps = {
  caseId: 'case_001',
  locationId: 'library',
  locationData: mockLocationData,
  onEvidenceDiscovered: vi.fn(),
  discoveredEvidence: [],
};

// ============================================
// Test Suite
// ============================================

describe('LocationView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ------------------------------------------
  // Rendering Tests
  // ------------------------------------------

  describe('Rendering', () => {
    it('renders location name', () => {
      render(<LocationView {...defaultProps} />);

      expect(screen.getByText(/Blackwood Collegiate Library - Crime Scene/i)).toBeInTheDocument();
    });

    it('renders location description', () => {
      render(<LocationView {...defaultProps} />);

      expect(
        screen.getByText(/You enter the library\. A heavy oak desk dominates the center\./i)
      ).toBeInTheDocument();
    });

    it('does not render explicit surface elements list (integrated into prose)', () => {
      render(<LocationView {...defaultProps} />);

      // Surface elements should NOT be displayed as explicit list items
      // They are now integrated into the narrator's prose response
      expect(screen.queryByText('You can see:')).not.toBeInTheDocument();
    });

    it('renders input textarea with terminal-style placeholder', () => {
      render(<LocationView {...defaultProps} />);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveAttribute('rows', '3');
    });

    it('renders quick action shortcuts', () => {
      render(<LocationView {...defaultProps} />);

      expect(screen.getByRole('button', { name: /examine desk/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /check window/i })).toBeInTheDocument();
    });

    it('renders loading state when locationData is null', () => {
      render(<LocationView {...defaultProps} locationData={null} />);

      expect(screen.getByText(/Loading location/i)).toBeInTheDocument();
    });

    // Witness shortcuts disabled - feature reserved for future implementation
    it.skip('renders witness shortcuts when witnesses are present', () => {
      // Test disabled - witnessesPresent prop removed
    });
  });

  // ------------------------------------------
  // Quick Actions Tests
  // ------------------------------------------

  describe('Quick Actions', () => {
    it('fills input when quick action clicked (does not submit)', async () => {
      const user = userEvent.setup();
      render(<LocationView {...defaultProps} />);

      const examineButton = screen.getByRole('button', { name: /examine desk/i });
      await user.click(examineButton);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      expect(textarea).toHaveValue('examine the desk');
      expect(api.investigate).not.toHaveBeenCalled();
    });

    // Witness click handler disabled - feature reserved for future implementation
    it.skip('calls onWitnessClick when witness shortcut clicked', async () => {
      // Test disabled - onWitnessClick prop removed
    });
  });

  // ------------------------------------------
  // Input Handling Tests
  // ------------------------------------------

  describe('Input Handling', () => {
    it('updates input value when typing', async () => {
      const user = userEvent.setup();
      render(<LocationView {...defaultProps} />);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      await user.type(textarea, 'I check the bookshelf');

      expect(textarea).toHaveValue('I check the bookshelf');
    });

    it.todo('shows Ctrl+Enter hint');
  });

  // ------------------------------------------
  // Validation Tests (added — converted from todo)
  // ------------------------------------------

  describe('Validation', () => {
    it('shows inline error and does NOT call investigateStream when input is empty', async () => {
      const user = userEvent.setup();
      render(<LocationView {...defaultProps} />);

      // SEND button is disabled when input empty, but we can force-submit
      // via Enter on an empty (whitespace) input
      const textarea = screen.getByPlaceholderText(/describe your action/i);
      await user.click(textarea);
      await user.keyboard('   '); // whitespace only
      await user.keyboard('{Enter}');

      // No backend call was attempted
      expect(api.investigateStream).not.toHaveBeenCalled();

      // Inline error is shown
      await waitFor(() => {
        expect(
          screen.getByText(/please enter an action to investigate/i),
        ).toBeInTheDocument();
      });
    });
  });

  // ------------------------------------------
  // API Integration Tests
  // ------------------------------------------

  describe('API Integration', () => {
    it('calls investigateStream with correct payload on submit', async () => {
      const user = userEvent.setup();
      (api.investigateStream as Mock).mockImplementation(
        (
          _req: unknown,
          callbacks: {
            onChunk: (t: string) => void;
            onDone: (d: Record<string, unknown>) => void;
          },
        ) => {
          callbacks.onChunk('You find nothing of note.');
          callbacks.onDone({ new_evidence: [], evidence_names: {} });
        },
      );

      render(<LocationView {...defaultProps} />);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      await user.type(textarea, 'I search under the desk');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(api.investigateStream).toHaveBeenCalledTimes(1);
      });

      // Verify the request payload
      const firstCall = (api.investigateStream as Mock).mock.calls[0];
      const requestArg = firstCall[0] as Record<string, unknown>;
      expect(requestArg).toMatchObject({
        player_input: 'I search under the desk',
        case_id: 'case_001',
        location_id: 'library',
        slot: 'autosave',
      });
      expect(requestArg).toHaveProperty('player_id');
    });

    it('accumulates streaming chunks into the narrator message', async () => {
      const user = userEvent.setup();
      (api.investigateStream as Mock).mockImplementation(
        (
          _req: unknown,
          callbacks: {
            onChunk: (t: string) => void;
            onDone: (d: Record<string, unknown>) => void;
          },
        ) => {
          callbacks.onChunk('You search ');
          callbacks.onChunk('carefully and ');
          callbacks.onChunk('find a clue.');
          callbacks.onDone({ new_evidence: [], evidence_names: {} });
        },
      );

      render(<LocationView {...defaultProps} />);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      await user.type(textarea, 'search desk');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(
          screen.getByText(/You search carefully and find a clue\./),
        ).toBeInTheDocument();
      });
    });

    it('strips [EVIDENCE: id] tags from rendered text and calls onEvidenceDiscovered', async () => {
      const user = userEvent.setup();
      const onEvidenceDiscovered = vi.fn();
      (api.investigateStream as Mock).mockImplementation(
        (
          _req: unknown,
          callbacks: {
            onChunk: (t: string) => void;
            onDone: (d: Record<string, unknown>) => void;
          },
        ) => {
          callbacks.onChunk(
            'You find a hidden note. [EVIDENCE: hidden_note]',
          );
          callbacks.onDone({
            new_evidence: ['hidden_note'],
            evidence_names: { hidden_note: 'Hidden Note' },
          });
        },
      );

      render(
        <LocationView
          {...defaultProps}
          onEvidenceDiscovered={onEvidenceDiscovered}
        />,
      );

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      await user.type(textarea, 'search desk');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(onEvidenceDiscovered).toHaveBeenCalledWith(['hidden_note']);
      });

      // Tag stripped from displayed text
      expect(screen.queryByText(/\[EVIDENCE: hidden_note\]/)).not.toBeInTheDocument();
      // Clean narrator text remains
      expect(screen.getByText(/You find a hidden note\./)).toBeInTheDocument();
    });

    it.todo('displays narrator response after successful submit');

    it.todo('shows evidence discovery indicator');

    it.todo('does not call onEvidenceDiscovered when no evidence found');

    it('clears input after successful submit', async () => {
      const user = userEvent.setup();
      (api.investigate as Mock).mockResolvedValueOnce(mockInvestigateResponse);

      render(<LocationView {...defaultProps} />);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      await user.type(textarea, 'I search under the desk');
      await user.keyboard('{Control>}{Enter}{/Control}');

      await waitFor(() => {
        expect(textarea).toHaveValue('');
      });
    });
  });

  // ------------------------------------------
  // Loading State Tests
  // ------------------------------------------

  describe('Loading State', () => {
    it.todo('shows loading indicator during API call');

    it('disables textarea and SEND button while stream is in flight', async () => {
      const user = userEvent.setup();
      let resolveStream: (() => void) | undefined;
      (api.investigateStream as Mock).mockImplementation(
        (_req: unknown, _callbacks: unknown) =>
          new Promise<void>((resolve) => {
            resolveStream = resolve;
          }),
      );

      render(<LocationView {...defaultProps} />);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      const sendButton = screen.getByRole('button', { name: /submit action/i });

      await user.type(textarea, 'I search the desk');
      await user.keyboard('{Enter}');

      // While the stream is pending: input disabled, send button disabled
      await waitFor(() => {
        expect(textarea).toBeDisabled();
      });
      expect(sendButton).toBeDisabled();

      // Clean up dangling promise
      resolveStream?.();
    });
  });

  // ------------------------------------------
  // Error Handling Tests
  // ------------------------------------------

  describe('Error Handling', () => {
    it.todo('displays error message on API failure');

    it.todo('displays network error message');

    it.todo('clears error when successful submit follows');
  });

  // ------------------------------------------
  // Conversation History Tests
  // ------------------------------------------

  describe('Conversation History', () => {
    it('displays player action in history', async () => {
      const user = userEvent.setup();
      (api.investigate as Mock).mockResolvedValueOnce(mockInvestigateResponse);

      render(<LocationView {...defaultProps} />);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      await user.type(textarea, 'I search under the desk');
      await user.keyboard('{Control>}{Enter}{/Control}');

      await waitFor(() => {
        expect(screen.getByText(/I search under the desk/i)).toBeInTheDocument();
      });
    });

    it.todo('maintains history of multiple interactions');
  });

  // ------------------------------------------
  // Keyboard Shortcuts Tests
  // ------------------------------------------

  describe('Keyboard Shortcuts', () => {
    it.todo('submits on Ctrl+Enter');

    it.todo('submits on Cmd+Enter (Mac)');
  });

  // ------------------------------------------
  // Quick Actions Tests (Phase 5.3.1 - Design System)
  // ------------------------------------------

  describe('Quick Actions (Design System)', () => {
    it.todo('renders quick action buttons');

    it('fills input with action text when examine desk clicked', async () => {
      const user = userEvent.setup();
      render(<LocationView {...defaultProps} />);

      const button = screen.getByRole('button', { name: /examine desk/i });
      await user.click(button);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      expect(textarea).toHaveValue("examine the desk");
    });

    it('fills input with action text when check window clicked', async () => {
      const user = userEvent.setup();
      render(<LocationView {...defaultProps} />);

      const button = screen.getByRole('button', { name: /check window/i });
      await user.click(button);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      expect(textarea).toHaveValue("check the window");
    });

    it('fills input with inner voice prompt when ask voice clicked', async () => {
      const user = userEvent.setup();
      render(<LocationView {...defaultProps} />);

      const button = screen.getByRole('button', { name: /ask voice/i });
      await user.click(button);

      const textarea = screen.getByPlaceholderText(/describe your action/i);
      expect(textarea).toHaveValue("Voice, what do you think?");
    });

    it('does NOT auto-submit when quick action clicked', async () => {
      const user = userEvent.setup();
      render(<LocationView {...defaultProps} />);

      const button = screen.getByRole('button', { name: /examine desk/i });
      await user.click(button);

      // Should NOT call investigate API
      expect(api.investigate).not.toHaveBeenCalled();
    });

    it.todo('allows editing action text before submission');

    it.todo('quick action buttons have B&W styling');
  });

  // ------------------------------------------
  // Lantern Compendium Tests (Phase 4.5)
  // ------------------------------------------

  describe("Lantern Compendium (Phase 4.5)", () => {
    it.todo('renders Handbook button');

    it.todo('opens Handbook modal when button clicked');

    it.todo('opens Handbook modal on Ctrl+H');

    it.todo('opens Handbook modal on Cmd+H (Mac)');

    it.todo('closes Handbook modal on second Ctrl+H press');

    it.todo('Handbook shows all 7 rites');

    it.todo('Handbook button has title with keyboard shortcut');
  });
});
