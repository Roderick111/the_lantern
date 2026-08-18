import type { Repositories } from "../db/repositories";
import type { EngineClient } from "../engine/client";
import { EngineError } from "../engine/client";
import type {
  InlineButton,
  JobPayload,
  JobRow,
  Language,
  StoredReply,
} from "../domain/types";
import { t } from "../i18n/strings";
import { log } from "../server/logger";
import { escapeHtml, splitMessage } from "../bot/format";
import { retryKeyboard, toTelegramMarkup } from "../bot/keyboards";
import { executeJob, type OpContext } from "./operations";
import { funnel } from "../server/metrics";

export interface TelegramDelivery {
  sendMessage(
    chatId: number,
    text: string,
    opts?: {
      replyMarkup?: ReturnType<typeof toTelegramMarkup>;
      parseMode?: "HTML";
    },
  ): Promise<void>;
  sendChatAction?(chatId: number, action: "typing"): Promise<void>;
  sendPhoto?(
    chatId: number,
    photo: { fileId?: string; path?: string },
    caption?: string,
  ): Promise<{ fileId?: string }>;
}

export interface WorkerDeps {
  repos: Repositories;
  engine: EngineClient;
  delivery: TelegramDelivery;
  featureNewSessions: boolean;
  featureLlmTurns: boolean;
  assetsPath?: string;
  publicUrl?: string;
}

/** Max users processed concurrently (per-user steps stay serialized). */
const USER_CONCURRENCY = 8;

