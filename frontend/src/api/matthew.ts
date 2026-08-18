/**
 * Matthew Croft spirit companion API — triggers, auto-comments, chat.
 * @module api/matthew
 */

import type { MatthewTrigger, MatthewResponse } from '../types/investigation';
import { MatthewTriggerSchema, MatthewResponseSchema } from './schemas';
import { apiCall, apiCallNullable, API_BASE_URL, isApiError, getLLMHeaders, getAuthHeaders, ensureSession } from './base';
import { ApiError } from './base';

export async function checkMatthewTrigger(
  caseId: string,
  evidenceCount: number,
  slot = 'autosave',
): Promise<MatthewTrigger | null> {
  const path =
    `/api/case/${encodeURIComponent(caseId)}/matthew/triggers/check` +
    `?slot=${encodeURIComponent(slot)}`;
  return apiCallNullable('POST', path, MatthewTriggerSchema, {
    evidence_count: evidenceCount,
  });
}

/**
 * Check if Matthew wants to auto-comment after evidence discovery.
 * Returns null on 204 (Matthew stays quiet).
 */
export async function checkMatthewAutoComment(
  caseId: string,
  isCritical = false,
  slot = 'autosave',
): Promise<MatthewResponse | null> {
  try {
    await ensureSession();
    const path =
      `/api/case/${encodeURIComponent(caseId)}/matthew/auto-comment` +
      `?slot=${encodeURIComponent(slot)}`;

    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...getLLMHeaders(),
      },
      body: JSON.stringify({ is_critical: isCritical }),
    });

    // 204 means Matthew stays quiet
    if (response.status === 204) {
      return null;
    }

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      const errData = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new ApiError(response.status, errData.detail ?? response.statusText);
    }

    const data: unknown = await response.json();
    if (data === null) return null;

    const result = MatthewResponseSchema.safeParse(data);
    if (!result.success) {
      throw new ApiError(0, `Invalid API response: ${result.error.message}`);
    }
    return result.data;
  } catch (error) {
    if (isApiError(error)) throw error;
    if (error instanceof TypeError) {
      throw new ApiError(0, 'Network error: Unable to connect to server.', error.message);
    }
    throw new ApiError(0, 'An unexpected error occurred');
  }
}

export async function sendMatthewChat(
  caseId: string,
  message: string,
  slot = 'autosave',
): Promise<MatthewResponse> {
  const path =
    `/api/case/${encodeURIComponent(caseId)}/matthew/chat` +
    `?slot=${encodeURIComponent(slot)}`;
  return apiCall('POST', path, MatthewResponseSchema, { message });
}