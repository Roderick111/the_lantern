import { createHash, timingSafeEqual } from "node:crypto";
import type { Repositories } from "../db/repositories";
import type { Language } from "../domain/types";
import { log } from "../server/logger";
import { extractUserAndOp } from "./route_update";

const ALLOWED_UPDATE_KEYS = new Set([
  "message",
  "callback_query",
  "my_chat_member",
]);

export interface EnqueueResult {
  accepted: boolean;
  duplicate: boolean;
  jobId: number | null;
  reason?: string;
  shouldAckQueued?: boolean;
  telegramUserId?: number;
  chatId?: number;
  language?: Language;
}

export function handleTelegramUpdate(
  repos: Repositories,
  update: Record<string, unknown>,
  opts: { featureNewSessions: boolean },
): EnqueueResult {
  const updateId = update.update_id;
  if (typeof updateId !== "number") {
    return { accepted: false, duplicate: false, jobId: null, reason: "no_update_id" };
  }

  const keys = Object.keys(update).filter((k) => k !== "update_id");
  const allowed = keys.some((k) => ALLOWED_UPDATE_KEYS.has(k));
  if (!allowed) {
    log({ msg: "update_ignored", update_id: updateId, status: "unsupported_type" });
    return { accepted: true, duplicate: false, jobId: null, reason: "unsupported_type" };
  }

  const extracted = extractUserAndOp(repos, update);
  if (!extracted) {
    return { accepted: true, duplicate: false, jobId: null, reason: "no_user" };
  }

  void opts.featureNewSessions;

  const result = repos.tryEnqueueUpdate({
    updateId,
    telegramUserId: extracted.telegramUserId,
    chatId: extracted.chatId,
    requestId: extracted.requestId,
    operation: extracted.operation,
    payload: extracted.payload,
  });

  if (!result.created) {
    log({ msg: "update_duplicate", update_id: updateId, status: "duplicate" });
    return { accepted: true, duplicate: true, jobId: null };
  }

  const user = repos.getUser(extracted.telegramUserId);
  const shouldAckQueued =
    result.jobId !== null &&
    repos.hasActiveWorkAhead(extracted.telegramUserId, result.jobId);

  log({
    msg: "update_enqueued",
    update_id: updateId,
    request_id: extracted.requestId,
    operation: extracted.operation,
    status: "pending",
  });

  return {
    accepted: true,
    duplicate: false,
    jobId: result.jobId,
    shouldAckQueued,
    telegramUserId: extracted.telegramUserId,
    chatId: extracted.chatId,
    language: (user?.language as Language) ?? "en",
  };
}

function sha256(s: string): Buffer {
  return createHash("sha256").update(s, "utf8").digest();
}

/** Constant-time secret compare (LOW-02). Length never early-exits via digest. */
export function verifyWebhookSecret(
  headerValue: string | undefined,
  expected: string,
): boolean {
  if (!headerValue || !expected) return false;
  return timingSafeEqual(sha256(headerValue), sha256(expected));
}
