/**
 * useVerdictFlow Hook Tests
 *
 * Tests for the verdict flow state management including:
 * - Initial state
 * - Submission flow
 * - Success/error handling
 * - State transitions
 * - Reset functionality
 *
 * @module hooks/__tests__/useVerdictFlow.test
 * @since Phase 3
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useVerdictFlow } from '../useVerdictFlow';
import * as apiClient from '../../api/client';
import type { SubmitVerdictResponse, MentorFeedbackData } from '../../types/investigation';

// ============================================
// Mocks
// ============================================

vi.mock('../../api/client', () => ({
  submitVerdict: vi.fn(),
}));

const mockFeedback: MentorFeedbackData = {
  analysis: 'Your reasoning was analyzed.',
  fallacies_detected: [],
  score: 75,
  quality: 'good',
  critique: 'Some areas to improve.',
  praise: 'Good work overall.',
  hint: null,
};

const mockSuccessResponseCorrect: SubmitVerdictResponse = {
  correct: true,
  attempts_remaining: 9,
  case_solved: true,
  mentor_feedback: mockFeedback,
  confrontation: {
    dialogue: [
      { speaker: 'graves', text: 'Good work.' },
      { speaker: 'cassian', text: 'I confess.', tone: 'remorseful' },
    ],
    aftermath: 'Justice was served.',
  },
  reveal: null,
  wrong_suspect_response: null,
};

const mockSuccessResponseIncorrect: SubmitVerdictResponse = {
  correct: false,
  attempts_remaining: 8,
  case_solved: false,
  mentor_feedback: {
    ...mockFeedback,
    score: 40,
    quality: 'poor',
    fallacies_detected: [
      { name: 'Confirmation Bias', description: 'You ignored evidence.', example: '' },
    ],
  },
  confrontation: null,
  reveal: null,
  wrong_suspect_response: 'GRAVES: Wrong suspect!',
};

const mockMaxAttemptsResponse: SubmitVerdictResponse = {
  correct: false,
  attempts_remaining: 0,
  case_solved: true,
  mentor_feedback: mockFeedback,
  confrontation: {
    dialogue: [{ speaker: 'graves', text: 'Let me show you what happened.' }],
    aftermath: 'The truth was revealed.',
  },
  reveal: 'The actual culprit was Cassian.',
  wrong_suspect_response: null,
};

// ============================================
// Test Suite
// ============================================

describe('useVerdictFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ------------------------------------------
  // Initial State Tests
  // ------------------------------------------

  describe('Initial State', () => {
    it('has correct initial state', () => {
      const { result } = renderHook(() => useVerdictFlow());

      expect(result.current.state).toEqual({
        submitting: false,
        submitted: false,
        feedback: null,
        confrontation: null,
        reveal: null,
        wrongSuspectResponse: null,
        correct: false,
        attemptsRemaining: 10,
        caseSolved: false,
        confrontationConfirmed: false,
        error: null,
      });
    });

    it('returns submitVerdict function', () => {
      const { result } = renderHook(() => useVerdictFlow());
      expect(typeof result.current.submitVerdict).toBe('function');
    });

    it('returns reset function', () => {
      const { result } = renderHook(() => useVerdictFlow());
      expect(typeof result.current.reset).toBe('function');
    });

    it('returns clearError function', () => {
      const { result } = renderHook(() => useVerdictFlow());
      expect(typeof result.current.clearError).toBe('function');
    });
  });

  // ------------------------------------------
  // Submit Verdict Tests
  // ------------------------------------------

  describe('Submit Verdict', () => {
    it('sets submitting to true during submission', () => {
      vi.mocked(apiClient.submitVerdict).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockSuccessResponseCorrect), 100))
      );

      const { result } = renderHook(() => useVerdictFlow());

      act(() => {
        void result.current.submitVerdict('cassian', 'Test reasoning', ['evidence_1']);
      });

      expect(result.current.state.submitting).toBe(true);
    });

    it('calls API with correct parameters', async () => {
      vi.mocked(apiClient.submitVerdict).mockResolvedValue(mockSuccessResponseCorrect);

      const { result } = renderHook(() => useVerdictFlow({ caseId: 'case_001', playerId: 'test_player' }));

      await act(async () => {
        await result.current.submitVerdict('cassian', 'My reasoning', ['frost_pattern', 'focus_signature']);
      });

      expect(apiClient.submitVerdict).toHaveBeenCalledWith({
        case_id: 'case_001',
        player_id: 'test_player',
        accused_suspect_id: 'cassian',
        reasoning: 'My reasoning',
        evidence_cited: ['frost_pattern', 'focus_signature'],
      });
    });

    it('updates state on successful correct verdict', async () => {
      vi.mocked(apiClient.submitVerdict).mockResolvedValue(mockSuccessResponseCorrect);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('cassian', 'Test reasoning', []);
      });

      expect(result.current.state.submitting).toBe(false);
      expect(result.current.state.submitted).toBe(true);
      expect(result.current.state.correct).toBe(true);
      expect(result.current.state.caseSolved).toBe(true);
      expect(result.current.state.feedback).toEqual(mockSuccessResponseCorrect.mentor_feedback);
      expect(result.current.state.confrontation).toEqual(mockSuccessResponseCorrect.confrontation);
      expect(result.current.state.attemptsRemaining).toBe(9);
    });

    it('updates state on incorrect verdict', async () => {
      vi.mocked(apiClient.submitVerdict).mockResolvedValue(mockSuccessResponseIncorrect);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('elena', 'Wrong reasoning', []);
      });

      expect(result.current.state.submitted).toBe(true);
      expect(result.current.state.correct).toBe(false);
      expect(result.current.state.caseSolved).toBe(false);
      expect(result.current.state.confrontation).toBeNull();
      expect(result.current.state.wrongSuspectResponse).toBe('GRAVES: Wrong suspect!');
      expect(result.current.state.attemptsRemaining).toBe(8);
    });

    it('sets reveal on max attempts reached', async () => {
      vi.mocked(apiClient.submitVerdict).mockResolvedValue(mockMaxAttemptsResponse);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('elena', 'Final wrong guess', []);
      });

      expect(result.current.state.reveal).toBe('The actual culprit was Cassian.');
      expect(result.current.state.confrontation).not.toBeNull();
      expect(result.current.state.attemptsRemaining).toBe(0);
    });
  });

  // ------------------------------------------
  // Error Handling Tests
  // ------------------------------------------

  describe('Error Handling', () => {
    it('handles API error during submission', async () => {
      // ApiError has status and message properties
      const apiError = { status: 500, message: 'Network error' };
      vi.mocked(apiClient.submitVerdict).mockRejectedValue(apiError);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('cassian', 'Test', []);
      });

      expect(result.current.state.submitting).toBe(false);
      expect(result.current.state.error).toBe('Network error');
    });

    it('sets generic error message for unknown errors', async () => {
      vi.mocked(apiClient.submitVerdict).mockRejectedValue({});

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('cassian', 'Test', []);
      });

      expect(result.current.state.error).toBe('Failed to submit verdict');
    });

    it('preserves form data after API error', async () => {
      // ApiError with status and message
      const apiError = { status: 500, message: 'Server error' };
      vi.mocked(apiClient.submitVerdict).mockRejectedValueOnce(apiError);
      vi.mocked(apiClient.submitVerdict).mockResolvedValueOnce(mockSuccessResponseCorrect);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('cassian', 'Test', []);
      });

      expect(result.current.state.error).toBe('Server error');

      await act(async () => {
        await result.current.submitVerdict('cassian', 'Test', []);
      });

      expect(result.current.state.error).toBeNull();
    });
  });

  // ------------------------------------------
  // Reset Tests
  // ------------------------------------------

  describe('Reset', () => {
    it('resets state for retry', async () => {
      vi.mocked(apiClient.submitVerdict).mockResolvedValue(mockSuccessResponseIncorrect);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('elena', 'Wrong', []);
      });

      expect(result.current.state.submitted).toBe(true);

      act(() => {
        result.current.reset();
      });

      expect(result.current.state.submitted).toBe(false);
      expect(result.current.state.feedback).toBeNull();
      expect(result.current.state.wrongSuspectResponse).toBeNull();
    });

    it('preserves attempts remaining after reset', async () => {
      vi.mocked(apiClient.submitVerdict).mockResolvedValue(mockSuccessResponseIncorrect);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('elena', 'Wrong', []);
      });

      const attemptsAfterSubmit = result.current.state.attemptsRemaining;

      act(() => {
        result.current.reset();
      });

      expect(result.current.state.attemptsRemaining).toBe(attemptsAfterSubmit);
    });

    it('resets caseSolved to allow retry after correct verdict', async () => {
      vi.mocked(apiClient.submitVerdict).mockResolvedValue(mockSuccessResponseCorrect);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('cassian', 'Correct reasoning', []);
      });

      expect(result.current.state.caseSolved).toBe(true);

      act(() => {
        result.current.reset();
      });

      // caseSolved should reset to false to allow retry
      expect(result.current.state.caseSolved).toBe(false);
    });
  });

  // ------------------------------------------
  // Clear Error Tests
  // ------------------------------------------

  describe('Clear Error', () => {
    it('clears error state', async () => {
      // Use ApiError format (status + message) so isApiError returns true
      const apiError = { status: 400, message: 'Test error' };
      vi.mocked(apiClient.submitVerdict).mockRejectedValue(apiError);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('cassian', 'Test', []);
      });

      expect(result.current.state.error).toBe('Test error');

      act(() => {
        result.current.clearError();
      });

      expect(result.current.state.error).toBeNull();
    });
  });

  // ------------------------------------------
  // Options Tests
  // ------------------------------------------

  describe('Options', () => {
    it('uses default case_id if not provided', async () => {
      vi.mocked(apiClient.submitVerdict).mockResolvedValue(mockSuccessResponseCorrect);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('cassian', 'Test', []);
      });

      expect(apiClient.submitVerdict).toHaveBeenCalledWith(
        expect.objectContaining({ case_id: 'case_001' })
      );
    });

    it('uses default player_id if not provided', async () => {
      vi.mocked(apiClient.submitVerdict).mockResolvedValue(mockSuccessResponseCorrect);

      const { result } = renderHook(() => useVerdictFlow());

      await act(async () => {
        await result.current.submitVerdict('cassian', 'Test', []);
      });

      expect(apiClient.submitVerdict).toHaveBeenCalledWith(
        expect.objectContaining({ player_id: 'default' })
      );
    });

    it('uses custom case_id when provided', async () => {
      vi.mocked(apiClient.submitVerdict).mockResolvedValue(mockSuccessResponseCorrect);

      const { result } = renderHook(() => useVerdictFlow({ caseId: 'case_002' }));

      await act(async () => {
        await result.current.submitVerdict('cassian', 'Test', []);
      });

      expect(apiClient.submitVerdict).toHaveBeenCalledWith(
        expect.objectContaining({ case_id: 'case_002' })
      );
    });
  });
});
