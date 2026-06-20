/**
 * useInvestigation Hook
 *
 * Manages investigation state including:
 * - Loading/saving player state
 * - Fetching location data
 * - Tracking discovered evidence
 * - Handling state persistence
 *
 * @module hooks/useInvestigation
 * @since Phase 1
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  loadState,
  saveGameState,
  getLocation,
  isApiError,
} from '../api/client';
import type {
  InvestigationState,
  LocationResponse,
  Message,
  ConversationMessage,
  ChangeLocationResponse,
} from '../types/investigation';

// ============================================
// Types
// ============================================

interface UseInvestigationOptions {
  /** Case ID to load */
  caseId: string;
  /** Location ID to load */
  locationId: string;
  /** Player ID for state persistence */
  playerId?: string;
  /** Auto-load state on mount (defaults to true) */
  autoLoad?: boolean;
  /** Save slot to load from (defaults to "autosave") */
  slot?: string;
}

interface UseInvestigationReturn {
  /** Current investigation state */
  state: InvestigationState | null;
  /** Current location data */
  location: LocationResponse | null;
  /** Whether initial data is loading */
  loading: boolean;
  /** Error message if loading failed */
  error: string | null;
  /** Whether save is in progress */
  saving: boolean;
  /** Save current state to backend */
  handleSave: () => Promise<boolean>;
  /** Reload state from backend */
  handleLoad: () => Promise<void>;
  /** Add newly discovered evidence to state */
  handleEvidenceDiscovered: (evidenceIds: string[]) => void;
  /** Clear error state */
  clearError: () => void;
  /** Restored conversation messages from backend (Phase 4.4) */
  restoredMessages: Message[] | null;
  /** Update narrator verbosity in local state */
  setNarratorVerbosity: (v: string) => void;
  /** Update game language in local state */
  setLanguage: (v: string) => void;
  /** Apply changeLocation response directly (B3: avoids extra GET roundtrips) */
  applyLocationChange: (response: ChangeLocationResponse) => void;
}

// ============================================
// Hook
// ============================================

/**
 * Convert backend conversation messages to frontend Message format
 * Maps 'matthew' (and legacy 'tom') to 'matthew_ghost' for rendering
 */
function convertConversationMessages(
  messages: ConversationMessage[] | null | undefined
): Message[] | null {
  if (!messages || messages.length === 0) {
    return null;
  }

  return messages.map((msg) => {
    if (msg.type === 'matthew' || msg.type === 'tom') {
      return {
        type: 'matthew_ghost' as const,
        text: msg.text,
        timestamp: msg.timestamp,
      };
    } else if (msg.type === 'player') {
      return {
        type: 'player' as const,
        text: msg.text,
        timestamp: msg.timestamp,
      };
    } else {
      return {
        type: 'narrator' as const,
        text: msg.text,
        timestamp: msg.timestamp,
      };
    }
  });
}

