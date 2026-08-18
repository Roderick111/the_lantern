/**
 * LLM configuration domain API — BYOK key verification, models.
 * Also player settings update (narrator verbosity, language).
 * @module api/settings
 */

import { API_BASE_URL, apiCall } from './base';
import { UpdateSettingsResponseSchema } from './schemas';

// ============================================
// Player Settings (verbosity, language)
// ============================================

export interface UpdateSettingsRequest {
  case_id: string;
  narrator_verbosity?: 'concise' | 'storyteller' | 'atmospheric';
  assistance_mode?: 'normal' | 'easy';
  language?: string;
  slot?: string;
}

export interface UpdateSettingsResponse {
  success: boolean;
  message: string;
}

/**
 * Update player settings (narrator verbosity, language).
 * Routes through API_BASE_URL via apiCall so prod deploys with cross-origin
 * frontend/backend reach the right host.
 */
export async function updateSettings(
  request: UpdateSettingsRequest,
): Promise<UpdateSettingsResponse> {
  return apiCall(
    'POST',
    '/api/settings/update',
    UpdateSettingsResponseSchema,
    request,
  );
}

export interface VerifyKeyResponse {
  valid: boolean;
  error?: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  free: boolean;
}

export async function verifyApiKey(
  provider: string,
  apiKey: string,
  model?: string,
): Promise<VerifyKeyResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, api_key: apiKey, model }),
    });
    return (await response.json()) as VerifyKeyResponse;
  } catch {
    return { valid: false, error: 'Network error' };
  }
}

export async function getAvailableModels(): Promise<ModelInfo[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm/models`);
    return (await response.json()) as ModelInfo[];
  } catch {
    return [];
  }
}

export async function getActiveModel(): Promise<{
  model_id: string;
  model_name: string;
} | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/llm/active`);
    return (await response.json()) as { model_id: string; model_name: string };
  } catch {
    return null;
  }
}
