 
/**
 * useWitnessInterrogation Hook Tests
 *
 * Tests for witness interrogation state management including:
 * - Loading witnesses
 * - Selecting witness
 * - Asking questions (streaming)
 * - Presenting evidence
 * - Trust tracking
 * - Secret revelation
 *
 * @module hooks/__tests__/useWitnessInterrogation.test
 * @since Phase 2
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWitnessInterrogation } from '../useWitnessInterrogation';
import * as api from '../../api/client';
import type { WitnessInfo, PresentEvidenceResponse } from '../../types/investigation';
import type { StreamCallbacks } from '../../api/client';

// ============================================
// Mocks
// ============================================

vi.mock('../../api/client', () => ({
  getWitnesses: vi.fn(),
  getWitness: vi.fn(),
  interrogateStream: vi.fn(),
  presentEvidence: vi.fn(),
  presentEvidenceStream: vi.fn(),
  isApiError: vi.fn(() => false),
}));

// ============================================
// Test Data
// ============================================

const mockWitnesses: WitnessInfo[] = [
  {
    id: 'elena',
    name: 'Elena Marsh',
    trust: 50,
    secrets_revealed: [],
  },
  {
    id: 'cassian',
    name: 'Cassian Thorne',
    trust: 30,
    secrets_revealed: ['secret_1'],
  },
];

const mockWitnessDetail: WitnessInfo = {
  id: 'elena',
  name: 'Elena Marsh',
  personality: 'helpful',
  trust: 55,
  conversation_history: [
    {
      question: 'What happened?',
      response: 'I saw something strange.',
      timestamp: '2026-01-05T12:00:00Z',
      trust_delta: 5,
    },
  ],
  secrets_revealed: [],
};

const mockPresentEvidenceResponse: PresentEvidenceResponse = {
  response: 'Where did you find that note?!',
  trust: 65,
  trust_delta: 5,
  secrets_revealed: ['secret_elena_1'],
};

// ============================================
// Test Suite
// ============================================

describe('useWitnessInterrogation', () => {
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
    it('returns initial state with empty witnesses', () => {
      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: false })
      );

      expect(result.current.state.witnesses).toEqual([]);
      expect(result.current.state.currentWitness).toBeNull();
      expect(result.current.state.conversation).toEqual([]);
      expect(result.current.state.trust).toBe(50);
      expect(result.current.state.loading).toBe(false);
      expect(result.current.state.error).toBeNull();
    });

    it('auto-loads witnesses on mount when autoLoad is true', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValue(mockWitnesses);

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      await waitFor(() => {
        expect(result.current.state.loading).toBe(false);
      }, { timeout: 2000 });

      expect(result.current.state.witnesses).toEqual(mockWitnesses);
      expect(api.getWitnesses).toHaveBeenCalledWith('case_001', 'default');
    });
  });

  // ------------------------------------------
  // Loading Witnesses Tests
  // ------------------------------------------

  describe('Loading Witnesses', () => {
    it('sets loading state while fetching witnesses', async () => {
      let resolvePromise: (value: WitnessInfo[]) => void;
      const promise = new Promise<WitnessInfo[]>((resolve) => {
        resolvePromise = resolve;
      });
      vi.mocked(api.getWitnesses).mockReturnValueOnce(promise);

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      expect(result.current.state.loading).toBe(true);

      act(() => {
        resolvePromise!(mockWitnesses);
      });

      await waitFor(() => {
        expect(result.current.state.loading).toBe(false);
      });
    });

    it('sets error when loading witnesses fails', async () => {
      vi.mocked(api.getWitnesses).mockRejectedValue({
        message: 'Failed to load witnesses',
      });

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      await waitFor(() => {
        expect(result.current.state.error).toBe('Failed to load witnesses');
      }, { timeout: 2000 });
    });

    it('reloads witnesses when reloadWitnesses is called', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValue(mockWitnesses);

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: false })
      );

      await act(async () => {
        await result.current.reloadWitnesses();
      });

      await waitFor(() => {
        expect(result.current.state.witnesses).toEqual(mockWitnesses);
      }, { timeout: 2000 });
    });
  });

  // ------------------------------------------
  // Selecting Witness Tests
  // ------------------------------------------

  describe('Selecting Witness', () => {
    it('loads witness details when selectWitness is called', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValueOnce(mockWitnesses);
      vi.mocked(api.getWitness).mockResolvedValueOnce(mockWitnessDetail);

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      await waitFor(() => {
        expect(result.current.state.witnesses.length).toBe(2);
      });

      await act(async () => {
        await result.current.selectWitness('elena');
      });

      expect(result.current.state.currentWitness).toEqual(mockWitnessDetail);
      expect(result.current.state.trust).toBe(55);
      expect(result.current.state.conversation).toEqual(mockWitnessDetail.conversation_history);
    });

    it('sets error when selecting witness fails', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValueOnce(mockWitnesses);
      vi.mocked(api.getWitness).mockRejectedValueOnce({
        message: 'Witness not found',
      });

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      await waitFor(() => {
        expect(result.current.state.witnesses.length).toBe(2);
      });

      await act(async () => {
        await result.current.selectWitness('invalid');
      });

      expect(result.current.state.error).toBe('Failed to load witness');
    });
  });

  // ------------------------------------------
  // Asking Questions Tests (Streaming)
  // ------------------------------------------

  describe('Asking Questions', () => {
    it('sends question via streaming and updates state', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValueOnce(mockWitnesses);
      vi.mocked(api.getWitness).mockResolvedValueOnce(mockWitnessDetail);
      vi.mocked(api.interrogateStream).mockImplementationOnce(
        (_request: unknown, callbacks: StreamCallbacks) => {
          callbacks.onChunk('I was in the library that night.');
          callbacks.onDone({ trust: 60, secrets_revealed: [] });
          return Promise.resolve();
        },
      );

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      await waitFor(() => {
        expect(result.current.state.witnesses.length).toBe(2);
      });

      await act(async () => {
        await result.current.selectWitness('elena');
      });

      await act(async () => {
        await result.current.askQuestion('What did you see?');
      });

      expect(api.interrogateStream).toHaveBeenCalledWith(
        {
          witness_id: 'elena',
          question: 'What did you see?',
          case_id: 'case_001',
          player_id: 'default',
          slot: 'autosave',
        },
        expect.objectContaining({

          onChunk: expect.any(Function),

          onDone: expect.any(Function),

          onError: expect.any(Function),
        }),
        expect.any(AbortSignal),
      );

      // Check conversation updated (placeholder + streamed chunk)
      const lastConversation = result.current.state.conversation[result.current.state.conversation.length - 1];
      expect(lastConversation.question).toBe('What did you see?');
      expect(lastConversation.response).toBe('I was in the library that night.');

      // Check trust updated
      expect(result.current.state.trust).toBe(60);
    });

    it('sets error when no witness is selected', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValueOnce(mockWitnesses);

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      await waitFor(() => {
        expect(result.current.state.witnesses.length).toBe(2);
      });

      await act(async () => {
        await result.current.askQuestion('What did you see?');
      });

      expect(result.current.state.error).toBe('No witness selected');
    });

    it('updates secretsRevealed when secrets are revealed', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValueOnce(mockWitnesses);
      vi.mocked(api.getWitness).mockResolvedValueOnce(mockWitnessDetail);
      vi.mocked(api.interrogateStream).mockImplementationOnce(
        (_request: unknown, callbacks: StreamCallbacks) => {
          callbacks.onChunk('Fine, I will tell you...');
          callbacks.onDone({ trust: 70, secrets_revealed: ['secret_1', 'secret_2'] });
          return Promise.resolve();
        },
      );

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      await waitFor(() => {
        expect(result.current.state.witnesses.length).toBe(2);
      });

      await act(async () => {
        await result.current.selectWitness('elena');
      });

      await act(async () => {
        await result.current.askQuestion('Tell me the truth!');
      });

      expect(result.current.state.secretsRevealed).toContain('secret_1');
      expect(result.current.state.secretsRevealed).toContain('secret_2');
    });
  });

  // ------------------------------------------
  // Presenting Evidence Tests
  // ------------------------------------------

  describe('Presenting Evidence', () => {
    it('presents evidence and updates state', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValueOnce(mockWitnesses);
      vi.mocked(api.getWitness).mockResolvedValueOnce(mockWitnessDetail);
      vi.mocked(api.presentEvidenceStream).mockImplementationOnce(
        (_params, callbacks) => {
          callbacks.onDone(mockPresentEvidenceResponse as unknown as Record<string, unknown>);
          return Promise.resolve();
        }
      );

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      await waitFor(() => {
        expect(result.current.state.witnesses.length).toBe(2);
      });

      await act(async () => {
        await result.current.selectWitness('elena');
      });

      await act(async () => {
        await result.current.presentEvidenceToWitness('hidden_note', 'Hidden Note');
      });

      expect(api.presentEvidenceStream).toHaveBeenCalledWith(
        expect.objectContaining({
          witness_id: 'elena',
          evidence_id: 'hidden_note',
          case_id: 'case_001',
          player_id: 'default',
          slot: 'autosave',
        }),
        expect.any(Object),
        expect.any(AbortSignal),
      );

      // Check conversation updated with evidence presentation
      const lastConversation = result.current.state.conversation[result.current.state.conversation.length - 1];
      expect(lastConversation.question).toBe('What do you know about Hidden Note?');

      // Check secrets revealed
      expect(result.current.state.secretsRevealed).toContain('secret_elena_1');
    });

    it('sets error when no witness selected for evidence presentation', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValueOnce(mockWitnesses);

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      await waitFor(() => {
        expect(result.current.state.witnesses.length).toBe(2);
      });

      await act(async () => {
        await result.current.presentEvidenceToWitness('hidden_note', 'Hidden Note');
      });

      expect(result.current.state.error).toBe('No witness selected');
    });
  });

  // ------------------------------------------
  // Clear Conversation Tests
  // ------------------------------------------

  describe('Clear Conversation', () => {
    it('clears conversation history', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValueOnce(mockWitnesses);
      vi.mocked(api.getWitness).mockResolvedValueOnce(mockWitnessDetail);

      const { result } = renderHook(() =>
        useWitnessInterrogation({ autoLoad: true })
      );

      await waitFor(() => {
        expect(result.current.state.witnesses.length).toBe(2);
      });

      await act(async () => {
        await result.current.selectWitness('elena');
      });

      expect(result.current.state.conversation.length).toBeGreaterThan(0);

      act(() => {
        result.current.clearConversation();
      });

      expect(result.current.state.conversation).toEqual([]);
    });
  });

  // ------------------------------------------
  // Custom Options Tests
  // ------------------------------------------

  describe('Custom Options', () => {
    it('uses custom caseId and playerId', async () => {
      vi.mocked(api.getWitnesses).mockResolvedValueOnce(mockWitnesses);

      const { result } = renderHook(() =>
        useWitnessInterrogation({
          caseId: 'case_002',
          playerId: 'player_123',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.state.witnesses.length).toBe(2);
      });

      expect(api.getWitnesses).toHaveBeenCalledWith('case_002', 'player_123');
    });
  });
});
