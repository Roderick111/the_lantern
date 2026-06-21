/**
 * API Client — shared infrastructure.
 *
 * Contains base URL, error handling, LLM headers, Zod parsing,
 * and generic helpers (apiCall, apiCallNullable, streamSSE).
 *
 * @module api/base
 */

import { z } from 'zod';
import { formatZodError } from './schemas';

// ============================================
// Configuration
// ============================================

function getApiBaseUrl(): string {
  const url = import.meta.env.VITE_API_URL as string | undefined;

  if (url && typeof url === 'string' && !url.startsWith('http')) {
    console.warn('VITE_API_URL should include protocol (http:// or https://)');
  }

  // In dev, prefer relative URL so Vite proxy handles /api calls (avoids CORS and localhost resolution issues)
  if (!url && import.meta.env.DEV) {
    return '';
  }

  return url ?? 'http://localhost:8000';
}

export const API_BASE_URL = getApiBaseUrl();

// ============================================
// Session / Auth Token
// ============================================

const TOKEN_KEY = 'lantern_player_token';
const PLAYER_ID_KEY = 'lantern_player_id';

function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

async function bootstrapSession(refreshToken?: string | null): Promise<void> {
  const existingPlayerId = localStorage.getItem(PLAYER_ID_KEY);
  const currentToken = refreshToken ?? getStoredToken();
  const response = await fetch(`${API_BASE_URL}/api/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      existing_player_id: existingPlayerId,
      current_token: currentToken,
    }),
  });

  if (!response.ok) {
    throw new Error(`Session bootstrap failed: ${response.status}`);
  }

  const data = (await response.json()) as { player_id: string; token: string };
  localStorage.setItem(TOKEN_KEY, data.token);
  localStorage.setItem(PLAYER_ID_KEY, data.player_id);
}

let sessionReady: Promise<void> | null = null;

export async function ensureSession(): Promise<void> {
  if (getStoredToken()) return;
  sessionReady ??= bootstrapSession().catch((err) => {
    sessionReady = null;
    throw err;
  });
  return sessionReady;
}

export function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { 'X-Player-Token': token } : {};
}

// B2 guard: prevent 401 storm / loops on rapid errors
let last401At = 0;

// dispatch toast event for UI (listened in App.tsx)
function notifySessionExpired(): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent('lantern-session-expired', {
        detail: { message: 'Session expired — refreshing' },
      }),
    );
  }
}

// Handle 401: clear creds, force re-bootstrap next ensure, notify, guard loop
function handle401(): void {
  const now = Date.now();
  if (now - last401At < 1500) {
    // guard: ignore rapid duplicate 401s to break loops
    return;
  }
  last401At = now;

  const expiredToken = getStoredToken();
  localStorage.removeItem(TOKEN_KEY);
  sessionReady = null; // force re-bootstrap on next call

  notifySessionExpired();

  // Refresh session with expired token to preserve player_id and saves
  void bootstrapSession(expiredToken).catch(() => {
    localStorage.removeItem(PLAYER_ID_KEY);
  });
}

// ============================================
// BYOK (Bring Your Own Key) Headers
// ============================================

const LLM_SETTINGS_KEY = 'lantern_llm_settings';

export interface LLMSettings {
  provider: string | null;
  apiKey: string | null;
  model: string | null;
}

/** BYOK keys live in sessionStorage (cleared when the tab closes). */
function readLLMSettingsRaw(): string | null {
  const sessionRaw = sessionStorage.getItem(LLM_SETTINGS_KEY);
  if (sessionRaw) return sessionRaw;

  const legacyRaw = localStorage.getItem(LLM_SETTINGS_KEY);
  if (!legacyRaw) return null;

  sessionStorage.setItem(LLM_SETTINGS_KEY, legacyRaw);
  localStorage.removeItem(LLM_SETTINGS_KEY);
  return legacyRaw;
}

export function getLLMSettings(): LLMSettings | null {
  const raw = readLLMSettingsRaw();
  if (!raw) return null;
  try {
    return JSON.parse(raw) as LLMSettings;
  } catch {
    return null;
  }
}

export function saveLLMSettings(settings: LLMSettings): void {
  sessionStorage.setItem(LLM_SETTINGS_KEY, JSON.stringify(settings));
  localStorage.removeItem(LLM_SETTINGS_KEY);
}

export function clearLLMSettings(): void {
  sessionStorage.removeItem(LLM_SETTINGS_KEY);
  localStorage.removeItem(LLM_SETTINGS_KEY);
}

export function getLLMHeaders(): Record<string, string> {
  const settings = getLLMSettings();
  if (!settings) return {};
  const headers: Record<string, string> = {};
  if (settings.apiKey) headers['X-User-API-Key'] = settings.apiKey;
  if (settings.model) headers['X-User-Model'] = settings.model;
  return headers;
}

// ============================================
// Error Handling
// ============================================

interface ErrorResponseBody {
  detail?: string;
  message?: string;
}

/**
 * Custom Error class for API errors.
 * Extends Error to satisfy eslint @typescript-eslint/only-throw-error.
 */
export class ApiError extends Error {
  status: number;
  details?: string;

  constructor(status: number, message: string, details?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    typeof (error as ApiError).status === 'number'
  );
}

async function createApiError(response: Response): Promise<ApiError> {
  let message = `API error: ${response.status} ${response.statusText}`;
  let details: string | undefined;

  try {
    const errorBody = (await response.json()) as ErrorResponseBody;
    if (errorBody.detail) {
      message = errorBody.detail;
    } else if (errorBody.message) {
      message = errorBody.message;
    }
    details = JSON.stringify(errorBody);
  } catch {
    // Response body is not JSON, use default message
  }

  return new ApiError(response.status, message, details);
}

function handleFetchError(error: unknown): ApiError {
  if (error instanceof TypeError) {
    return new ApiError(
      0,
      'Network error: Unable to connect to server. Is the backend running?',
      error.message,
    );
  }

  if (error instanceof Error) {
    return new ApiError(0, error.message, error.stack);
  }

  return new ApiError(0, 'An unexpected error occurred');
}

function handleZodError(error: z.ZodError): ApiError {
  const message = `Invalid API response: ${formatZodError(error)}`;
  return new ApiError(0, message, JSON.stringify(error.issues));
}

// ============================================
// Generic Helpers
// ============================================

export function parseResponse<T>(data: unknown, schema: z.ZodType<T>): T {
  if (data === null) {
    throw new ApiError(
      0,
      'Invalid API response: Received null instead of expected data',
      'Backend returned null with 200 status. Should return 404 for missing data.',
    );
  }

  const result = schema.safeParse(data);

  if (!result.success) {
    throw handleZodError(result.error);
  }

  return result.data;
}

/**
 * Generic API call with fetch + LLM headers + error handling + Zod parse.
 * B2: on 401 clear token, rebootstrap, toast, guard.
 */
export async function apiCall<T>(
  method: string,
  path: string,
  schema: z.ZodType<T>,
  body?: unknown,
): Promise<T> {
  try {
    await ensureSession();
    let response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...getLLMHeaders(),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });

    if (response.status === 401) {
      handle401();
      // retry once with fresh session (ensure will bootstrap)
      await ensureSession();
      response = await fetch(`${API_BASE_URL}${path}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
          ...getLLMHeaders(),
        },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
    }

    if (!response.ok) {
      throw await createApiError(response);
    }

    const data: unknown = await response.json();
    return parseResponse(data, schema);
  } catch (error) {
    if (isApiError(error)) {
      throw error;
    }
    throw handleFetchError(error);
  }
}

