/**
 * VerdictSubmission Component Tests
 *
 * Tests for the verdict submission form including:
 * - Suspect dropdown rendering and selection
 * - Reasoning textarea validation
 * - Evidence checklist selection
 * - Submit button states
 * - Loading and disabled states
 *
 * @module components/__tests__/VerdictSubmission.test
 * @since Phase 3
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '../../test/render';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VerdictSubmission, type VerdictSubmissionProps } from '../VerdictSubmission';

// ============================================
// Test Data
// ============================================

const mockSuspects = [
  { id: 'elena', name: 'Elena Marsh' },
  { id: 'cassian', name: 'Cassian Thorne' },
  { id: 'rowan', name: 'Rowan Ashford' },
];

const mockEvidence = [
  { id: 'frost_pattern', name: 'Frost Pattern' },
  { id: 'focus_signature', name: 'Focus Signature' },
  { id: 'hidden_note', name: 'Hidden Note' },
];

const defaultProps: VerdictSubmissionProps = {
  suspects: mockSuspects,
  discoveredEvidence: mockEvidence,
  onSubmit: vi.fn(),
  loading: false,
  disabled: false,
  attemptsRemaining: 10,
};

// ============================================
// Test Suite
// ============================================

describe('VerdictSubmission', () => {
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
    it.todo('renders header');

    it('renders suspect dropdown', () => {
      render(<VerdictSubmission {...defaultProps} />);
      expect(screen.getByLabelText(/Select suspect/i)).toBeInTheDocument();
    });

    it('renders all suspects in dropdown', () => {
      render(<VerdictSubmission {...defaultProps} />);
      const select = screen.getByLabelText(/Select suspect/i);

      expect(select).toBeInTheDocument();
      expect(screen.getByText('Elena Marsh')).toBeInTheDocument();
      expect(screen.getByText('Cassian Thorne')).toBeInTheDocument();
      expect(screen.getByText('Rowan Ashford')).toBeInTheDocument();
    });

    it('renders reasoning textarea', () => {
      render(<VerdictSubmission {...defaultProps} />);
      expect(screen.getByLabelText(/enter your reasoning/i)).toBeInTheDocument();
    });

    it('renders evidence checklist', () => {
      render(<VerdictSubmission {...defaultProps} />);

      expect(screen.getByText('Frost Pattern')).toBeInTheDocument();
      expect(screen.getByText('Focus Signature')).toBeInTheDocument();
      expect(screen.getByText('Hidden Note')).toBeInTheDocument();
    });

    it('renders submit button', () => {
      render(<VerdictSubmission {...defaultProps} />);
      expect(screen.getByRole('button', { name: /submit verdict/i })).toBeInTheDocument();
    });

    it.todo('renders attempts remaining');

    it.todo('renders character count');
  });

  // ------------------------------------------
  // Suspect Selection Tests
  // ------------------------------------------

  describe('Suspect Selection', () => {
    it('allows selecting a suspect', async () => {
      const user = userEvent.setup();
      render(<VerdictSubmission {...defaultProps} />);

      const select = screen.getByLabelText(/Select suspect/i);
      await user.selectOptions(select, 'cassian');

      expect(select).toHaveValue('cassian');
    });

    it('starts with no suspect selected', () => {
      render(<VerdictSubmission {...defaultProps} />);
      const select = screen.getByLabelText(/Select suspect/i);
      expect(select).toHaveValue('');
    });
  });

  // ------------------------------------------
  // Reasoning Textarea Tests
  // ------------------------------------------

  describe('Reasoning Textarea', () => {
    it('allows typing reasoning', async () => {
      const user = userEvent.setup();
      render(<VerdictSubmission {...defaultProps} />);

      const textarea = screen.getByLabelText(/enter your reasoning/i);
      await user.type(textarea, 'This is my reasoning for the accusation.');

      expect(textarea).toHaveValue('This is my reasoning for the accusation.');
    });

    it.todo('updates character count as user types');

    it.todo('shows characters needed when under minimum');

    it.todo('shows green character count when minimum met');
  });

  // ------------------------------------------
  // Evidence Selection Tests
  // ------------------------------------------

  describe('Evidence Selection', () => {
    it('allows selecting evidence', async () => {
      const user = userEvent.setup();
      render(<VerdictSubmission {...defaultProps} />);

      const checkbox = screen.getByRole('checkbox', { name: /frost pattern/i });
      await user.click(checkbox);

      expect(checkbox).toBeChecked();
    });

    it('allows selecting multiple evidence', async () => {
      const user = userEvent.setup();
      render(<VerdictSubmission {...defaultProps} />);

      await user.click(screen.getByRole('checkbox', { name: /frost pattern/i }));
      await user.click(screen.getByRole('checkbox', { name: /focus signature/i }));

      expect(screen.getByRole('checkbox', { name: /frost pattern/i })).toBeChecked();
      expect(screen.getByRole('checkbox', { name: /focus signature/i })).toBeChecked();
    });

    it('allows deselecting evidence', async () => {
      const user = userEvent.setup();
      render(<VerdictSubmission {...defaultProps} />);

      const checkbox = screen.getByRole('checkbox', { name: /frost pattern/i });
      await user.click(checkbox);
      await user.click(checkbox);

      expect(checkbox).not.toBeChecked();
    });

    it.todo('shows evidence count when selected');
  });

  // ------------------------------------------
  // Submit Button Tests
  // ------------------------------------------

  describe('Submit Button', () => {
    it('is disabled when no suspect selected', () => {
      render(<VerdictSubmission {...defaultProps} />);
      expect(screen.getByRole('button', { name: /submit verdict/i })).toBeDisabled();
    });

    it('is disabled when reasoning too short', async () => {
      const user = userEvent.setup();
      render(<VerdictSubmission {...defaultProps} />);

      await user.selectOptions(screen.getByLabelText(/Select suspect/i), 'cassian');
      await user.type(screen.getByLabelText(/enter your reasoning/i), 'Too short');

      expect(screen.getByRole('button', { name: /submit verdict/i })).toBeDisabled();
    });

    it('is enabled when form is valid', async () => {
      const user = userEvent.setup();
      render(<VerdictSubmission {...defaultProps} />);

      await user.selectOptions(screen.getByLabelText(/Select suspect/i), 'cassian');
      await user.type(
        screen.getByLabelText(/enter your reasoning/i),
        'This is my detailed reasoning that explains why this suspect is guilty of the crime.'
      );

      expect(screen.getByRole('button', { name: /submit verdict/i })).not.toBeDisabled();
    });

    it('is disabled when loading', async () => {
      const user = userEvent.setup();
      render(<VerdictSubmission {...defaultProps} loading={true} />);

      await user.selectOptions(screen.getByLabelText(/Select suspect/i), 'cassian');

      expect(screen.getByRole('button', { name: /TRANSMITTING.../i })).toBeDisabled();
    });

    it('is disabled when disabled prop is true', () => {
      render(<VerdictSubmission {...defaultProps} disabled={true} />);
      expect(screen.getByRole('button', { name: /submit verdict/i })).toBeDisabled();
    });
  });

  // ------------------------------------------
  // Submission Tests
  // ------------------------------------------

  describe('Submission', () => {
    it('calls onSubmit with correct data', async () => {
      const mockOnSubmit = vi.fn().mockResolvedValue(undefined);
      const user = userEvent.setup();

      render(<VerdictSubmission {...defaultProps} onSubmit={mockOnSubmit} />);

      await user.selectOptions(screen.getByLabelText(/Select suspect/i), 'cassian');
      await user.type(
        screen.getByLabelText(/enter your reasoning/i),
        'Cassian is guilty because of the frost pattern and focus signature evidence.'
      );
      await user.click(screen.getByRole('checkbox', { name: /frost pattern/i }));
      await user.click(screen.getByRole('button', { name: /submit verdict/i }));

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          'cassian',
          'Cassian is guilty because of the frost pattern and focus signature evidence.',
          ['frost_pattern']
        );
      });
    });

    it('shows validation error when suspect not selected', async () => {
      const user = userEvent.setup();
      render(<VerdictSubmission {...defaultProps} />);

      await user.type(
        screen.getByLabelText(/enter your reasoning/i),
        'This is my detailed reasoning that explains why this suspect is guilty of the crime.'
      );

      // The button should be disabled, so we check validation works
      expect(screen.getByRole('button', { name: /submit verdict/i })).toBeDisabled();
    });

    it('shows loading state during submission', () => {
      render(<VerdictSubmission {...defaultProps} loading={true} />);
      expect(screen.getByText(/TRANSMITTING.../i)).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Disabled State Tests
  // ------------------------------------------

  describe('Disabled State', () => {
    it('disables all inputs when disabled', () => {
      render(<VerdictSubmission {...defaultProps} disabled={true} />);

      expect(screen.getByLabelText(/Select suspect/i)).toBeDisabled();
      expect(screen.getByLabelText(/enter your reasoning/i)).toBeDisabled();
      mockEvidence.forEach(e => {
        expect(screen.getByRole('checkbox', { name: new RegExp(e.name, 'i') })).toBeDisabled();
      });
    });

    it('shows message when no attempts remaining', () => {
      render(<VerdictSubmission {...defaultProps} disabled={true} attemptsRemaining={0} />);
      expect(screen.getByText(/CASE_CLOSED: ATTEMPTS_EXHAUSTED/i)).toBeInTheDocument();
    });

    it('shows low attempts warning', () => {
      render(<VerdictSubmission {...defaultProps} attemptsRemaining={2} />);
      const attemptsText = screen.getByText('[02/10]');
      expect(attemptsText).toHaveClass('text-red-400');
    });
  });

  // ------------------------------------------
  // Empty Evidence Tests
  // ------------------------------------------

  describe('Empty Evidence List', () => {
    it('does not render evidence section when no evidence', () => {
      render(<VerdictSubmission {...defaultProps} discoveredEvidence={[]} />);
      expect(screen.queryByText(/key evidence/i)).not.toBeInTheDocument();
    });
  });
});
