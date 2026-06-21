/**
 * useWitnessInterrogation Hook
 *
 * Manages witness interrogation state including:
 * - Current witness selection
 * - Conversation history
 * - Trust level tracking
 * - Evidence presentation
 * - Secret revelation tracking
 *
 * @module hooks/useWitnessInterrogation
 * @since Phase 2
 */

import { useReducer, useCallback, useEffect, useRef } from 'react';
import {
  interrogateStream,
  presentEvidenceStream,
  getWitnesses,
  getWitness,
  isApiError,
} from '../api/client';
import type {
  WitnessInfo,
  WitnessConversationItem,
} from '../types/investigation';

/**
 * Strip [TRUST_DELTA: N] tags from witness responses.
 * LLMs may abbreviate the tag (e.g., "TA: -12]", "TRUST_DELTA: 5]", "[TRUST_DELTA: -3]"),
 * so we match broadly: any bracket-like pattern ending with a number and ']'.
 * Used at render time (not in reducer) to preserve raw buffer for correct partial-tag detection.
 */
// Colon optional — LLMs sometimes output [TRUST_DELTA +4] or [TRUST_DELTA4]
const TRUST_TAG_RE = /\s*\[?TRUST_DELTA:?\s*[+-]?\d+\s*\]/gi;
const TRUST_TAG_ABBREV_RE = /\s*\[?T(?:RUST_?)?(?:D(?:ELTA)?)?(?:A)?:?\s*[+-]?\d+\s*\]/gi;
const TRUST_TAG_PARTIAL_RE = /\s*\[T(?:R(?:U(?:S(?:T(?:_(?:D(?:E(?:L(?:T(?:A)?)?)?)?)?)?)?)?)?)?:?\s*[^\]]*$/i;
export function stripTrustTags(text: string): string {
  return text
    .replace(TRUST_TAG_RE, '')
    .replace(TRUST_TAG_ABBREV_RE, '')
    .replace(TRUST_TAG_PARTIAL_RE, '')
    .trimEnd();
}

// ============================================
// Types
// ============================================

interface WitnessInterrogationState {
  /** List of available witnesses */
  witnesses: WitnessInfo[];
  /** Currently selected witness */
  currentWitness: WitnessInfo | null;
  /** Local conversation history (display purposes) */
  conversation: WitnessConversationItem[];
  /** Current trust level */
  trust: number;
  /** Loading state */
  loading: boolean;
  /** Error message */
  error: string | null;
  /** Secrets revealed in current session */
  secretsRevealed: string[];
}

type WitnessAction =
  | { type: 'SET_WITNESSES'; payload: WitnessInfo[] }
  | { type: 'SELECT_WITNESS'; payload: WitnessInfo }
  | { type: 'ADD_CONVERSATION'; payload: WitnessConversationItem }
  | { type: 'APPEND_LAST_RESPONSE'; payload: string }
  | { type: 'UPDATE_TRUST'; payload: number }
  | { type: 'UPDATE_LAST_TRUST_DELTA'; payload: number }
  | { type: 'REVEAL_SECRETS'; payload: string[] }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'CLEAR_CONVERSATION' }
  | { type: 'RESET' };

interface UseWitnessInterrogationOptions {
  /** Case ID */
  caseId?: string;
  /** Player ID */
  playerId?: string;
  /** Auto-load witnesses on mount */
  autoLoad?: boolean;
}

interface UseWitnessInterrogationReturn {
  /** Current state */
  state: WitnessInterrogationState;
  /** Ask a question to the current witness */
  askQuestion: (question: string) => Promise<void>;
  /** Present evidence to the current witness */
  presentEvidenceToWitness: (evidenceId: string, evidenceName: string) => Promise<void>;
  /** Select a witness for interrogation */
  selectWitness: (witnessId: string) => Promise<void>;
  /** Clear current conversation */
  clearConversation: () => void;
  /** Reload witnesses list */
  reloadWitnesses: () => Promise<void>;
}

// ============================================
// Reducer
// ============================================

const initialState: WitnessInterrogationState = {
  witnesses: [],
  currentWitness: null,
  conversation: [],
  trust: 50,
  loading: false,
  error: null,
  secretsRevealed: [],
};