/**
 * Generic API call that returns null on 404 instead of throwing.
 * Also handles null response bodies gracefully.
 * B2: 401 handling + retry once.
 */
export async function apiCallNullable<T>(
  method: string,
  path: string,
  schema: z.ZodType<T>,
  body?: unknown,
): Promise<T | null> {
  try {
    await ensureSession();
    let response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...getLLMHeaders(),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });

    if (response.status === 401) {
      handle401();
      await ensureSession();
      response = await fetch(`${API_BASE_URL}${path}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
          ...getLLMHeaders(),
        },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
    }

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      throw await createApiError(response);
    }

    const data: unknown = await response.json();
    if (data === null) {
      return null;
    }

    const result = schema.safeParse(data);
    if (!result.success) {
      throw handleZodError(result.error);
    }
    return result.data;
  } catch (error) {
    if (isApiError(error)) {
      throw error;
    }
    throw handleFetchError(error);
  }
}

// ============================================
// Streaming SSE
// ============================================

export interface StreamCallbacks {
  onChunk: (text: string) => void;
  onDone: (data: Record<string, unknown>) => void;
  onError: (error: string) => void;
}

/**
 * Type guard for AbortError-shaped exceptions.
 * Fetch + reader throw a DOMException with name='AbortError' when their
 * AbortSignal fires. We treat this as an intentional cancel, not an error.
 */
function isAbortError(err: unknown): boolean {
  return (
    typeof err === 'object' &&
    err !== null &&
    'name' in err &&
    (err as { name: string }).name === 'AbortError'
  );
}

export async function streamSSE(
  url: string,
  body: unknown,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  await ensureSession();
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...getLLMHeaders(),
      },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    // Caller aborted before/during fetch — silent.
    if (signal?.aborted || isAbortError(err)) return;
    throw err;
  }

  if (response.status === 401) {
    handle401();
    // do not retry stream here (caller decides), just error out cleanly
    callbacks.onError('HTTP 401');
    return;
  }

  if (!response.ok || !response.body) {
    try {
      const errBody = (await response.json()) as { detail?: unknown };
      if (typeof errBody.detail === 'string') {
        callbacks.onError(errBody.detail);
        return;
      }
    } catch {
      // non-JSON error body
    }
    callbacks.onError(`HTTP ${response.status}`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let receivedDone = false;
  let receivedAnyChunk = false;

  try {
    while (true) {
      if (signal?.aborted) return;
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6)) as Record<string, unknown>;
          if (data.error) {
            const code = typeof data.code === 'string' ? data.code : undefined;
            const message = data.error as string;
            callbacks.onError(code ? `${message} (${code})` : message);
            return;
          }
          if (data.done) {
            receivedDone = true;
            callbacks.onDone(data);
            return;
          }
          if (data.text) {
            receivedAnyChunk = true;
            callbacks.onChunk(data.text as string);
          }
        } catch {
          // Skip malformed SSE lines (including keepalive comments)
        }
      }
    }
  } catch (err) {
    // Cancellation surfaces here as AbortError — exit silently.
    if (signal?.aborted || isAbortError(err)) return;
    throw err;
  }

  // Stream ended without a done message — connection was dropped
  if (!receivedDone && receivedAnyChunk) {
    callbacks.onError('Connection lost — response may be incomplete.');
  }
}