async function mapPool(
  items: number[],
  limit: number,
  fn: (userId: number) => Promise<void>,
): Promise<void> {
  let i = 0;
  const n = Math.min(limit, items.length);
  if (n === 0) return;
  const workers = Array.from({ length: n }, async () => {
    while (i < items.length) {
      const idx = i++;
      const userId = items[idx];
      try {
        await fn(userId);
      } catch (err) {
        log({
          level: "error",
          msg: "worker_user_step_failed",
          telegram_user_id: userId,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  });
  await Promise.all(workers);
}

/**
 * Process durable jobs for all users with work.
 * One active mutation per user; arrival order via job id FIFO.
 * Users run in parallel (bounded); failures isolated per user.
 */
export async function processQueue(deps: WorkerDeps): Promise<void> {
  for (let round = 0; round < 100; round++) {
    const users = deps.repos.listUsersWithWork();
    if (users.length === 0) return;
    await mapPool(users, USER_CONCURRENCY, (userId) =>
      processUserStep(deps, userId),
    );
  }
}

export async function processUser(
  deps: WorkerDeps,
  telegramUserId: number,
): Promise<void> {
  await processUserStep(deps, telegramUserId);
}

async function processUserStep(
  deps: WorkerDeps,
  telegramUserId: number,
): Promise<void> {
  const retry = deps.repos.getDeliveryRetryJob(telegramUserId);
  if (retry) {
    await deliverJob(deps, retry);
    return;
  }

  const job = deps.repos.claimNextJobForUser(telegramUserId);
  if (!job) return;

  await runJob(deps, job);
}

function opContext(deps: WorkerDeps): OpContext {
  return {
    repos: deps.repos,
    engine: deps.engine,
    featureNewSessions: deps.featureNewSessions,
    featureLlmTurns: deps.featureLlmTurns,
    assetsPath: deps.assetsPath ?? "",
    publicUrl: deps.publicUrl,
  };
}

async function runJob(deps: WorkerDeps, job: JobRow): Promise<void> {
  const start = Date.now();
  const payload = JSON.parse(job.payload) as JobPayload;
  const user = deps.repos.getUser(job.telegram_user_id);
  const lang: Language = (user?.language as Language) ?? "en";

  try {
    void deps.delivery.sendChatAction?.(payload.chatId, "typing");

    const reply = await executeJob(opContext(deps), job);
    deps.repos.markEngineComplete(job.id, reply);
    await deliverJob(deps, deps.repos.getJob(job.id)!);

    log({
      msg: "job_done",
      update_id: job.update_id,
      request_id: job.request_id,
      operation: job.operation,
      duration_ms: Date.now() - start,
      status: "delivered",
    });
  } catch (err) {
    if (err instanceof EngineError && err.code === "timeout") {
      deps.repos.markNeedsManualRetry(job.id, "engine timeout after dispatch");
      funnel("engine_error", {
        telegram_user_id: job.telegram_user_id,
        request_id: job.request_id,
        operation: job.operation,
        status: "timeout",
      });
      try {
        await deps.delivery.sendMessage(
          payload.chatId,
          t(lang, "engine_unknown"),
          { replyMarkup: toTelegramMarkup(retryKeyboard(lang)) },
        );
      } catch {
        /* ignore */
      }
      log({
        level: "error",
        msg: "job_ambiguous",
        update_id: job.update_id,
        request_id: job.request_id,
        operation: job.operation,
        status: "needs_manual_retry",
      });
      return;
    }

    if (err instanceof EngineError && err.code === "conflict") {
      const reply: StoredReply = {
        reply_text: t(lang, "engine_conflict"),
        buttons: retryKeyboard(lang),
      };
      deps.repos.markEngineComplete(job.id, reply);
      await deliverJob(deps, deps.repos.getJob(job.id)!);
      return;
    }

    const fresh = deps.repos.getJob(job.id);
    if (fresh && fresh.engine_dispatched === 0) {
      // Pre-mutation failure: allow requeue once as complete error message
      const reply: StoredReply = {
        reply_text: t(lang, "engine_error"),
        buttons: retryKeyboard(lang),
      };
      deps.repos.markEngineComplete(job.id, reply);
      await deliverJob(deps, deps.repos.getJob(job.id)!);
    } else {
      deps.repos.markNeedsManualRetry(
        job.id,
        err instanceof Error ? err.message : "error",
      );
      try {
        await deps.delivery.sendMessage(
          payload.chatId,
          t(lang, "engine_unknown"),
          { replyMarkup: toTelegramMarkup(retryKeyboard(lang)) },
        );
      } catch {
        /* ignore */
      }
    }
    funnel("engine_error", {
      telegram_user_id: job.telegram_user_id,
      request_id: job.request_id,
      operation: job.operation,
      status: err instanceof EngineError ? err.code : "unknown",
    });
    log({
      level: "error",
      msg: "job_failed",
      update_id: job.update_id,
      request_id: job.request_id,
      operation: job.operation,
      status: "error",
      error_code: err instanceof EngineError ? err.code : "unknown",
    });
  }
}

async function deliverJob(deps: WorkerDeps, job: JobRow): Promise<void> {
  const payload = JSON.parse(job.payload) as JobPayload;
  let stored: StoredReply = { reply_text: "…" };
  if (job.engine_response) {
    try {
      stored = JSON.parse(job.engine_response) as StoredReply;
    } catch {
      stored = { reply_text: "…" };
    }
  }

  try {
    // Silent jobs (e.g. retry_job ack after requeue)
    const noText = !stored.reply_text.trim();
    const noNotices = !stored.notices?.length;
    const noPhoto = !stored.photo;
    if (noText && noNotices && noPhoto) {
      deps.repos.markDelivered(job.id);
      return;
    }

    // Notices first (evidence discovery) — trim after each send for retry safety
    if (stored.notices && stored.notices.length > 0) {
      const remaining = [...stored.notices];
      while (remaining.length > 0) {
        const n = remaining[0];
        await deps.delivery.sendMessage(payload.chatId, escapeHtml(n), {
          parseMode: "HTML",
        });
        remaining.shift();
        stored = { ...stored, notices: remaining.length ? remaining : undefined };
        deps.repos.updateEngineResponse(job.id, stored);
      }
    }

    // Photo once — skip if already receipted
    if (stored.photo && deps.delivery.sendPhoto) {
      const photo = stored.photo;
      const already =
        deps.repos.hasMediaReceipt(
          job.telegram_user_id,
          photo.kind,
          photo.mediaId,
        );
      if (!already) {
        try {
          const result = await deps.delivery.sendPhoto(
            payload.chatId,
            {
              fileId: photo.fileId,
              path: photo.path,
            },
            photo.caption,
          );
          deps.repos.recordMediaReceipt(
            job.telegram_user_id,
            photo.kind,
            photo.mediaId,
            result.fileId ?? photo.fileId ?? null,
          );
        } catch {
          // Still record receipt so we don't spam retries of missing assets
          deps.repos.recordMediaReceipt(
            job.telegram_user_id,
            photo.kind,
            photo.mediaId,
            photo.fileId ?? null,
          );
        }
      }
      stored = { ...stored, photo: undefined };
      deps.repos.updateEngineResponse(job.id, stored);
    }

    const chunks = splitMessage(stored.reply_text);
    for (let i = 0; i < chunks.length; i++) {
      const isLast = i === chunks.length - 1;
      const buttons: InlineButton[][] | undefined = isLast
        ? stored.buttons
        : undefined;
      await deps.delivery.sendMessage(
        payload.chatId,
        escapeHtml(chunks[i]),
        {
          parseMode: "HTML",
          replyMarkup: toTelegramMarkup(buttons),
        },
      );
    }

    deps.repos.markDelivered(job.id);
  } catch (err) {
    deps.repos.markDeliveryFailed(
      job.id,
      err instanceof Error ? err.message : "delivery failed",
    );
    funnel("delivery_error", {
      telegram_user_id: job.telegram_user_id,
      request_id: job.request_id,
      operation: job.operation,
    });
    log({
      level: "warn",
      msg: "delivery_failed",
      update_id: job.update_id,
      request_id: job.request_id,
      operation: job.operation,
      status: "failed_delivery",
    });
  }
}
