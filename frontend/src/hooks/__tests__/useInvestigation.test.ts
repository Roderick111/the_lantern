/**
 * Tests for useInvestigation Hook (Phase 4.4)
 *
 * Covers conversation restoration functionality:
 * - Loading with conversation_history -> Messages mapped correctly
 * - Loading with empty conversation_history -> No errors
 * - Message keys unique and stable
 * - Type conversion (matthew/tom -> matthew_ghost)
 */

import { renderHook, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useInvestigation } from '../useInvestigation';
import * as client from '../../api/client';
import { ApiError } from '../../api/base';
import type { LoadResponse, LocationResponse } from '../../types/investigation';

// Mock the API client (preserve isApiError from barrel)
vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return {
    ...actual,
    loadState: vi.fn(),
    saveGameState: vi.fn(),
    getLocation: vi.fn(),
  };
});

describe('useInvestigation Hook', () => {
  const mockLocation: LocationResponse = {
    id: 'library',
    name: 'Blackwood Collegiate Library',
    description: 'A grand library',
    surface_elements: ['desk', 'bookshelf'],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Default mocks
    vi.mocked(client.getLocation).mockResolvedValue(mockLocation);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic hook functionality', () => {
    it('initializes with loading state', () => {
      vi.mocked(client.loadState).mockResolvedValue(null);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      expect(result.current.loading).toBe(true);
    });

    it('creates default state when no saved state exists', async () => {
      vi.mocked(client.loadState).mockResolvedValue(null);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.state).toEqual({
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
        narrator_verbosity: 'storyteller',
        language: 'en',
      });
      expect(result.current.restoredMessages).toBeNull();
    });

    it('does not create default state when load fails with an error', async () => {
      vi.mocked(client.loadState).mockRejectedValue(
        new ApiError(400, 'Corrupted save in slot autosave: invalid JSON'),
      );

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' }),
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.state).toBeNull();
      expect(result.current.error).toContain('Corrupted save');
      expect(result.current.restoredMessages).toBeNull();
    });
  });

  describe('Conversation restoration (Phase 4.4)', () => {
    it('restores conversation_history from backend', async () => {
      const savedState: LoadResponse = {
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: ['hidden_note'],
        visited_locations: ['library'],
        conversation_history: [
          { type: 'player', text: 'I examine the desk', timestamp: 1000 },
          { type: 'narrator', text: 'You find a hidden note.', timestamp: 1001 },
          { type: 'tom', text: 'Interesting find...', timestamp: 1002 },
        ],
      };

      vi.mocked(client.loadState).mockResolvedValue(savedState);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.restoredMessages).not.toBeNull();
      expect(result.current.restoredMessages).toHaveLength(3);
    });

    it('converts matthew type to matthew_ghost for rendering', async () => {
      const savedState: LoadResponse = {
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
        conversation_history: [
          { type: 'matthew', text: 'A ghostly whisper...', timestamp: 1000 },
        ],
      };

      vi.mocked(client.loadState).mockResolvedValue(savedState);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const messages = result.current.restoredMessages;
      expect(messages).not.toBeNull();
      expect(messages![0].type).toBe('matthew_ghost');
      expect(messages![0].text).toBe('A ghostly whisper...');
    });

    it('converts legacy tom type to matthew_ghost for rendering', async () => {
      const savedState: LoadResponse = {
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
        conversation_history: [
          { type: 'tom', text: 'Legacy whisper...', timestamp: 1000 },
        ],
      };

      vi.mocked(client.loadState).mockResolvedValue(savedState);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const messages = result.current.restoredMessages;
      expect(messages).not.toBeNull();
      expect(messages![0].type).toBe('matthew_ghost');
      expect(messages![0].text).toBe('Legacy whisper...');
    });

    it('preserves player message type', async () => {
      const savedState: LoadResponse = {
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
        conversation_history: [
          { type: 'player', text: 'I check the window', timestamp: 1000 },
        ],
      };

      vi.mocked(client.loadState).mockResolvedValue(savedState);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const messages = result.current.restoredMessages;
      expect(messages![0].type).toBe('player');
      expect(messages![0].text).toBe('I check the window');
    });

    it('preserves narrator message type', async () => {
      const savedState: LoadResponse = {
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
        conversation_history: [
          { type: 'narrator', text: 'The window reveals nothing.', timestamp: 1000 },
        ],
      };

      vi.mocked(client.loadState).mockResolvedValue(savedState);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const messages = result.current.restoredMessages;
      expect(messages![0].type).toBe('narrator');
      expect(messages![0].text).toBe('The window reveals nothing.');
    });

    it('preserves timestamps from backend', async () => {
      const savedState: LoadResponse = {
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
        conversation_history: [
          { type: 'player', text: 'Test', timestamp: 1704067200000 },
        ],
      };

      vi.mocked(client.loadState).mockResolvedValue(savedState);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.restoredMessages![0].timestamp).toBe(1704067200000);
    });

    it('handles empty conversation_history gracefully', async () => {
      const savedState: LoadResponse = {
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: ['note'],
        visited_locations: ['library'],
        conversation_history: [],
      };

      vi.mocked(client.loadState).mockResolvedValue(savedState);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.restoredMessages).toBeNull();
    });

    it('handles missing conversation_history field gracefully', async () => {
      const savedState: LoadResponse = {
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
        // conversation_history is undefined
      };

      vi.mocked(client.loadState).mockResolvedValue(savedState);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.restoredMessages).toBeNull();
    });

    it('maintains message order from backend', async () => {
      const savedState: LoadResponse = {
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
        conversation_history: [
          { type: 'player', text: 'First', timestamp: 1000 },
          { type: 'narrator', text: 'Second', timestamp: 1001 },
          { type: 'tom', text: 'Third', timestamp: 1002 },
          { type: 'player', text: 'Fourth', timestamp: 1003 },
        ],
      };

      vi.mocked(client.loadState).mockResolvedValue(savedState);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const messages = result.current.restoredMessages!;
      expect(messages[0].text).toBe('First');
      expect(messages[1].text).toBe('Second');
      expect(messages[2].text).toBe('Third');
      expect(messages[3].text).toBe('Fourth');
    });
  });

  describe('handleEvidenceDiscovered', () => {
    it('adds new evidence ids to the discovered_evidence set', async () => {
      vi.mocked(client.loadState).mockResolvedValue(null);

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' }),
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.state?.discovered_evidence).toEqual([]);

      // Synchronously call the handler with a new evidence id
      result.current.handleEvidenceDiscovered(['hidden_note']);

      await waitFor(() => {
        expect(result.current.state?.discovered_evidence).toEqual([
          'hidden_note',
        ]);
      });
    });

    it('deduplicates already-discovered evidence ids', async () => {
      vi.mocked(client.loadState).mockResolvedValue({
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: ['note_a'],
        visited_locations: ['library'],
      });

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' }),
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Try to add an already-discovered id along with a new one
      result.current.handleEvidenceDiscovered(['note_a', 'note_b']);

      await waitFor(() => {
        expect(result.current.state?.discovered_evidence).toEqual([
          'note_a',
          'note_b',
        ]);
      });
    });
  });

  describe('handleSave', () => {
    it('calls saveGameState with caseId, current state, slot, and playerId', async () => {
      vi.mocked(client.loadState).mockResolvedValue(null);
      vi.mocked(client.saveGameState).mockResolvedValue({
        success: true,
        message: 'ok',
      });

      const { result } = renderHook(() =>
        useInvestigation({
          caseId: 'case_001',
          locationId: 'library',
          playerId: 'player-xyz',
          slot: 'slot_2',
        }),
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const ok = await result.current.handleSave();
      expect(ok).toBe(true);

      expect(client.saveGameState).toHaveBeenCalledTimes(1);
      expect(client.saveGameState).toHaveBeenCalledWith(
        'case_001',
        expect.objectContaining({
          case_id: 'case_001',
          current_location: 'library',
        }),
        'slot_2',
        'player-xyz',
      );
    });

    it('returns false and surfaces an error when saveGameState rejects', async () => {
      vi.mocked(client.loadState).mockResolvedValue(null);
      vi.mocked(client.saveGameState).mockRejectedValue(new Error('network down'));

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' }),
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const ok = await result.current.handleSave();
      expect(ok).toBe(false);

      await waitFor(() => {
        expect(result.current.error).toBe('Failed to save progress');
      });
    });
  });

  describe('Reload behavior', () => {
    it('updates restoredMessages on handleLoad', async () => {
      // First load: no conversation history
      vi.mocked(client.loadState).mockResolvedValueOnce({
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
      });

      const { result } = renderHook(() =>
        useInvestigation({ caseId: 'case_001', locationId: 'library' })
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.restoredMessages).toBeNull();

      // Second load: with conversation history
      vi.mocked(client.loadState).mockResolvedValueOnce({
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: ['note'],
        visited_locations: ['library'],
        conversation_history: [
          { type: 'player', text: 'Reload test', timestamp: 2000 },
        ],
      });

      await result.current.handleLoad();

      await waitFor(() => {
        expect(result.current.restoredMessages).not.toBeNull();
      });

      expect(result.current.restoredMessages![0].text).toBe('Reload test');
    });
  });
});
