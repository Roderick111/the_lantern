/**
 * BriefingModal Component Tests
 *
 * Tests for dossier-only briefing UI.
 *
 * @module components/__tests__/BriefingModal.test
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '../../test/render';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BriefingModal, type BriefingModalProps } from '../BriefingModal';
import { BriefingCompleteResponseSchema } from '../../api/schemas';
import type { BriefingContent } from '../../types/investigation';

const mockBriefing: BriefingContent = {
  case_id: 'case_001',
  dossier: {
    title: 'The Sealed Stacks',
    victim: 'Third-year student',
    location: 'Blackwood Collegiate Library, Sealed Stacks',
    time: 'Approximately 9:15pm last night',
    status: 'Found held in stillness near frost-covered window',
    synopsis: `VICTIM: Third-year student
LOCATION: Blackwood Collegiate Library, Sealed Stacks`,
  },
  teaching_questions: [],
  transition: 'Trust nothing unseen.',
  briefing_completed: false,
};

const defaultProps: BriefingModalProps = {
  briefing: mockBriefing,
  onComplete: vi.fn(),
  loading: false,
};

describe('BriefingModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders case dossier content', () => {
    render(<BriefingModal {...defaultProps} />);
    expect(screen.getByText(/VICTIM: Third-year student/)).toBeInTheDocument();
    expect(screen.getByText(/CASE DOSSIER: The Sealed Stacks/)).toBeInTheDocument();
    expect(screen.getByText('WHAT HAPPENED')).toBeInTheDocument();
    expect(screen.queryByText(/How to investigate/i)).not.toBeInTheDocument();
  });

  it('renders Start Investigation button', () => {
    render(<BriefingModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /START INVESTIGATION/i })).toBeInTheDocument();
  });

  it('calls onComplete when Start Investigation clicked', async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<BriefingModal {...defaultProps} onComplete={onComplete} />);

    await user.click(screen.getByRole('button', { name: /START INVESTIGATION/i }));
    expect(onComplete).toHaveBeenCalled();
  });

  it('shows loading label on button when loading', () => {
    render(<BriefingModal {...defaultProps} loading={true} />);
    expect(screen.getByRole('button', { name: /SAVING/i })).toBeInTheDocument();
  });

  it('displays error message when provided', () => {
    render(<BriefingModal {...defaultProps} error="Failed to load briefing" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Failed to load briefing');
  });

  it('calls onClose when close button clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<BriefingModal {...defaultProps} onClose={onClose} />);

    await user.click(screen.getByRole('button', { name: /Close Case Briefing/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it('schema accepts realistic backend response with updated_state', () => {
    const result = BriefingCompleteResponseSchema.safeParse({
      success: true,
      updated_state: { case_id: 'case_001', briefing_completed: true },
    });
    expect(result.success).toBe(true);
  });
});
