/**
 * Anonymous Player ID Management
 *
 * Generates and persists a UUID per browser via localStorage.
 * Session bootstrap (POST /api/session) may later upgrade this
 * to a server-issued ID, but the key stays the same.
 *
 * Use `usePlayerId()` hook inside React components for lazy resolution
 * (avoids top-level side effects at module import time).
 *
 * @module utils/playerId
 */

import { useMemo } from 'react';

const KEY = 'lantern_player_id';

export function getOrCreatePlayerId(): string {
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(KEY, id);
  }
  return id;
}

/**
 * React hook for lazy player ID resolution.
 * Safe to call from components/effects — no module top-level execution.
 */
export function usePlayerId(): string {
  return useMemo(() => getOrCreatePlayerId(), []);
}
