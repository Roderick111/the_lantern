/**
 * MentorFeedback Component Tests
 *
 * Tests for the mentor feedback display including:
 * - Verdict result display
 * - Score meter rendering and colors
 * - Graves's Response (natural LLM prose)
 * - Retry functionality
 * - Loading states
 *
 * @module components/__tests__/MentorFeedback.test
 * @since Phase 3
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '../../test/render';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MentorFeedback, type MentorFeedbackProps, type MentorFeedbackData } from '../MentorFeedback';

// ============================================
// Test Data
// ============================================

const mockFeedbackExcellent: MentorFeedbackData = {
  analysis: 'You correctly identified the culprit and provided strong reasoning.',
  fallacies_detected: [],
  score: 85,
  quality: 'excellent',
  critique: '',
  praise: 'Your deduction was thorough and logical.',
  hint: null,
};

const mockFeedbackPoor: MentorFeedbackData = {
  analysis: 'Your reasoning has significant gaps.',
  fallacies_detected: [
    {
      name: 'Confirmation Bias',
      description: 'You focused only on evidence supporting your theory.',
      example: 'You ignored the alibi testimony.',
    },
    {
      name: 'Correlation Not Causation',
      description: 'Presence at the scene does not prove guilt.',
      example: 'The scarf proves presence, not murder.',
    },
  ],
  score: 35,
  quality: 'poor',
  critique: 'You ignored key timeline evidence.',
  praise: '',
  hint: 'Check when the suspect actually left the library.',
};

const mockFeedbackMedium: MentorFeedbackData = {
  analysis: 'Reasonable attempt but incomplete reasoning.',
  fallacies_detected: [
    {
      name: 'Post Hoc Fallacy',
      description: 'Timing alone does not prove causation.',
      example: '',
    },
  ],
  score: 55,
  quality: 'fair',
  critique: 'Consider the magical signature evidence.',
  praise: 'Good attention to witness statements.',
  hint: null,
};

const defaultProps: MentorFeedbackProps = {
  feedback: mockFeedbackExcellent,
  correct: true,
  attemptsRemaining: 10,
};

// ============================================
// Test Suite
// ============================================

describe('MentorFeedback', () => {
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
    it('renders score meter', () => {
      render(<MentorFeedback {...defaultProps} />);
      expect(screen.getByText('85')).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('renders quality label', () => {
      render(<MentorFeedback {...defaultProps} />);
      expect(screen.getByText('Excellent')).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Verdict Result Tests
  // ------------------------------------------

  describe('Verdict Result', () => {
    it.todo('shows CORRECT banner when correct');

    it('shows INCORRECT banner when incorrect', () => {
      render(<MentorFeedback {...defaultProps} correct={false} />);
      expect(screen.getByText(/INCORRECT/i)).toBeInTheDocument();
    });

    it.todo('applies green styling to correct verdict');

    it('applies red styling to incorrect verdict', () => {
      render(<MentorFeedback {...defaultProps} correct={false} />);
      const banner = screen.getByText(/INCORRECT/i);
      expect(banner).toHaveClass('text-red-400');
    });
  });

  // ------------------------------------------
  // Score Meter Tests
  // ------------------------------------------

  describe('Score Meter', () => {
    it('shows score value for high scores (>=75)', () => {
      render(<MentorFeedback {...defaultProps} feedback={{ ...mockFeedbackExcellent, score: 80 }} />);
      expect(screen.getByText('80')).toBeInTheDocument();
    });

    it('shows score value for medium scores (50-74)', () => {
      render(<MentorFeedback {...defaultProps} feedback={mockFeedbackMedium} />);
      expect(screen.getByText('55')).toBeInTheDocument();
    });

    it('shows score value for low scores (<50)', () => {
      render(<MentorFeedback {...defaultProps} feedback={mockFeedbackPoor} correct={false} />);
      expect(screen.getByText('35')).toBeInTheDocument();
    });

    it('renders progress bar with correct width', () => {
      render(<MentorFeedback {...defaultProps} />);
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '85');
    });
  });

  // ------------------------------------------
  // Attempts Remaining Tests
  // ------------------------------------------

  describe('Attempts Remaining', () => {
    it('shows attempts remaining when incorrect', () => {
      render(<MentorFeedback {...defaultProps} correct={false} attemptsRemaining={7} />);
      expect(screen.getByText(/7 attempts remaining/i)).toBeInTheDocument();
    });

    it('does not show attempts when correct', () => {
      render(<MentorFeedback {...defaultProps} correct={true} attemptsRemaining={7} />);
      expect(screen.queryByText(/attempts remaining/i)).not.toBeInTheDocument();
    });

    it('shows low attempts remaining', () => {
      render(<MentorFeedback {...defaultProps} correct={false} attemptsRemaining={2} />);
      expect(screen.getByText(/2 attempts remaining/i)).toBeInTheDocument();
    });

    it('shows normal attempts remaining', () => {
      render(<MentorFeedback {...defaultProps} correct={false} attemptsRemaining={8} />);
      expect(screen.getByText(/8 attempts remaining/i)).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Retry Button Tests
  // ------------------------------------------

  describe('Retry Button', () => {
    it('renders retry button when incorrect and has attempts', () => {
      const mockOnRetry = vi.fn();
      render(
        <MentorFeedback
          {...defaultProps}
          correct={false}
          attemptsRemaining={5}
          onRetry={mockOnRetry}
        />
      );
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('calls onRetry when clicked', async () => {
      const mockOnRetry = vi.fn();
      const user = userEvent.setup();

      render(
        <MentorFeedback
          {...defaultProps}
          correct={false}
          attemptsRemaining={5}
          onRetry={mockOnRetry}
        />
      );

      await user.click(screen.getByRole('button', { name: /try again/i }));
      expect(mockOnRetry).toHaveBeenCalled();
    });

    it('does not render retry when correct', () => {
      const mockOnRetry = vi.fn();
      render(
        <MentorFeedback
          {...defaultProps}
          correct={true}
          attemptsRemaining={5}
          onRetry={mockOnRetry}
        />
      );
      expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
    });

    it('does not render retry when no attempts remaining', () => {
      const mockOnRetry = vi.fn();
      render(
        <MentorFeedback
          {...defaultProps}
          correct={false}
          attemptsRemaining={0}
          onRetry={mockOnRetry}
        />
      );
      expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
    });

    it('shows max attempts message when exhausted', () => {
      render(
        <MentorFeedback
          {...defaultProps}
          correct={false}
          attemptsRemaining={0}
        />
      );
      expect(screen.getByText(/exhausted all attempts/i)).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Wrong Suspect Response Tests
  // ------------------------------------------

  describe('Wrong Suspect Response', () => {
    it('renders LLM-generated analysis when provided', () => {
      const feedbackWithAnalysis: MentorFeedbackData = {
        analysis: "WRONG. You accused Elena because she 'seemed suspicious'? Confirmation bias - check the frost pattern direction!",
        fallacies_detected: [],
        score: 20,
        quality: 'poor',
        critique: '',
        praise: '',
        hint: null,
      };

      render(
        <MentorFeedback
          {...defaultProps}
          correct={false}
          feedback={feedbackWithAnalysis}
          wrongSuspectResponse={null}
        />
      );
      expect(screen.getByText(/Graves's Response/i)).toBeInTheDocument();
      expect(screen.getByText(/Confirmation bias/i)).toBeInTheDocument();
    });

    it('does not render Graves section when analysis is empty', () => {
      const feedbackNoAnalysis: MentorFeedbackData = {
        analysis: '',
        fallacies_detected: [],
        score: 20,
        quality: 'poor',
        critique: '',
        praise: '',
        hint: null,
      };

      render(
        <MentorFeedback
          {...defaultProps}
          correct={false}
          feedback={feedbackNoAnalysis}
          wrongSuspectResponse={null}
        />
      );
      expect(screen.queryByText(/Graves's Response/i)).not.toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Loading State Tests (Phase 3.1)
  // ------------------------------------------

  describe('Loading State', () => {
    it('shows loading spinner when isLoading is true', () => {
      render(
        <MentorFeedback
          {...defaultProps}
          isLoading={true}
          feedback={undefined}
        />
      );

      expect(screen.getByText(/Graves is reviewing your case/i)).toBeInTheDocument();
    });

    it('does not show feedback content when loading', () => {
      render(
        <MentorFeedback
          {...defaultProps}
          isLoading={true}
          feedback={mockFeedbackExcellent}
        />
      );

      // Should show loading, not the feedback
      expect(screen.getByText(/Graves is reviewing your case/i)).toBeInTheDocument();
      expect(screen.queryByText(/Correct/i)).not.toBeInTheDocument();
    });

    it.todo('shows feedback when not loading and feedback provided');

    it('renders nothing when not loading and no feedback', () => {
      const { container } = render(
        <MentorFeedback
          {...defaultProps}
          isLoading={false}
          feedback={undefined}
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it('loading state has proper ARIA attributes', () => {
      render(
        <MentorFeedback
          {...defaultProps}
          isLoading={true}
          feedback={undefined}
        />
      );

      const loadingContainer = screen.getByRole('status');
      expect(loadingContainer).toHaveAttribute('aria-live', 'polite');
      expect(loadingContainer).toHaveAttribute('aria-busy', 'true');
    });

    it('loading spinner has aria-hidden', () => {
      render(
        <MentorFeedback
          {...defaultProps}
          isLoading={true}
          feedback={undefined}
        />
      );

      // The spinner div should be aria-hidden for screen readers
      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toHaveAttribute('aria-hidden', 'true');
    });
  });
});