function witnessReducer(
  state: WitnessInterrogationState,
  action: WitnessAction
): WitnessInterrogationState {
  switch (action.type) {
    case 'SET_WITNESSES':
      return { ...state, witnesses: action.payload };

    case 'SELECT_WITNESS':
      return {
        ...state,
        currentWitness: action.payload,
        trust: action.payload.trust,
        conversation: [...(action.payload.conversation_history ?? [])],
        secretsRevealed: [...(action.payload.secrets_revealed ?? [])],
        error: null,
      };

    case 'ADD_CONVERSATION':
      return {
        ...state,
        conversation: [...state.conversation, action.payload],
      };

    case 'APPEND_LAST_RESPONSE': {
      const conv = [...state.conversation];
      if (conv.length > 0) {
        const last = conv[conv.length - 1];
        conv[conv.length - 1] = { ...last, response: last.response + action.payload };
      }
      return { ...state, conversation: conv };
    }

    case 'UPDATE_LAST_TRUST_DELTA': {
      const convDelta = [...state.conversation];
      if (convDelta.length > 0) {
        const lastItem = convDelta[convDelta.length - 1];
        convDelta[convDelta.length - 1] = { ...lastItem, trust_delta: action.payload };
      }
      return { ...state, conversation: convDelta };
    }

    case 'UPDATE_TRUST':
      // Update trust in current state AND in witnesses array for sidebar sync
      return {
        ...state,
        trust: action.payload,
        currentWitness: state.currentWitness
          ? { ...state.currentWitness, trust: action.payload }
          : null,
        witnesses: state.witnesses.map((w) =>
          w.id === state.currentWitness?.id ? { ...w, trust: action.payload } : w
        ),
      };

    case 'REVEAL_SECRETS': {
      const newSecretsRevealed = [...new Set([...state.secretsRevealed, ...action.payload])];
      return {
        ...state,
        secretsRevealed: newSecretsRevealed,
        currentWitness: state.currentWitness
          ? { ...state.currentWitness, secrets_revealed: newSecretsRevealed }
          : null,
        witnesses: state.witnesses.map((w) =>
          w.id === state.currentWitness?.id
            ? { ...w, secrets_revealed: newSecretsRevealed }
            : w
        ),
      };
    }

    case 'SET_LOADING':
      return { ...state, loading: action.payload };

    case 'SET_ERROR':
      return { ...state, error: action.payload };

    case 'CLEAR_CONVERSATION':
      return { ...state, conversation: [] };

    case 'RESET':
      return initialState;

    default:
      return state;
  }
}

// ============================================
// Hook
// ============================================

