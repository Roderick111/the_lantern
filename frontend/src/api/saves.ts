/**
 * Save/Load domain API — state persistence, slots, import/export.
 * @module api/saves
 */

import type {
  LoadResponse,
  InvestigationState,
  SaveSlotMetadata,
  SaveSlotResponse,
  DeleteSlotResponse,
} from '../types/investigation';
import {
  LoadResponseSchema,
  SaveSlotResponseSchema,
  SaveSlotsListResponseSchema,
  DeleteSlotResponseSchema,
} from './schemas';
import { ApiError, apiCall, apiCallNullable } from './base';

export async function loadState(
  caseId: string,
  slot = 'autosave',
  locationId?: string,
): Promise<LoadResponse | null> {
  let path =
    `/api/load/${encodeURIComponent(caseId)}` +
    `?slot=${encodeURIComponent(slot)}`;
  if (locationId) {
    path += `&location_id=${encodeURIComponent(locationId)}`;
  }
  return apiCallNullable('GET', path, LoadResponseSchema);
}

export async function saveGameState(
  _caseId: string,
  state: InvestigationState,
  slot = 'autosave',
  _playerId = 'default',
): Promise<SaveSlotResponse> {
  const result = await apiCall('POST', '/api/save', SaveSlotResponseSchema, {
    state: state,
    slot: slot,
  });
  if (!result.success) {
    throw new ApiError(200, result.message ?? 'Failed to save game state');
  }
  return result;
}

export async function loadGameState(
  caseId: string,
  slot = 'autosave',
): Promise<LoadResponse | null> {
  const path =
    `/api/load/${encodeURIComponent(caseId)}` +
    `?slot=${encodeURIComponent(slot)}`;
  return apiCallNullable('GET', path, LoadResponseSchema);
}

export async function listSaveSlots(
  caseId: string,
): Promise<SaveSlotMetadata[]> {
  const path = `/api/case/${encodeURIComponent(caseId)}/saves/list`;
  const data = await apiCall('GET', path, SaveSlotsListResponseSchema);
  return data.saves;
}

export async function deleteSaveSlot(
  caseId: string,
  slot: string,
): Promise<DeleteSlotResponse> {
  const path =
    `/api/case/${encodeURIComponent(caseId)}` +
    `/saves/${encodeURIComponent(slot)}`;
  return apiCall('DELETE', path, DeleteSlotResponseSchema);
}
