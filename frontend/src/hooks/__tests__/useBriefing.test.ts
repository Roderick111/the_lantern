/**
 * useBriefing Hook Tests
 *
 * Tests for the briefing state management hook:
 * - Load briefing content
 * - Ask questions and track conversation
 * - Mark briefing complete
 * - Error handling
 *
 * @module hooks/__tests__/useBriefing.test
 * @since Phase 3.5
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useBriefing } from '../useBriefing';
import * as client from '../../api/client';
import type { BriefingContent } from '../../types/investigation';

// ============================================
// Mocks
// ============================================

vi.mock('../../api/client');

const mockBriefing: BriefingContent = {
  case_id: 'case_001',
  dossier: {
    title: 'The Sealed Archive',
    victim: 'Third-year student',
    location: 'Library',
    time: '9:15pm',
    status: 'Held in stillness',
    synopsis: 'VICTIM: Third-year student\nLOCATION: Library',
  },
  teaching_questions: [
    {
      prompt: 'How many school incidents are actually accidents?',
      choices: [
        { id: '25_percent', text: '25%', response: 'Too low.' },
        { id: '50_percent', text: '50%', response: 'Not quite.' },
        { id: '85_percent', text: '85%', response: '*nods* Correct.' },
        { id: 'almost_all', text: 'Almost all', response: 'Overcorrecting.' },
      ],
      concept_summary: "That's base rates, recruit.",
    },
  ],
  transition: 'Now get to work. TRUST NOTHING UNSEEN.',
  briefing_completed: false,
};

// ============================================
// Test Suite
// ============================================

describe('useBriefing', () => {
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
    it('starts with null briefing', () => {
      const { result } = renderHook(() => useBriefing());

      expect(result.current.briefing).toBeNull();
    });

    it('starts with empty conversation', () => {
      const { result } = renderHook(() => useBriefing());

      expect(result.current.conversation).toEqual([]);
    });

    it('starts not loading', () => {
      const { result } = renderHook(() => useBriefing());

      expect(result.current.loading).toBe(false);
    });

    it('starts with no error', () => {
      const { result } = renderHook(() => useBriefing());

      expect(result.current.error).toBeNull();
    });

    it('starts not completed', () => {
      const { result } = renderHook(() => useBriefing());

      expect(result.current.completed).toBe(false);
    });

    it('starts with null selectedChoice', () => {
      const { result } = renderHook(() => useBriefing());

      expect(result.current.selectedChoice).toBeNull();
    });

    it('starts with null choiceResponse', () => {
      const { result } = renderHook(() => useBriefing());

      expect(result.current.choiceResponse).toBeNull();
    });
  });

  // ------------------------------------------
  // Load Briefing Tests
  // ------------------------------------------

  describe('loadBriefing', () => {
    it('loads briefing content successfully', async () => {
      vi.mocked(client.getBriefing).mockResolvedValue(mockBriefing);

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.loadBriefing();
      });

      expect(result.current.briefing).toEqual(mockBriefing);
    });

    it('sets loading state during API call', async () => {
      let resolvePromise: (value: BriefingContent) => void;
      const promise = new Promise<BriefingContent>((resolve) => {
        resolvePromise = resolve;
      });
      vi.mocked(client.getBriefing).mockReturnValue(promise);

      const { result } = renderHook(() => useBriefing());

      act(() => {
        void result.current.loadBriefing();
      });

      expect(result.current.loading).toBe(true);

      await act(async () => {
        resolvePromise!(mockBriefing);
        await promise;
      });

      expect(result.current.loading).toBe(false);
    });

    it('handles API error', async () => {
      vi.mocked(client.getBriefing).mockRejectedValue({
        message: 'Failed to load briefing',
        status: 500,
      });

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.loadBriefing();
      });

      expect(result.current.error).toBe('Failed to load briefing');
      expect(result.current.briefing).toBeNull();
    });

    it('returns loaded content', async () => {
      vi.mocked(client.getBriefing).mockResolvedValue(mockBriefing);

      const { result } = renderHook(() => useBriefing());

      let returnedContent: BriefingContent | null = null;
      await act(async () => {
        returnedContent = await result.current.loadBriefing();
      });

      expect(returnedContent).toEqual(mockBriefing);
    });

    it('returns null on error', async () => {
      vi.mocked(client.getBriefing).mockRejectedValue({
        message: 'Network error',
        status: 500,
      });

      const { result } = renderHook(() => useBriefing());

      let returnedContent: BriefingContent | null = mockBriefing;
      await act(async () => {
        returnedContent = await result.current.loadBriefing();
      });

      expect(returnedContent).toBeNull();
    });

    it('uses custom caseId', async () => {
      vi.mocked(client.getBriefing).mockResolvedValue(mockBriefing);

      const { result } = renderHook(() =>
        useBriefing({ caseId: 'case_002' })
      );

      await act(async () => {
        await result.current.loadBriefing();
      });

      expect(client.getBriefing).toHaveBeenCalledWith('case_002');
    });
  });

  // ------------------------------------------
  // Ask Question Tests
  // ------------------------------------------

  describe('askQuestion', () => {
    it('asks question and gets answer', async () => {
      vi.mocked(client.askBriefingQuestion).mockResolvedValue({
        answer: 'Base rates are prior probabilities.',
      });

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.askQuestion('What are base rates?');
      });

      expect(result.current.conversation).toHaveLength(1);
      expect(result.current.conversation[0]).toEqual({
        question: 'What are base rates?',
        answer: 'Base rates are prior probabilities.',
      });
    });

    it('accumulates conversation history', async () => {
      vi.mocked(client.askBriefingQuestion)
        .mockResolvedValueOnce({ answer: 'Answer 1' })
        .mockResolvedValueOnce({ answer: 'Answer 2' });

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.askQuestion('Question 1');
      });

      await act(async () => {
        await result.current.askQuestion('Question 2');
      });

      expect(result.current.conversation).toHaveLength(2);
      expect(result.current.conversation[0].question).toBe('Question 1');
      expect(result.current.conversation[1].question).toBe('Question 2');
    });

    it('ignores empty questions', async () => {
      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.askQuestion('');
      });

      expect(client.askBriefingQuestion).not.toHaveBeenCalled();
      expect(result.current.conversation).toHaveLength(0);
    });

    it('ignores whitespace-only questions', async () => {
      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.askQuestion('   ');
      });

      expect(client.askBriefingQuestion).not.toHaveBeenCalled();
    });

    it('sets loading state during API call', async () => {
      let resolvePromise: (value: { answer: string }) => void;
      const promise = new Promise<{ answer: string }>((resolve) => {
        resolvePromise = resolve;
      });
      vi.mocked(client.askBriefingQuestion).mockReturnValue(promise);

      const { result } = renderHook(() => useBriefing());

      act(() => {
        void result.current.askQuestion('Test?');
      });

      expect(result.current.loading).toBe(true);

      await act(async () => {
        resolvePromise!({ answer: 'Test answer' });
        await promise;
      });

      expect(result.current.loading).toBe(false);
    });

    it('handles API error', async () => {
      vi.mocked(client.askBriefingQuestion).mockRejectedValue({
        message: 'LLM service unavailable',
        status: 503,
      });

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.askQuestion('What are base rates?');
      });

      expect(result.current.error).toBe('LLM service unavailable');
      expect(result.current.conversation).toHaveLength(0);
    });

    it('uses custom caseId', async () => {
      vi.mocked(client.askBriefingQuestion).mockResolvedValue({
        answer: 'Answer',
      });

      const { result } = renderHook(() =>
        useBriefing({ caseId: 'case_002' })
      );

      await act(async () => {
        await result.current.askQuestion('Test?');
      });

      expect(client.askBriefingQuestion).toHaveBeenCalledWith('case_002', 'Test?');
    });
  });

  // ------------------------------------------
  // Mark Complete Tests
  // ------------------------------------------

  describe('markComplete', () => {
    it('marks briefing complete successfully', async () => {
      vi.mocked(client.markBriefingComplete).mockResolvedValue({
        success: true,
      });

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.markComplete();
      });

      expect(result.current.completed).toBe(true);
    });

    it('does not mark complete on API failure', async () => {
      vi.mocked(client.markBriefingComplete).mockResolvedValue({
        success: false,
      });

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.markComplete();
      });

      expect(result.current.completed).toBe(false);
    });

    it('handles API error', async () => {
      vi.mocked(client.markBriefingComplete).mockRejectedValue({
        message: 'Failed to complete briefing',
        status: 500,
      });

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.markComplete();
      });

      expect(result.current.error).toBe('Failed to complete briefing');
      expect(result.current.completed).toBe(false);
    });

    it('sets loading state during API call', async () => {
      let resolvePromise: (value: { success: boolean }) => void;
      const promise = new Promise<{ success: boolean }>((resolve) => {
        resolvePromise = resolve;
      });
      vi.mocked(client.markBriefingComplete).mockReturnValue(promise);

      const { result } = renderHook(() => useBriefing());

      act(() => {
        void result.current.markComplete();
      });

      expect(result.current.loading).toBe(true);

      await act(async () => {
        resolvePromise!({ success: true });
        await promise;
      });

      expect(result.current.loading).toBe(false);
    });

    it('uses custom caseId', async () => {
      vi.mocked(client.markBriefingComplete).mockResolvedValue({
        success: true,
      });

      const { result } = renderHook(() =>
        useBriefing({ caseId: 'case_002' })
      );

      await act(async () => {
        await result.current.markComplete();
      });

      expect(client.markBriefingComplete).toHaveBeenCalledWith('case_002');
    });
  });

  // ------------------------------------------
  // Select Choice Tests
  // ------------------------------------------

  describe('selectChoice', () => {
    it('sets selectedChoice and choiceResponse', async () => {
      vi.mocked(client.getBriefing).mockResolvedValue(mockBriefing);

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.loadBriefing();
      });

      act(() => {
        result.current.selectChoice('85_percent', 0);
      });

      expect(result.current.selectedChoice).toBe('85_percent');
      expect(result.current.choiceResponse).toBe('*nods* Correct.');
    });

    it('does nothing if briefing not loaded', () => {
      const { result } = renderHook(() => useBriefing());

      act(() => {
        result.current.selectChoice('85_percent', 0);
      });

      expect(result.current.selectedChoice).toBeNull();
      expect(result.current.choiceResponse).toBeNull();
    });

    it('does nothing if choice ID not found', async () => {
      vi.mocked(client.getBriefing).mockResolvedValue(mockBriefing);

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.loadBriefing();
      });

      act(() => {
        result.current.selectChoice('invalid_choice', 0);
      });

      expect(result.current.selectedChoice).toBeNull();
      expect(result.current.choiceResponse).toBeNull();
    });

    it('allows changing choice selection', async () => {
      vi.mocked(client.getBriefing).mockResolvedValue(mockBriefing);

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.loadBriefing();
      });

      act(() => {
        result.current.selectChoice('25_percent', 0);
      });

      expect(result.current.selectedChoice).toBe('25_percent');
      expect(result.current.choiceResponse).toBe('Too low.');

      act(() => {
        result.current.selectChoice('85_percent', 0);
      });

      expect(result.current.selectedChoice).toBe('85_percent');
      expect(result.current.choiceResponse).toBe('*nods* Correct.');
    });
  });

  // ------------------------------------------
  // Clear Error Tests
  // ------------------------------------------

  describe('clearError', () => {
    it('clears error state', async () => {
      vi.mocked(client.getBriefing).mockRejectedValue({
        message: 'Network error',
        status: 500,
      });

      const { result } = renderHook(() => useBriefing());

      await act(async () => {
        await result.current.loadBriefing();
      });

      expect(result.current.error).toBe('Network error');

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });
});
