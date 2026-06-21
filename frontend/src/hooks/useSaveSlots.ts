/**
 * useSaveSlots Hook
 *
 * Manages save slot operations (save, load, list, delete) via server API.
 * All persistence goes through the backend.
 *
 * @module hooks/useSaveSlots
 * @since Phase 5.3, updated for server-only saves
 */

import { useState, useCallback, useEffect } from 'react';
import {
  saveGameState,
  loadGameState,
  listSaveSlots,
  deleteSaveSlot,
} from '../api/client';
import type { SaveSlotMetadata, InvestigationState, LoadResponse } from '../types/investigation';

// ============================================
// Hook
// ============================================

export function useSaveSlots(caseId: string, _playerId?: string) {
  const [slots, setSlots] = useState<SaveSlotMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Refresh the list of save slots from server
   */
  const refreshSlots = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const savedSlots = await listSaveSlots(caseId);
      setSlots(savedSlots);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'Failed to load save slots';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  /**
   * Save game state to a specific slot via server
   */
  const saveToSlot = useCallback(
    async (slot: string, state: InvestigationState): Promise<boolean> => {
      try {
        setLoading(true);
        setError(null);
        await saveGameState(caseId, state, slot);
        await refreshSlots();
        return true;
      } catch (e) {
        const errorMessage = e instanceof Error ? e.message : `Failed to save to ${slot}`;
        setError(errorMessage);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [caseId, refreshSlots]
  );

  /**
   * Load game state from a specific slot via server
   */
  const loadFromSlot = useCallback(
    async (slot: string): Promise<LoadResponse | null> => {
      try {
        setLoading(true);
        setError(null);
        return await loadGameState(caseId, slot);
      } catch (e) {
        const errorMessage = e instanceof Error ? e.message : `Failed to load from ${slot}`;
        setError(errorMessage);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [caseId]
  );

  /**
   * Delete a specific save slot via server
   */
  const deleteSlot = useCallback(
    async (slot: string): Promise<boolean> => {
      try {
        setLoading(true);
        setError(null);
        await deleteSaveSlot(caseId, slot);
        await refreshSlots();
        return true;
      } catch (e) {
        const errorMessage = e instanceof Error ? e.message : `Failed to delete ${slot}`;
        setError(errorMessage);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [caseId, refreshSlots]
  );

  // Load slots on mount
  useEffect(() => {
    void refreshSlots();
  }, [refreshSlots]);

  return {
    slots,
    loading,
    error,
    saveToSlot,
    loadFromSlot,
    deleteSlot,
    refreshSlots,
  };
}
