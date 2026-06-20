/**
 * useLocation Hook Tests
 *
 * Tests for the location state management hook:
 * - Load available locations
 * - Change current location
 * - Track visited locations
 * - Error handling
 *
 * @module hooks/__tests__/useLocation.test
 * @since Phase 5.2
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useLocation } from '../useLocation';
import * as client from '../../api/client';
import type { LocationInfo, ChangeLocationResponse } from '../../types/investigation';

// ============================================
// Mocks
// ============================================

vi.mock('../../api/client');

const mockLocations: LocationInfo[] = [
  { id: 'library', name: 'Blackwood Collegiate Library', type: 'micro' },
  { id: 'dormitory', name: 'Iron Lodge Dormitory', type: 'micro' },
  { id: 'great_hall', name: 'Great Hall', type: 'building' },
];

const mockChangeLocationResponse: ChangeLocationResponse = {
  success: true,
  location: {
    id: 'dormitory',
    name: 'Iron Lodge Dormitory',
    description: 'The Iron Lodge common room...',
  },
  message: 'Location changed successfully',
};

// ============================================
// Test Suite
// ============================================

describe('useLocation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(client.getLocations).mockResolvedValue(mockLocations);
    vi.mocked(client.changeLocation).mockResolvedValue(mockChangeLocationResponse);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ------------------------------------------
  // Initial State Tests
  // ------------------------------------------

  describe('Initial State', () => {
    it('starts with empty locations array', () => {
      vi.mocked(client.getLocations).mockImplementation(
        () => new Promise(() => {
          // Never resolves, prevents auto-load
        })
      );

      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: false,
        })
      );

      expect(result.current.locations).toEqual([]);
    });

    it('starts with initial location ID', () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          initialLocationId: 'library',
          autoLoad: false,
        })
      );

      expect(result.current.currentLocationId).toBe('library');
    });

    it('starts with default location ID when not specified', () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: false,
        })
      );

      expect(result.current.currentLocationId).toBe('');
    });

    it('starts with initial location in visited array', () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          initialLocationId: 'dormitory',
          autoLoad: false,
        })
      );

      expect(result.current.visitedLocations).toEqual(['dormitory']);
    });

    it('starts loading when autoLoad is true', async () => {
      vi.mocked(client.getLocations).mockImplementation(() =>
        new Promise((resolve) => setTimeout(() => resolve(mockLocations), 100))
      );

      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: true,
        })
      );

      expect(result.current.loading).toBe(true);

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
    });

    it('starts not changing', () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: false,
        })
      );

      expect(result.current.changing).toBe(false);
    });

    it('starts with no error', () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: false,
        })
      );

      expect(result.current.error).toBeNull();
    });
  });

  // ------------------------------------------
  // Load Locations Tests
  // ------------------------------------------

  describe('Load Locations', () => {
    it('auto-loads locations on mount', async () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.locations).toEqual(mockLocations);
      });

      expect(client.getLocations).toHaveBeenCalledWith('case_001', undefined);
    });

    it('passes sessionId to getLocations when provided', async () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          sessionId: 'session_123',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.locations).toEqual(mockLocations);
      });

      expect(client.getLocations).toHaveBeenCalledWith('case_001', 'session_123');
    });

    it('sets loading state during API call', async () => {
      let resolvePromise: (value: LocationInfo[]) => void;
      const promise = new Promise<LocationInfo[]>((resolve) => {
        resolvePromise = resolve;
      });
      vi.mocked(client.getLocations).mockReturnValue(promise);

      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: true,
        })
      );

      expect(result.current.loading).toBe(true);

      await act(async () => {
        resolvePromise!(mockLocations);
        await promise;
      });

      expect(result.current.loading).toBe(false);
    });

    it('handles load error', async () => {
      vi.mocked(client.getLocations).mockRejectedValue(new Error('Failed to load locations'));

      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.error).toBe('Failed to load locations');
      });
    });

    it('can manually reload locations', async () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: false,
        })
      );

      await act(async () => {
        await result.current.reloadLocations();
      });

      expect(result.current.locations).toEqual(mockLocations);
    });
  });

  // ------------------------------------------
  // Change Location Tests
  // ------------------------------------------

  describe('handleLocationChange', () => {
    it('changes current location', async () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          initialLocationId: 'library',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.locations.length).toBe(3);
      });

      await act(async () => {
        await result.current.handleLocationChange('dormitory');
      });

      expect(result.current.currentLocationId).toBe('dormitory');
    });

    it('adds new location to visited array', async () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          initialLocationId: 'library',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.locations.length).toBe(3);
      });

      await act(async () => {
        await result.current.handleLocationChange('dormitory');
      });

      expect(result.current.visitedLocations).toContain('dormitory');
    });

    it('does not duplicate in visited array', async () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          initialLocationId: 'library',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.locations.length).toBe(3);
      });

      // Visit dormitory
      await act(async () => {
        await result.current.handleLocationChange('dormitory');
      });

      // Go back to library
      vi.mocked(client.changeLocation).mockResolvedValue({
        success: true,
        location: { id: 'library', name: 'Blackwood Collegiate Library', description: '...' },
      });

      await act(async () => {
        await result.current.handleLocationChange('library');
      });

      // Visit dormitory again
      vi.mocked(client.changeLocation).mockResolvedValue(mockChangeLocationResponse);

      await act(async () => {
        await result.current.handleLocationChange('dormitory');
      });

      // Should only have library and dormitory, no duplicates
      const dormitoryCount = result.current.visitedLocations.filter(
        (id) => id === 'dormitory'
      ).length;
      expect(dormitoryCount).toBe(1);
    });

    it('skips if already at target location', async () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          initialLocationId: 'library',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.locations.length).toBe(3);
      });

      await act(async () => {
        await result.current.handleLocationChange('library');
      });

      // Should not call changeLocation API
      expect(client.changeLocation).not.toHaveBeenCalled();
    });

    it('sets error if location not found', async () => {
      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.locations.length).toBe(3);
      });

      await act(async () => {
        await result.current.handleLocationChange('nonexistent');
      });

      expect(result.current.error).toBe('Location not found: nonexistent');
    });

    it('sets changing state during API call', async () => {
      let resolvePromise: (value: ChangeLocationResponse) => void;
      const promise = new Promise<ChangeLocationResponse>((resolve) => {
        resolvePromise = resolve;
      });

      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.locations.length).toBe(3);
      });

      vi.mocked(client.changeLocation).mockReturnValue(promise);

      act(() => {
        void result.current.handleLocationChange('dormitory');
      });

      expect(result.current.changing).toBe(true);

      await act(async () => {
        resolvePromise!(mockChangeLocationResponse);
        await promise;
      });

      expect(result.current.changing).toBe(false);
    });

    it('calls onLocationChange callback when provided', async () => {
      const onLocationChange = vi.fn();

      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: true,
          onLocationChange,
        })
      );

      await waitFor(() => {
        expect(result.current.locations.length).toBe(3);
      });

      await act(async () => {
        await result.current.handleLocationChange('dormitory');
      });

      expect(onLocationChange).toHaveBeenCalledWith('dormitory', mockChangeLocationResponse);
    });

    it('handles change location error', async () => {
      vi.mocked(client.changeLocation).mockRejectedValue(new Error('Server error'));

      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.locations.length).toBe(3);
      });

      await act(async () => {
        await result.current.handleLocationChange('dormitory');
      });

      expect(result.current.error).toBe('Server error');
      // Should not change location on error
      expect(result.current.currentLocationId).toBe('library');
    });
  });

  // ------------------------------------------
  // Clear Error Tests
  // ------------------------------------------

  describe('clearError', () => {
    it('clears error state', async () => {
      vi.mocked(client.getLocations).mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() =>
        useLocation({
          caseId: 'case_001',
          autoLoad: true,
        })
      );

      await waitFor(() => {
        expect(result.current.error).toBe('Network error');
      });

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });
});