export function useInvestigation({
  caseId,
  locationId,
  playerId = 'default',
  autoLoad = true,
  slot = 'autosave',
}: UseInvestigationOptions): UseInvestigationReturn {
  // State
  const [state, setState] = useState<InvestigationState | null>(null);
  const [location, setLocation] = useState<LocationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Restored conversation messages from backend (Phase 4.4)
  const [restoredMessages, setRestoredMessages] = useState<Message[] | null>(null);

  // B3: skip next loadInitialData after applyLocationChange (prevents extra roundtrips)
  const skipNextLoadRef = useRef(false);

  // Initialize default state
  const createDefaultState = useCallback((): InvestigationState => ({
    case_id: caseId,
    current_location: locationId,
    discovered_evidence: [],
    visited_locations: [locationId],
    narrator_verbosity: 'storyteller',
    language: 'en',
  }), [caseId, locationId]);

  // Load initial data
  const loadInitialData = useCallback(async () => {
    // Guard: Don't load if locationId is empty or invalid
    if (!locationId || locationId === '') {
      console.warn('useInvestigation: locationId is empty, waiting for valid location');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Always load from server
      const [loadedState, locationData] = await Promise.all([
        loadState(caseId, playerId, slot, locationId),
        getLocation(caseId, locationId),
      ]);

      // Use loaded state or create default
      if (loadedState) {
        setState({
          case_id: loadedState.case_id,
          current_location: loadedState.current_location,
          discovered_evidence: loadedState.discovered_evidence,
          visited_locations: loadedState.visited_locations,
          narrator_verbosity: loadedState.narrator_verbosity ?? 'storyteller',
          language: loadedState.language ?? 'en',
        });

        // Restore conversation history (Phase 4.4)
        const history = 'conversation_history' in loadedState ? loadedState.conversation_history : undefined;
        const converted = convertConversationMessages(history);
        setRestoredMessages(converted);
      } else {
        setState(createDefaultState());
        setRestoredMessages(null);
      }

      setLocation(locationData);
    } catch (err) {
      if (isApiError(err)) {
        setError(err.message || 'Failed to load investigation data');
      } else {
        setError('Failed to load investigation data');
      }
      // Still create default state so the app is usable
      setState(createDefaultState());
    } finally {
      setLoading(false);
    }
  }, [caseId, locationId, playerId, slot, createDefaultState]);

  // Auto-load on mount and when locationId changes (Phase 5.2)
  // B3: respect skip flag set by applyLocationChange to cut roundtrips
  useEffect(() => {
    if (autoLoad && locationId && locationId !== '') {
      if (skipNextLoadRef.current) {
        skipNextLoadRef.current = false;
        return;
      }
      void loadInitialData();
    }
  }, [autoLoad, loadInitialData, locationId]);

  // Save state handler — server only
  const handleSave = useCallback(async (): Promise<boolean> => {
    if (!state) {
      setError('No state to save');
      return false;
    }

    setSaving(true);
    setError(null);

    try {
      await saveGameState(caseId, state, slot, playerId);
      return true;
    } catch {
      setError('Failed to save progress');
      return false;
    } finally {
      setSaving(false);
    }
  }, [state, slot, playerId, caseId]);

  // Load state handler
  const handleLoad = useCallback(async () => {
    await loadInitialData();
  }, [loadInitialData]);

  // Evidence discovered handler
  const handleEvidenceDiscovered = useCallback((evidenceIds: string[]) => {
    setState((prev) => {
      if (!prev) return prev;

      // Filter out already discovered evidence
      const newEvidence = evidenceIds.filter(
        (id) => !prev.discovered_evidence.includes(id)
      );

      if (newEvidence.length === 0) {
        return prev;
      }

      return {
        ...prev,
        discovered_evidence: [...prev.discovered_evidence, ...newEvidence],
      };
    });
  }, []);

  // Clear error handler
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const setNarratorVerbosity = useCallback((v: string) => {
    setState((prev) => prev ? { ...prev, narrator_verbosity: v as 'concise' | 'storyteller' | 'atmospheric' } : prev);
  }, []);

  const setLanguage = useCallback((v: string) => {
    setState((prev) => prev ? { ...prev, language: v } : prev);
  }, []);

  // B3: apply data from changeLocation response to avoid loadState+getLocation roundtrips
  const applyLocationChange = useCallback((response: ChangeLocationResponse) => {
    if (response.location) {
      const loc = response.location as unknown as { id: string; name: string; description?: string; surface_elements?: string[] };
      const locData: LocationResponse = {
        id: loc.id,
        name: loc.name,
        description: loc.description ?? '',
        surface_elements: loc.surface_elements ?? [],
      };
      setLocation(locData);
    }

    if (response.updated_state) {
      const us = (response.updated_state ?? {});
      setState((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          current_location: (us.current_location as string) ?? prev.current_location,
          visited_locations: Array.isArray(us.visited_locations) ? us.visited_locations : prev.visited_locations,
          discovered_evidence: Array.isArray(us.discovered_evidence) ? us.discovered_evidence : prev.discovered_evidence,
          narrator_verbosity: (us.narrator_verbosity as InvestigationState["narrator_verbosity"]) ?? prev.narrator_verbosity,
          language: (us.language as string) ?? prev.language,
        };
      });

      // Fix: also pull per-location conversation from full updated_state (B3 omitted this)
      const targetLoc = typeof us.current_location === 'string' ? us.current_location : '';
      let chatHist: unknown[] = [];
      const locChat = (us.location_chat_history as Record<string, unknown> | undefined);
      if (locChat && targetLoc) {
        chatHist = (locChat[targetLoc] as unknown[]) ?? [];
      } else if (Array.isArray(us.conversation_history)) {
        chatHist = us.conversation_history as unknown[];
      }
      const converted = convertConversationMessages(chatHist as ConversationMessage[] | null | undefined);
      setRestoredMessages(converted);
    }

    // signal effect to skip re-fetch
    skipNextLoadRef.current = true;
  }, []);

  return {
    state,
    location,
    loading,
    error,
    saving,
    handleSave,
    handleLoad,
    handleEvidenceDiscovered,
    clearError,
    restoredMessages,
    setNarratorVerbosity,
    setLanguage,
    applyLocationChange,
  };
}
