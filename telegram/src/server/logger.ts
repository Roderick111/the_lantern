/** Structured logs. Never log player prose, tokens, keys, or raw initData. */

const REDACT_PATTERNS: RegExp[] = [
  /bot\d+:[A-Za-z0-9_-]{20,}/gi,
  /\bsk-[A-Za-z0-9_-]{8,}/gi,
  /Bearer\s+[A-Za-z0-9._-]+/gi,
  /X-Player-Token["\s:=]+[A-Za-z0-9._-]+/gi,
  /player_token["\s:=]+[A-Za-z0-9._-]+/gi,
  /initData["\s:=]+[^\s"']+/gi,
];

const SECRET_KEYS = new Set([
  "token",
  "bot_token",
  "player_token",
  "api_key",
  "initdata",
  "init_data",
  "authorization",
  "secret",
  "password",
  "prose",
  "player_input",
  "question",
  "message",
  "text",
  "prompt",
]);

export function redactString(value: string): string {
  let out = value;
  for (const re of REDACT_PATTERNS) {
    out = out.replace(re, "[REDACTED]");
  }
  return out;
}

export function sanitizeFields(
  fields: Record<string, unknown>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(fields)) {
    const lower = key.toLowerCase();
    if (SECRET_KEYS.has(lower) || lower.includes("token") || lower.includes("secret")) {
      out[key] = "[REDACTED]";
      continue;
    }
    if (typeof value === "string") {
      out[key] = redactString(value);
    } else {
      out[key] = value;
    }
  }
  return out;
}

export type LogLevel = "info" | "warn" | "error" | "debug";

export interface LogEvent {
  level?: LogLevel;
  msg: string;
  update_id?: number;
  request_id?: string;
  operation?: string;
  duration_ms?: number;
  status?: string;
  [key: string]: unknown;
}

export function log(event: LogEvent): void {
  const { level = "info", msg, ...rest } = event;
  const payload = {
    ts: new Date().toISOString(),
    level,
    msg,
    ...sanitizeFields(rest),
  };
  const line = JSON.stringify(payload);
  if (level === "error") {
    console.error(line);
  } else if (level === "warn") {
    console.warn(line);
  } else {
    console.log(line);
  }
}
