/* eslint-disable @typescript-eslint/no-explicit-any */
 
 
 
/**
 * LandingPage Component Tests
 *
 * Tests for the main menu landing page (Phase 5.4):
 * - Dynamic case loading from API
 * - Loading, error, and empty states
 * - Case list display with backend data
 * - Start Case button functionality
 * - Load Game button functionality
 * - Keyboard shortcuts
 *
 * @module components/__tests__/LandingPage.test
 * @since Phase 5.3.1
 * @updated Phase 5.4 - Dynamic case loading
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '../../test/render';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { LandingPage } from '../LandingPage';
import * as client from '../../api/client';
import type { CaseListResponse } from '../../types/investigation';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// ============================================
// Mocks
// ============================================

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return {
    ...actual,
    getCases: vi.fn(),
  };
});

const mockCasesResponse: CaseListResponse = {
  cases: [
    {
      id: 'case_001',
      title: 'The Sealed Stacks',
      difficulty: 'intermediate',
      description:
        'A third-year student has been found held in stillness in the Blackwood Collegiate Library.',
    },
    {
      id: 'case_002',
      title: 'The Poisoned Potion',
      difficulty: 'advanced',
      description: 'A professor has been found unconscious after drinking a remedy.',
    },
  ],
  count: 2,
};

const mockEmptyResponse: CaseListResponse = {
  cases: [],
  count: 0,
};

const mockPartialErrorResponse: CaseListResponse = {
  cases: [
    {
      id: 'case_001',
      title: 'The Sealed Stacks',
      difficulty: 'intermediate',
      description: 'A student has been found held in stillness.',
    },
  ],
  count: 1,
  errors: ['case_002: Missing required field: title'],
};

// ============================================
// Test Data
// ============================================

const defaultProps = {
  onLoadGame: vi.fn(),
};

// ============================================
// Test Suite
// ============================================

describe('LandingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
    localStorage.removeItem('lantern-onboarding-seen');
    (client.getCases as any).mockResolvedValue(mockCasesResponse);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ------------------------------------------
  // Loading State Tests
  // ------------------------------------------

  describe('Loading State', () => {
    it.todo('displays loading state while fetching cases');

    it('shows game title during loading', () => {
      (client.getCases as any).mockImplementation(
        () => new Promise<CaseListResponse>(() => { /* intentionally never resolves */ })
      );

      render(<LandingPage {...defaultProps} />);

      expect(screen.getByText('THE LANTERN')).toBeInTheDocument();
      expect(screen.getByText(/Case Investigation System/i)).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Error State Tests
  // ------------------------------------------

  describe('Error State', () => {
    it.todo('displays error message when API fails');

    it('shows retry button on error', async () => {
      (client.getCases as any).mockRejectedValue(new Error('API error'));

      render(<LandingPage {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /RETRY/i })).toBeInTheDocument();
      });
    });

    it.todo('retries fetching when retry button clicked');
  });

  // ------------------------------------------
  // Empty State Tests
  // ------------------------------------------

  describe('Empty State', () => {
    it.todo('displays empty state when no cases available');

    it('shows help text in empty state', async () => {
      (client.getCases as any).mockResolvedValue(mockEmptyResponse);

      render(<LandingPage {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText(/Add case files/i)).toBeInTheDocument();
      });
    });
  });

  // ------------------------------------------
  // Successful Load Tests
  // ------------------------------------------

  describe('Successful Case Loading', () => {
    it('fetches cases on mount', async () => {
      render(<LandingPage {...defaultProps} />);

      await waitFor(() => {
        expect(client.getCases).toHaveBeenCalledTimes(1);
      });
    });

    it.todo('displays cases from API');

    it.todo('maps backend difficulty to frontend format');

    it('logs warnings when some cases fail to load', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => { /* suppress console output */ });

      (client.getCases as any).mockResolvedValue(mockPartialErrorResponse);

      render(<LandingPage {...defaultProps} />);

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Some cases failed to load:',
          ['case_002: Missing required field: title']
        );
      });

      consoleSpy.mockRestore();
    });
  });

  // ------------------------------------------
  // Rendering Tests
  // ------------------------------------------

  describe('Rendering', () => {
    it.todo('renders the game title');

    it.todo('renders the version text');

    it.todo('renders the Available Cases section');

    it('renders case description', async () => {
      render(<LandingPage {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText(/held in stillness/i)).toBeInTheDocument();
      });
    });

    it('shows onboarding and remembers explicit dismissal', async () => {
      render(<LandingPage {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Your own way through mysteries/i })).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /Close onboarding/i }));

      expect(screen.queryByRole('heading', { name: /Your own way through mysteries/i })).not.toBeInTheDocument();
      expect(localStorage.getItem('lantern-onboarding-seen')).toBe('true');
      expect(screen.getByRole('button', { name: /What is The Lantern/i })).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /What is The Lantern/i }));
      expect(screen.getByRole('heading', { name: /Your own way through mysteries/i })).toBeInTheDocument();
    });

    it('hides onboarding after it was dismissed on a previous visit', async () => {
      localStorage.setItem('lantern-onboarding-seen', 'true');
      render(<LandingPage {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getAllByText(/The Sealed Stacks/i).length).toBeGreaterThan(0);
      });
      expect(screen.queryByRole('heading', { name: /Your own way through mysteries/i })).not.toBeInTheDocument();
    });

    it.todo('renders Load Game button');

    it.todo('renders keyboard hints');
  });

  // ------------------------------------------
  // Button Click Tests
  // ------------------------------------------

  describe('Button Interactions', () => {
    it.todo('calls onStartNewCase with case_001 when Start Case clicked');

    it.todo('calls onLoadGame when Load Game clicked');

    it.todo('selects a different case when clicked');
  });

  // ------------------------------------------
  // Keyboard Shortcut Tests
  // ------------------------------------------

  describe('Keyboard Shortcuts', () => {
    it.todo('calls onStartNewCase when Enter pressed on selected case');

    it.todo('calls onLoadGame when L key pressed');

    it.todo('selects case with number key');

    it.todo('navigates with arrow keys');

    it.todo('does not trigger shortcuts when typing in input fields');
  });

  // ------------------------------------------
  // Styling Tests
  // ------------------------------------------

  describe('Styling', () => {
    it.todo('applies terminal B&W aesthetic');

    it.todo('has proper container styling');
  });

  // ------------------------------------------
  // Accessibility Tests
  // ------------------------------------------

  describe('Accessibility', () => {
    it.todo('has proper heading hierarchy');

    it.todo('buttons are focusable');
  });

  // ------------------------------------------
  // Single Case Tests
  // ------------------------------------------

  describe('Single Case', () => {
    it.todo('displays single case correctly');

    it.todo('starts first case with Enter key');
  });
});
