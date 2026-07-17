/** Telegram Mini App initData validation + signed session cookie. */

import { createHmac, timingSafeEqual, randomBytes } from "node:crypto";

export const SESSION_COOKIE = "lantern_ma";
export const CSRF_HEADER = "x-csrf-token";
export const MAX_INIT_DATA_AGE_SEC = 86_400; // 24h
export const SESSION_TTL_SEC = 3_600; // 1h

export interface ValidatedTelegramUser {
  telegramUserId: number;
  authDate: number;
}

export interface SessionPayload {
  uid: number;
  exp: number;
  csrf: string;
}

/** Validate Telegram WebApp initData (HMAC-SHA-256). Never use initDataUnsafe. */
export function validateInitData(
  initData: string,
  botToken: string,
  nowSec = Math.floor(Date.now() / 1000),
  maxAgeSec = MAX_INIT_DATA_AGE_SEC,
): ValidatedTelegramUser {
  if (!initData || typeof initData !== "string") {
    throw new AuthError("missing_init_data", 401);
  }

  const params = new URLSearchParams(initData);
  const hash = params.get("hash");
  if (!hash) throw new AuthError("missing_hash", 401);

  const pairs: string[] = [];
  for (const [key, value] of params.entries()) {
    if (key === "hash") continue;
    pairs.push(`${key}=${value}`);
  }
  pairs.sort();
  const dataCheckString = pairs.join("\n");

  const secretKey = createHmac("sha256", "WebAppData").update(botToken).digest();
  const computed = createHmac("sha256", secretKey)
    .update(dataCheckString)
    .digest("hex");

  if (!equalHex(computed, hash)) {
    throw new AuthError("bad_hash", 401);
  }

  const authDateRaw = params.get("auth_date");
  const authDate = authDateRaw ? Number(authDateRaw) : NaN;
  if (!Number.isFinite(authDate)) throw new AuthError("bad_auth_date", 401);
  if (nowSec - authDate > maxAgeSec) throw new AuthError("stale_auth_date", 401);
  if (authDate > nowSec + 60) throw new AuthError("future_auth_date", 401);

  const userRaw = params.get("user");
  if (!userRaw) throw new AuthError("missing_user", 401);
  let user: { id?: number };
  try {
    user = JSON.parse(userRaw) as { id?: number };
  } catch {
    throw new AuthError("bad_user", 401);
  }
  if (!user.id || typeof user.id !== "number") {
    throw new AuthError("bad_user_id", 401);
  }

  return { telegramUserId: user.id, authDate };
}

export function createSession(
  telegramUserId: number,
  secret: string,
  ttlSec = SESSION_TTL_SEC,
): { cookieValue: string; csrf: string; exp: number } {
  const exp = Math.floor(Date.now() / 1000) + ttlSec;
  const csrf = randomBytes(16).toString("hex");
  const payload: SessionPayload = { uid: telegramUserId, exp, csrf };
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const sig = sign(body, secret);
  return { cookieValue: `${body}.${sig}`, csrf, exp };
}

export function parseSession(
  cookieValue: string | undefined,
  secret: string,
  nowSec = Math.floor(Date.now() / 1000),
): SessionPayload {
  if (!cookieValue) throw new AuthError("no_session", 401);
  const [body, sig] = cookieValue.split(".");
  if (!body || !sig) throw new AuthError("bad_session", 401);
  const expected = sign(body, secret);
  if (!equalHex(expected, sig)) throw new AuthError("bad_session_sig", 401);
  let payload: SessionPayload;
  try {
    payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8")) as SessionPayload;
  } catch {
    throw new AuthError("bad_session_body", 401);
  }
  if (!payload.uid || !payload.exp || !payload.csrf) {
    throw new AuthError("bad_session_fields", 401);
  }
  if (payload.exp < nowSec) throw new AuthError("session_expired", 401);
  return payload;
}

export function checkOrigin(
  origin: string | undefined,
  host: string | undefined,
  publicUrl: string,
): boolean {
  let expectedHost: string;
  try {
    expectedHost = new URL(publicUrl).host;
  } catch {
    return false;
  }
  if (origin) {
    try {
      return new URL(origin).host === expectedHost;
    } catch {
      return false;
    }
  }
  // Some Telegram clients omit Origin; fall back to Host
  if (host) {
    return host.split(":")[0] === expectedHost.split(":")[0] || host === expectedHost;
  }
  return false;
}

export function sessionCookieHeader(
  value: string,
  maxAge: number,
  secure: boolean,
): string {
  const parts = [
    `${SESSION_COOKIE}=${value}`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
    `Max-Age=${maxAge}`,
  ];
  if (secure) parts.push("Secure");
  return parts.join("; ");
}

export function clearSessionCookieHeader(secure: boolean): string {
  return sessionCookieHeader("", 0, secure);
}

function sign(body: string, secret: string): string {
  return createHmac("sha256", secret).update(body).digest("base64url");
}

function equalHex(a: string, b: string): boolean {
  try {
    const ba = Buffer.from(a);
    const bb = Buffer.from(b);
    if (ba.length !== bb.length) return false;
    return timingSafeEqual(ba, bb);
  } catch {
    return false;
  }
}

export class AuthError extends Error {
  constructor(
    public readonly code: string,
    public readonly status: number,
  ) {
    super(code);
    this.name = "AuthError";
  }
}

/** Build initData string for tests. */
export function signInitDataForTests(
  fields: Record<string, string>,
  botToken: string,
): string {
  const params = new URLSearchParams(fields);
  const pairs: string[] = [];
  for (const [key, value] of params.entries()) {
    pairs.push(`${key}=${value}`);
  }
  pairs.sort();
  const dataCheckString = pairs.join("\n");
  const secretKey = createHmac("sha256", "WebAppData").update(botToken).digest();
  const hash = createHmac("sha256", secretKey).update(dataCheckString).digest("hex");
  params.set("hash", hash);
  return params.toString();
}
