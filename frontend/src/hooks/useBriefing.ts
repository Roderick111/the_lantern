/**
 * useBriefing Hook
 *
 * Manages briefing state and API interactions:
 * - Load briefing content from backend
 * - Ask Graves questions (LLM dialogue)
 * - Track conversation history
 * - Handle teaching question choice selection
 * - Mark briefing as complete
 *
 * @module hooks/useBriefing
 * @since Phase 3.5 (updated Phase 3.6)
 */

import { useState, useCallback } from 'react';
import {
  getBriefing as getBriefingAPI,
  askBriefingQuestion as askBriefingQuestionAPI,
  markBriefingComplete as markBriefingCompleteAPI,
} from '../api/client';
import type {
  BriefingContent,
  BriefingConversation,
} from '../types/investigation';
import { isApiError } from '../types/investigation';

// ============================================
// Types
// ============================================

export interface UseBriefingOptions {
  /** Case ID (defaults to case_001) */
  caseId?: string;
  /** Player ID (defaults to default) */
  playerId?: string;
}

export interface UseBriefingReturn {
  /** Briefing content loaded from backend */
  briefing: BriefingContent | null;
  /** Q&A conversation history */
  conversation: BriefingConversation[];
  /** Selected choice ID (null if not yet answered) */
  selectedChoice: string | null;
  /** Graves's response to selected choice */
  choiceResponse: string | null;
  /** Whether an API call is in progress */
  loading: boolean;
  /** Error message if operation failed */
  error: string | null;
  /** Whether the briefing has been completed */
  completed: boolean;
  /** Load briefing content from backend */
  loadBriefing: () => Promise<BriefingContent | null>;
  /** Select a teaching question choice */
  selectChoice: (choiceId: string, questionIndex: number) => void;
  /** Reset choice selection state */
  resetChoice: () => void;
  /** Ask Graves a question */
  askQuestion: (question: string) => Promise<void>;
  /** Mark briefing as complete */
  markComplete: () => Promise<void>;
  /** Clear error state */
  clearError: () => void;
}

// ============================================
// Hook
// ============================================

export function useBriefing({
  caseId = 'case_001',
  playerId = 'default',
}: UseBriefingOptions = {}): UseBriefingReturn {
  // State
  const [briefing, setBriefing] = useState<BriefingContent | null>(null);
  const [conversation, setConversation] = useState<BriefingConversation[]>([]);
  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);
  const [choiceResponse, setChoiceResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Use backend-persisted completion state (defaults to false until loaded)
  const [completed, setCompleted] = useState(false);

  // Load briefing content (includes backend completion state)
  const loadBriefing = useCallback(async (): Promise<BriefingContent | null> => {
    setLoading(true);
    setError(null);

    try {
      const content = await getBriefingAPI(caseId, playerId);
      setBriefing(content);
      // Sync local state with backend-persisted completion status
      if (content.briefing_completed) {
        setCompleted(true);
      }
      return content;
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to load briefing');
      return null;
    } finally {
      setLoading(false);
    }
  }, [caseId, playerId]);

  // Select a teaching question choice
  const selectChoice = useCallback(
    (choiceId: string, questionIndex: number) => {
      if (!briefing) return;

      const question = briefing.teaching_questions[questionIndex];
      if (!question) return;

      const choice = question.choices.find((c) => c.id === choiceId);
      if (choice) {
        setSelectedChoice(choiceId);
        setChoiceResponse(choice.response);
      }
    },
    [briefing]
  );

  // Reset selected choice (for moving between questions)
  const resetChoice = useCallback(() => {
    setSelectedChoice(null);
    setChoiceResponse(null);
  }, []);

  // Ask Graves a question
  const askQuestion = useCallback(
    async (question: string): Promise<void> => {
      if (!question.trim()) {
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await askBriefingQuestionAPI(caseId, question, playerId);

        // Add to conversation history
        setConversation((prev) => [...prev, { question, answer: response.answer }]);
      } catch (err) {
        setError(isApiError(err) ? err.message : 'Failed to get response from Graves');
      } finally {
        setLoading(false);
      }
    },
    [caseId, playerId]
  );

  // Mark briefing as complete
  const markComplete = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const response = await markBriefingCompleteAPI(caseId, playerId);
      if (response.success) {
        setCompleted(true);
      }
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to complete briefing');
    } finally {
      setLoading(false);
    }
  }, [caseId, playerId]);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    briefing,
    conversation,
    selectedChoice,
    choiceResponse,
    loading,
    error,
    completed,
    loadBriefing,
    selectChoice,
    resetChoice,
    askQuestion,
    markComplete,
    clearError,
  };
}
