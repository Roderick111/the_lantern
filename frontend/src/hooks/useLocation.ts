/**
 * useLocation Hook
 *
 * Manages location state including:
 * - Loading available locations for a case
 * - Changing location via API call
 * - Tracking current location and visited locations
 *
 * @module hooks/useLocation
 * @since Phase 5.2
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { flushSync } from 'react-dom';
import { getLocations, changeLocation } from '../api/client';
import type { LocationInfo, ChangeLocationResponse } from '../types/investigation';

// Re-export LocationInfo for convenience
export type { LocationInfo } from '../types/investigation';

// ============================================
// Types
// ============================================

interface UseLocationOptions {
  /** Case ID to load locations for */
  caseId: string;
  /** Initial location ID (defaults to 'library') */
  initialLocationId?: string;
  /** Player ID for state persistence (defaults to 'default') */
  playerId?: string;
  /** Session ID for state tracking */
  sessionId?: string;
  /** Auto-load locations on mount (defaults to true) */
  autoLoad?: boolean;
  /** Save slot for state (defaults to "autosave") */
  slot?: string;
  /** Content language for location labels and descriptions */
  language?: string;
  /** Callback when location changes successfully */
  onLocationChange?: (locationId: string, response: ChangeLocationResponse) => void;
}

interface UseLocationReturn {
  /** Available locations for this case */
  locations: LocationInfo[];
  /** Current location ID */
  currentLocationId: string;
  /** Array of visited location IDs */
  visitedLocations: string[];
  /** Whether locations are loading */
  loading: boolean;
  /** Whether location change is in progress */
  changing: boolean;
  /** Error message if any operation failed */
  error: string | null;
  /** Change to a new location */
  handleLocationChange: (locationId: string) => Promise<void>;
  /** Manually set the current location ID (internal sync) */
  setCurrentLocationId: (locationId: string) => void;
  /** Reload locations from backend */
  reloadLocations: () => Promise<void>;
  /** Clear error state */
  clearError: () => void;
}

// ============================================
// Hook
// ============================================

// localStorage key for persisting current location per case
const LOCATION_STORAGE_KEY = (caseId: string) => `lantern_game_location_${caseId}`;

export function useLocation({
  caseId,
  initialLocationId = '', // Phase 5.2: Empty string means let backend decide, or wait for fetch
  playerId: _playerId = 'default',
  sessionId,
  autoLoad = true,
  slot = 'autosave',
  language = 'en',
  onLocationChange,
}: UseLocationOptions): UseLocationReturn {
  // State — restore from localStorage if no explicit initialLocationId
  const [locations, setLocations] = useState<LocationInfo[]>([]);
  const [currentLocationId, setCurrentLocationId] = useState(() => {
    if (initialLocationId) return initialLocationId;
    try {
      return localStorage.getItem(LOCATION_STORAGE_KEY(caseId)) ?? '';
    } catch {
      return '';
    }
  });
  const [visitedLocations, setVisitedLocations] = useState<string[]>(currentLocationId ? [currentLocationId] : []);
  const [loading, setLoading] = useState(true);
  const [changing, setChanging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Persist currentLocationId to localStorage for reload recovery
  useEffect(() => {
    if (currentLocationId) {
      try {
        localStorage.setItem(LOCATION_STORAGE_KEY(caseId), currentLocationId);
      } catch { /* localStorage full or unavailable */ }
    }
  }, [currentLocationId, caseId]);

  // Ref to track latest locations for use in callbacks (avoids stale closure)
  const locationsRef = useRef<LocationInfo[]>(locations);
  useEffect(() => {
    locationsRef.current = locations;
  }, [locations]);

  // Load locations from backend
  const loadLocations = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const locs = language === 'en'
        ? await getLocations(caseId, sessionId)
        : await getLocations(caseId, sessionId, language);
      setLocations(locs);

      // If no current location set (initial load), default to the first available location
      // Use functional update to get the latest currentLocationId value
      setCurrentLocationId((prevLocationId) => {
        if (!prevLocationId && locs.length > 0) {
          const firstLocationId = locs[0].id;
          setVisitedLocations(prev => prev.includes(firstLocationId) ? prev : [...prev, firstLocationId]);
          return firstLocationId;
        }
        return prevLocationId;
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load locations';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [caseId, sessionId, language]);

  // Auto-load on mount
  useEffect(() => {
    if (autoLoad) {
      void loadLocations();
    }
  }, [autoLoad, loadLocations]);

  // Handle location change
  const handleLocationChange = useCallback(
    async (locationId: string) => {
      // Skip if already at this location
      if (locationId === currentLocationId) {
        return;
      }

      // Use ref to get latest locations (avoids stale closure issues)
      const currentLocations = locationsRef.current;
      const targetLocation = currentLocations.find((loc) => loc.id === locationId);
      if (!targetLocation) {
        setError(`Location not found: ${locationId}`);
        return;
      }

      setChanging(true);
      setError(null);

      try {
        const response = await changeLocation(caseId, locationId, sessionId, slot);

        // Update current location (with view transition if supported)
        if (document.startViewTransition) {
          document.startViewTransition(() => {
            flushSync(() => setCurrentLocationId(locationId));
          });
        } else {
          setCurrentLocationId(locationId);
        }

        // Add to visited locations if not already visited
        setVisitedLocations((prev) => {
          if (prev.includes(locationId)) {
            return prev;
          }
          return [...prev, locationId];
        });

        // Call optional callback
        if (onLocationChange) {
          onLocationChange(locationId, response);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to change location';
        setError(message);
      } finally {
        setChanging(false);
      }
    },
    [caseId, currentLocationId, sessionId, slot, onLocationChange]
  );

  // Reload locations handler
  const reloadLocations = useCallback(async () => {
    await loadLocations();
  }, [loadLocations]);

  // Clear error handler
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    locations,
    currentLocationId,
    visitedLocations,
    loading,
    changing,
    error,
    handleLocationChange,
    setCurrentLocationId,
    reloadLocations,
    clearError,
  };
}