export function useWitnessInterrogation({
  caseId = 'case_001',
  autoLoad = true,
}: UseWitnessInterrogationOptions = {}): UseWitnessInterrogationReturn {
  const [state, dispatch] = useReducer(witnessReducer, initialState);

  // AbortController for in-flight interrogate / present-evidence stream.
  // Aborted when the user changes witness or unmounts so abandoned streams
  // don't keep burning LLM tokens.
  const streamControllerRef = useRef<AbortController | null>(null);

  // Abort any in-flight stream when component unmounts.
  useEffect(() => {
    return () => {
      streamControllerRef.current?.abort();
      streamControllerRef.current = null;
    };
  }, []);

  // Load witnesses list
  const reloadWitnesses = useCallback(async () => {
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    try {
      const witnesses = await getWitnesses(caseId);
      dispatch({ type: 'SET_WITNESSES', payload: witnesses });
    } catch (err) {
      dispatch({
        type: 'SET_ERROR',
        payload: isApiError(err) ? err.message : 'Failed to load witnesses',
      });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [caseId]);

  // Auto-load on mount
  useEffect(() => {
    if (autoLoad) {
      void reloadWitnesses();
    }
  }, [autoLoad, reloadWitnesses]);

  // Select witness for interrogation
  const selectWitness = useCallback(
    async (witnessId: string) => {
      // Switching witness = abandon any in-flight stream for the previous one.
      streamControllerRef.current?.abort();
      streamControllerRef.current = null;

      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'SET_ERROR', payload: null });

      try {
        const witness = await getWitness(witnessId, caseId);
        dispatch({ type: 'SELECT_WITNESS', payload: witness });
      } catch (err) {
        dispatch({
          type: 'SET_ERROR',
          payload: isApiError(err) ? err.message : 'Failed to load witness',
        });
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    },
    [caseId]
  );

  // Ask question to current witness
  const askQuestion = useCallback(
    async (question: string) => {
      if (!state.currentWitness) {
        dispatch({ type: 'SET_ERROR', payload: 'No witness selected' });
        return;
      }

      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'SET_ERROR', payload: null });

      // Add placeholder conversation item for streaming
      const placeholderItem: WitnessConversationItem = {
        question,
        response: '',
        timestamp: new Date().toISOString(),
        trust_delta: 0,
      };
      dispatch({ type: 'ADD_CONVERSATION', payload: placeholderItem });

      // Cancel any in-flight stream then start fresh.
      streamControllerRef.current?.abort();
      const controller = new AbortController();
      streamControllerRef.current = controller;

      try {
        await interrogateStream(
          {
            witness_id: state.currentWitness.id,
            question,
            case_id: caseId,
            slot: 'autosave',
          },
          {
            onChunk: (text) => {
              dispatch({ type: 'APPEND_LAST_RESPONSE', payload: text });
            },
            onDone: (data) => {
              const trust = data.trust as number | undefined;
              if (trust !== undefined) {
                dispatch({ type: 'UPDATE_TRUST', payload: trust });
              }
              const trustDelta = data.trust_delta as number | undefined;
              if (trustDelta !== undefined) {
                dispatch({ type: 'UPDATE_LAST_TRUST_DELTA', payload: trustDelta });
              }
              const secrets = data.secrets_revealed as string[] | undefined;
              if (secrets && secrets.length > 0) {
                dispatch({ type: 'REVEAL_SECRETS', payload: secrets });
              }
              if (import.meta.env.DEV) {
                const meta = data.meta as { model?: string; latency_ms?: number } | undefined;
                if (meta) {
                  console.log(`%c[${meta.model ?? '?'}] · ${meta.latency_ms ?? '?'}ms`, 'color: #6b7280; font-size: 11px');
                }
              }
              dispatch({ type: 'SET_LOADING', payload: false });
            },
            onError: (errMsg) => {
              dispatch({ type: 'SET_ERROR', payload: errMsg });
              dispatch({ type: 'SET_LOADING', payload: false });
            },
          },
          controller.signal,
        );
      } catch (err) {
        if (controller.signal.aborted) return;
        dispatch({
          type: 'SET_ERROR',
          payload: isApiError(err) ? err.message : 'Failed to interrogate witness',
        });
        dispatch({ type: 'SET_LOADING', payload: false });
      } finally {
        if (streamControllerRef.current === controller) {
          streamControllerRef.current = null;
        }
      }
    },
    [state.currentWitness, caseId]
  );

  // Present evidence to current witness (streaming)
  const presentEvidenceToWitness = useCallback(
    async (evidenceId: string, evidenceName: string) => {
      if (!state.currentWitness) {
        dispatch({ type: 'SET_ERROR', payload: 'No witness selected' });
        return;
      }

      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'SET_ERROR', payload: null });

      // Show player message immediately
      const placeholderItem: WitnessConversationItem = {
        question: `What do you know about ${evidenceName}?`,
        response: '',
        timestamp: new Date().toISOString(),
        trust_delta: 0,
      };
      dispatch({ type: 'ADD_CONVERSATION', payload: placeholderItem });

      // Cancel any in-flight stream then start fresh.
      streamControllerRef.current?.abort();
      const controller = new AbortController();
      streamControllerRef.current = controller;

      try {
        await presentEvidenceStream(
          {
            witness_id: state.currentWitness.id,
            evidence_id: evidenceId,
            case_id: caseId,
            slot: 'autosave',
          },
          {
            onChunk: (text) => {
              dispatch({ type: 'APPEND_LAST_RESPONSE', payload: text });
            },
            onDone: (data) => {
              const trust = data.trust as number | undefined;
              if (trust !== undefined) {
                dispatch({ type: 'UPDATE_TRUST', payload: trust });
              }
              const trustDelta = data.trust_delta as number | undefined;
              if (trustDelta !== undefined) {
                dispatch({ type: 'UPDATE_LAST_TRUST_DELTA', payload: trustDelta });
              }
              const secrets = data.secrets_revealed as string[] | undefined;
              if (secrets && secrets.length > 0) {
                dispatch({ type: 'REVEAL_SECRETS', payload: secrets });
              }
              if (import.meta.env.DEV) {
                const meta = data.meta as { model?: string; latency_ms?: number } | undefined;
                if (meta) {
                  console.log(`%c[${meta.model ?? '?'}] · ${meta.latency_ms ?? '?'}ms`, 'color: #6b7280; font-size: 11px');
                }
              }
              dispatch({ type: 'SET_LOADING', payload: false });
            },
            onError: (errMsg) => {
              dispatch({ type: 'SET_ERROR', payload: errMsg });
              dispatch({ type: 'SET_LOADING', payload: false });
            },
          },
          controller.signal,
        );
      } catch (err) {
        if (controller.signal.aborted) return;
        dispatch({
          type: 'SET_ERROR',
          payload: isApiError(err) ? err.message : 'Failed to present evidence',
        });
        dispatch({ type: 'SET_LOADING', payload: false });
      } finally {
        if (streamControllerRef.current === controller) {
          streamControllerRef.current = null;
        }
      }
    },
    [state.currentWitness, caseId]
  );

  // Clear conversation
  const clearConversation = useCallback(() => {
    dispatch({ type: 'CLEAR_CONVERSATION' });
  }, []);

  return {
    state,
    askQuestion,
    presentEvidenceToWitness,
    selectWitness,
    clearConversation,
    reloadWitnesses,
  };
}
