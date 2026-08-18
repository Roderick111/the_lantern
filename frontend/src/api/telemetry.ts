/**
 * Telemetry client — batched, fire-and-forget.
 * Never throws, never blocks UI.
 *
 * Uses auth headers (X-Player-Token) instead of raw player_id in body.
 * Server injects player identity from token.
 */

import { getAuthHeaders, ensureSession } from './base';

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? (import.meta.env.DEV ? '' : 'http://localhost:8000');
const BATCH_SIZE = 10;
const FLUSH_INTERVAL_MS = 5000;

interface TelemetryEvent {
  event_type: string;
  case_id: string;
  data: Record<string, unknown>;
}

const eventQueue: TelemetryEvent[] = [];
let flushTimer: ReturnType<typeof setInterval> | null = null;

function getCaseId(): string {
  try {
    const session = localStorage.getItem('lantern-active-session');
    if (session) {
      const parsed = JSON.parse(session) as Record<string, string>;
      return parsed.caseId ?? 'unknown';
    }
  } catch {
    // ignore
  }
  return 'unknown';
}

// eslint-disable-next-line @typescript-eslint/no-empty-function
const noop = () => {};

async function flush(): Promise<void> {
  if (eventQueue.length === 0) return;

  const batch = eventQueue.splice(0, BATCH_SIZE);

  // Ensure session token (non-blocking)
  await ensureSession().catch(noop);

  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
  };

  // Fire all in parallel; ignore individual failures
  const sends = batch.map((event) =>
    fetch(`${API_BASE}/api/telemetry/event`, {
      method: 'POST',
      headers,
      body: JSON.stringify(event),
    }).catch(noop),
  );
  await Promise.allSettled(sends);
}

function ensureTimer(): void {
  flushTimer ??= setInterval(() => { void flush(); }, FLUSH_INTERVAL_MS);
}

/**
 * Log a telemetry event. Fire-and-forget — never throws.
 */
export function logEvent(eventType: string, data: Record<string, unknown> = {}): void {
  eventQueue.push({
    event_type: eventType,
    case_id: getCaseId(),
    data,
  });

  ensureTimer();

  if (eventQueue.length >= BATCH_SIZE) {
    void flush();
  }
}

/**
 * Log a frontend error. Sends immediately.
 */
export function logError(
  errorType: string,
  message: string,
  context: Record<string, unknown> = {},
): void {
  void ensureSession().catch(noop);

  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
  };

  fetch(`${API_BASE}/api/telemetry/error`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      error_type: errorType,
      case_id: getCaseId(),
      message: message.slice(0, 500),
      context,
    }),
  }).catch(noop);
}

/**
 * Log session start — fires once per browser tab.
 * sessionStorage clears on tab close, so new tabs get a new session.
 */
export function logSessionStart(): void {
  if (sessionStorage.getItem('telemetry_session_started')) return;
  sessionStorage.setItem('telemetry_session_started', '1');
  sessionStorage.setItem('telemetry_session_start_time', String(Date.now()));
  logEvent('session_start');
}

// Flush on page unload + send session_end via sendBeacon
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    void flush();
    const startTime = sessionStorage.getItem('telemetry_session_start_time');
    if (startTime) {
      const duration = Math.round((Date.now() - parseInt(startTime)) / 1000);
      const payload = {
        event_type: 'session_end',
        case_id: getCaseId(),
        data: { duration_seconds: duration },
      };
      fetch(`${API_BASE}/api/telemetry/event`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(noop);
    }
  });
}
