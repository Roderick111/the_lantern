/**
 * useMatthewChat Hook
 *
 * Manages Matthew Croft's LLM-powered spirit companion:
 * - Check for auto-comments after evidence discovery (30% chance)
 * - Handle direct chat ("Matthew, what do you think?")
 * - Returns matthew_ghost messages with timestamps for ordering
 * - Non-blocking async (errors don't break investigation)
 *
 * @module hooks/useMatthewChat
 * @since Phase 4.1
 */

import { useState, useCallback } from 'react';
import { checkMatthewAutoComment, sendMatthewChat } from '../api/client';
import type { Message } from '../types/investigation';

// ============================================
// Types
// ============================================

export interface MatthewMessage extends Extract<Message, { type: 'matthew_ghost' }> {
  /** Response mode (auto_helpful, auto_misleading, direct_chat_*) */
  mode: string;
  /** Current trust level (0-100) */
  trust_level: number;
  /** Timestamp for message ordering */
  timestamp: number;
}

export interface UseMatthewChatOptions {
  /** Case ID (defaults to case_001) */
  caseId?: string;
  /** Player ID (defaults to default) */
  playerId?: string;
}

export interface UseMatthewChatReturn {
  /** Check if Matthew wants to auto-comment after evidence discovery */
  checkAutoComment: (isCritical?: boolean) => Promise<MatthewMessage | null>;
  /** Send direct message to Matthew (always responds) */
  sendMessage: (message: string) => Promise<MatthewMessage>;
  /** Whether an LLM call is in progress */
  loading: boolean;
  /** Last Matthew message (for debugging/display) */
  lastMatthewMessage: MatthewMessage | null;
}

// ============================================
// Hook
// ============================================

export function useMatthewChat({
  caseId = 'case_001',
  playerId = 'default',
}: UseMatthewChatOptions = {}): UseMatthewChatReturn {
  const [loading, setLoading] = useState(false);
  const [lastMatthewMessage, setLastMatthewMessage] = useState<MatthewMessage | null>(null);

  const checkAutoComment = useCallback(
    async (isCritical = false): Promise<MatthewMessage | null> => {
      setLoading(true);

      try {
        const response = await checkMatthewAutoComment(caseId, playerId, isCritical);

        if (!response) {
          return null;
        }

        const tone = response.mode.includes('helpful') ? 'helpful' : 'misleading';

        const message: MatthewMessage = {
          type: 'matthew_ghost',
          text: response.text,
          tone,
          mode: response.mode,
          trust_level: response.trust_level,
          timestamp: Date.now(),
        };

        setLastMatthewMessage(message);
        return message;
      } catch (error) {
        console.error('Matthew auto-comment failed:', error);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [caseId, playerId]
  );

  const sendMessage = useCallback(
    async (message: string): Promise<MatthewMessage> => {
      setLoading(true);

      try {
        const response = await sendMatthewChat(caseId, playerId, message);

        const tone = response.mode.includes('helpful') ? 'helpful' : 'misleading';

        const matthewMessage: MatthewMessage = {
          type: 'matthew_ghost',
          text: response.text,
          tone,
          mode: response.mode,
          trust_level: response.trust_level,
          timestamp: Date.now(),
        };

        setLastMatthewMessage(matthewMessage);
        return matthewMessage;
      } catch (error) {
        console.error('Matthew chat error:', error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [caseId, playerId]
  );

  return {
    checkAutoComment,
    sendMessage,
    loading,
    lastMatthewMessage,
  };
}