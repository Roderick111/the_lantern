/**
 * BriefingModal Component Tests
 *
 * Tests for the dialogue-based briefing UI:
 * - Dialogue feed display (no separated boxes)
 * - Interactive teaching question with choices
 * - Q&A conversation history
 * - Text input for follow-up questions
 * - Start Investigation button
 *
 * @module components/__tests__/BriefingModal.test
 * @since Phase 3.6
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '../../test/render';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BriefingModal, type BriefingModalProps } from '../BriefingModal';
import { BriefingCompleteResponseSchema } from '../../api/schemas';
import type {
  BriefingContent,
  BriefingConversation,
} from '../../types/investigation';

// ============================================
// Test Data
// ============================================

const mockBriefing: BriefingContent = {
  case_id: 'case_001',
  dossier: {
    title: 'The Sealed Stacks',
    victim: 'Third-year student',
    location: 'Blackwood Collegiate Library, Sealed Stacks',
    time: 'Approximately 9:15pm last night',
    status: 'Found held in stillness near frost-covered window',
    synopsis: `*Inspector Graves tosses a thin case file onto the desk*

VICTIM: Third-year student
LOCATION: Blackwood Collegiate Library, Sealed Stacks
TIME: Approximately 9:15pm last night
STATUS: Found held in stillness near frost-covered window`,
  },
  teaching_questions: [
    {
      prompt: `Before you start, recruit - a question:

Out of 100 school incidents ruled "accidents," how many actually ARE accidents?`,
      choices: [
        {
          id: '25_percent',
          text: '25%',
          response: '*eye narrows* Too low. You\'re being paranoid.',
        },
        {
          id: '50_percent',
          text: '50%',
          response: 'Not quite. You\'re guessing, not deducing.',
        },
        {
          id: '85_percent',
          text: '85%',
          response: '*nods* Correct. 85%. Blackwood Collegiate is dangerous.',
        },
        {
          id: 'almost_all',
          text: 'Almost all (95%+)',
          response: 'Close, but overcorrecting. 85% is the number.',
        },
      ],
      concept_summary:
        "That's base rates, recruit. Always start with what's LIKELY.",
    },
  ],
  transition: `Now get to work. The library's waiting.

TRUST NOTHING UNSEEN.`,
  briefing_completed: false,
};

const mockConversation: BriefingConversation[] = [
  {
    question: 'What are base rates?',
    answer: 'Base rates are prior probabilities. Most Blackwood Collegiate accidents are just accidents.',
  },
];

const defaultProps: BriefingModalProps = {
  briefing: mockBriefing,
  conversation: [],
  selectedChoice: null,
  choiceResponse: null,
  onSelectChoice: vi.fn(),
  onResetChoice: vi.fn(),
  onAskQuestion: vi.fn(),
  onComplete: vi.fn(),
  loading: false,
};

// ============================================
// Test Suite
// ============================================

describe('BriefingModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ------------------------------------------
  // Dialogue Feed Tests
  // ------------------------------------------

  describe('Dialogue Feed', () => {
    it('renders case assignment as Graves message', () => {
      render(<BriefingModal {...defaultProps} />);

      expect(screen.getByText(/VICTIM: Third-year student/)).toBeInTheDocument();
    });

    it.todo('displays GRAVES label for case assignment');

    it.todo('renders teaching question prompt');

    it.todo('hides transition text when no questions asked');

    it.todo('hides TRUST NOTHING UNSEEN when no questions asked');

    it('displays transition text after asking question', () => {
      render(<BriefingModal {...defaultProps} initialStep={2} conversation={mockConversation} />);

      expect(screen.getByText(/Now get to work/)).toBeInTheDocument();
    });

    it('displays TRUST NOTHING UNSEEN after asking question', () => {
      render(<BriefingModal {...defaultProps} initialStep={2} conversation={mockConversation} />);

      expect(screen.getByText(/TRUST NOTHING UNSEEN/)).toBeInTheDocument();
    });

    it('preserves whitespace in messages', () => {
      render(<BriefingModal {...defaultProps} />);

      const content = screen.getByText(/VICTIM: Third-year student/);
      expect(content).toHaveClass('whitespace-pre-wrap');
    });
  });

  // ------------------------------------------
  // Teaching Question Choice Tests
  // ------------------------------------------

  describe('Teaching Question Choices', () => {
    it('renders choice buttons when not answered', () => {
      render(<BriefingModal {...defaultProps} initialStep={1} />);

      expect(screen.getByRole('button', { name: /25%/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /50%/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /85%/i })).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /almost all/i }),
      ).toBeInTheDocument();
    });

    it('calls onSelectChoice with choice id and question index when choice clicked', async () => {
      const user = userEvent.setup();
      const onSelectChoice = vi.fn();

      render(
        <BriefingModal
          {...defaultProps}
          initialStep={1}
          onSelectChoice={onSelectChoice}
        />,
      );

      await user.click(screen.getByRole('button', { name: /85%/i }));

      // Question index for first teaching question = 0
      expect(onSelectChoice).toHaveBeenCalledWith('85_percent', 0);
    });

    it('hides choice buttons after selection', () => {
      render(
        <BriefingModal
          {...defaultProps}
          selectedChoice="85_percent"
          choiceResponse="*nods* Correct. 85%. Blackwood Collegiate is dangerous."
        />
      );

      expect(screen.queryByRole('button', { name: '25%' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: '50%' })).not.toBeInTheDocument();
    });

    it.todo('shows player choice as message after selection');

    it.todo('shows YOU label for player choice');

    it.todo('shows Graves response after selection');

    it.todo('shows concept summary after response');

    it.todo('choice buttons have amber text');

    it.todo('choice buttons are disabled when loading');
  });

  // ------------------------------------------
  // Q&A Section Tests
  // ------------------------------------------

  describe('Q&A Section', () => {
    it.todo('renders question input');

    it('renders Ask button', () => {
      render(<BriefingModal {...defaultProps} initialStep={2} />);

      expect(screen.getByRole('button', { name: 'Send Message' })).toBeInTheDocument();
    });

    it.todo('input has aria-label');

    it.todo('displays conversation history');

    it.todo('shows Ctrl+Enter hint');
  });

  // ------------------------------------------
  // Question Submission Tests
  // ------------------------------------------

  describe('Question Submission', () => {
    it('calls onAskQuestion with question text when form is submitted', async () => {
      const user = userEvent.setup();
      const onAskQuestion = vi.fn().mockResolvedValue(undefined);

      render(
        <BriefingModal
          {...defaultProps}
          initialStep={2}
          onAskQuestion={onAskQuestion}
        />,
      );

      const textarea = screen.getByPlaceholderText(/ask Graves/i);
      await user.type(textarea, 'What are base rates?');
      await user.click(screen.getByRole('button', { name: 'Send Message' }));

      await waitFor(() => {
        expect(onAskQuestion).toHaveBeenCalledWith('What are base rates?');
      });
    });

    it('clears input after submission', async () => {
      const user = userEvent.setup();
      const onAskQuestion = vi.fn().mockResolvedValue(undefined);

      render(
        <BriefingModal
          {...defaultProps}
          initialStep={2}
          onAskQuestion={onAskQuestion}
        />,
      );

      const textarea = screen.getByPlaceholderText(/ask Graves/i);
      await user.type(textarea, 'What are base rates?');
      await user.click(screen.getByRole('button', { name: 'Send Message' }));

      await waitFor(() => {
        expect(textarea).toHaveValue('');
      });
    });

    it.todo('trims whitespace from question');

    it('does not submit empty questions', async () => {
      const user = userEvent.setup();
      const onAskQuestion = vi.fn().mockResolvedValue(undefined);

      render(<BriefingModal {...defaultProps} initialStep={2} onAskQuestion={onAskQuestion} />);

      await user.click(screen.getByRole('button', { name: 'Send Message' }));

      expect(onAskQuestion).not.toHaveBeenCalled();
    });

    it.todo('submits on Ctrl+Enter');

    it.todo('submits on Meta+Enter (Mac)');
  });

  // ------------------------------------------
  // Start Investigation Button Tests
  // ------------------------------------------

  describe('Start Investigation Button', () => {
    it('renders Start Investigation button', () => {
      render(<BriefingModal {...defaultProps} initialStep={2} />);

      expect(
        screen.getByRole('button', { name: 'Start Investigation' })
      ).toBeInTheDocument();
    });

    it.todo('button has amber background');

    it('button has uppercase text', () => {
      render(<BriefingModal {...defaultProps} initialStep={2} />);

      const button = screen.getByRole('button', { name: 'Start Investigation' });
      expect(button).toHaveClass('uppercase');
    });

    it('calls onComplete when button clicked', async () => {
      const user = userEvent.setup();
      const onComplete = vi.fn();

      render(<BriefingModal {...defaultProps} initialStep={2} onComplete={onComplete} />);

      await user.click(
        screen.getByRole('button', { name: 'Start Investigation' })
      );

      expect(onComplete).toHaveBeenCalled();
    });

    it.todo('button is disabled when loading');

    // Bug #5 fix: schema now accepts the real backend payload
    // {success: true, updated_state: {...}}. Previously Start Investigation
    // crashed because .strict() rejected the unknown `updated_state` key.
    it('schema accepts realistic backend response with updated_state', () => {
      const realisticBackendPayload = {
        success: true,
        updated_state: {
          case_id: 'case_001',
          briefing_completed: true,
        },
      };

      const result = BriefingCompleteResponseSchema.safeParse(
        realisticBackendPayload,
      );

      expect(result.success).toBe(true);
    });
  });

  // ------------------------------------------
  // Loading State Tests
  // ------------------------------------------

  describe('Loading States', () => {
    it.todo('disables input when loading');

    it.todo('disables Ask button when loading');

    it.todo('shows loading spinner on Ask button');

    it.todo('does not submit question when loading');
  });

  // ------------------------------------------
  // Button State Tests
  // ------------------------------------------

  describe('Button States', () => {
    it('Ask button disabled when input is empty', () => {
      render(<BriefingModal {...defaultProps} initialStep={2} />);

      const button = screen.getByRole('button', { name: 'Send Message' });
      expect(button).toBeDisabled();
    });

    it.todo('Ask button enabled when input has text');
  });

  // ------------------------------------------
  // Styling Tests
  // ------------------------------------------

  describe('Styling', () => {
    it.todo('uses font-mono throughout');

    it.todo('has gray-900 background');

    it.todo('has max-height for scrolling');

    it.todo('has overflow-y-auto for scrolling');

    it.todo('input has focus ring styling');
  });

  // ------------------------------------------
  // Accessibility Tests
  // ------------------------------------------

  describe('Accessibility', () => {
    it.todo('input is a textarea for multiline questions');

    it.todo('textarea is resizable none');

    it.todo('loading spinner is aria-hidden');
  });

  // ------------------------------------------
  // Conditional Transition Tests
  // ------------------------------------------

  describe('Conditional Transition', () => {
    it.todo('hides transition when conversation is empty');

    it('shows transition when conversation has entries', () => {
      render(<BriefingModal {...defaultProps} initialStep={2} conversation={mockConversation} />);

      expect(screen.getByText(/Now get to work/)).toBeInTheDocument();
      expect(screen.getByText(/TRUST NOTHING UNSEEN/)).toBeInTheDocument();
    });

    it.todo('shows transition after player asks first question');
  });

  // ------------------------------------------
  // Edge Cases
  // ------------------------------------------

  describe('Edge Cases', () => {
    it('handles missing transition text when conversation present', () => {
      const briefingNoTransition = {
        ...mockBriefing,
        transition: '',
      };

      render(
        <BriefingModal {...defaultProps} initialStep={2} briefing={briefingNoTransition} conversation={mockConversation} />
      );

      // Should still render Start Investigation button
      expect(
        screen.getByRole('button', { name: 'Start Investigation' })
      ).toBeInTheDocument();
    });

    it('handles empty transition with no conversation', () => {
      const briefingNoTransition = {
        ...mockBriefing,
        transition: '',
      };

      render(
        <BriefingModal {...defaultProps} briefing={briefingNoTransition} conversation={[]} initialStep={2} />
      );

      // Should still render without errors
      expect(
        screen.getByRole('button', { name: 'Start Investigation' })
      ).toBeInTheDocument();
    });

    it('handles long conversation history', () => {
      const longConversation: BriefingConversation[] = Array.from(
        { length: 10 },
        (_, i) => ({
          question: `Question ${i + 1}`,
          answer: `Answer ${i + 1}`,
        })
      );

      render(
        <BriefingModal {...defaultProps} conversation={longConversation} initialStep={2} />
      );

      // Should render all conversations
      expect(screen.getByText('Question 1')).toBeInTheDocument();
      expect(screen.getByText('Question 10')).toBeInTheDocument();
    });

    it('handles special characters in content', () => {
      const briefingSpecialChars = {
        ...mockBriefing,
        dossier: {
          ...mockBriefing.dossier,
          synopsis: 'Test <script>alert("xss")</script> content',
        },
      };

      render(
        <BriefingModal {...defaultProps} briefing={briefingSpecialChars} />
      );

      // Should escape HTML
      expect(screen.getByText(/Test.*content/)).toBeInTheDocument();
    });
  });
});
