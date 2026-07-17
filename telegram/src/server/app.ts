import { Hono } from "hono";
import { serveStatic } from "hono/bun";
import type { AppConfig } from "./config";
import type { Repositories } from "../db/repositories";
import type { EngineClient } from "../engine/client";
import { handleTelegramUpdate, verifyWebhookSecret } from "../bot/webhook";
import { processQueue, type WorkerDeps } from "../jobs/worker";
import { log } from "./logger";
import { t } from "../i18n/strings";
import type { Language } from "../domain/types";
import { createMiniAppRouter } from "../miniapp/routes";
import { collectHealthMetrics } from "./metrics";
import { resolve } from "node:path";
import { existsSync } from "node:fs";

export interface AppDeps {
  config: AppConfig;
  repos: Repositories;
  engine: EngineClient;
  workerDeps: WorkerDeps;
  kickWorker?: () => void;
  miniAppDir?: string;
}

export function createApp(deps: AppDeps): Hono {
  const app = new Hono();

  app.get("/health", async (c) => {
    let dbOk = false;
    try {
      deps.repos.countJobsByState("pending");
      dbOk = true;
    } catch {
      dbOk = false;
    }

    const engineOk = await deps.engine.health();
    const metrics = dbOk ? collectHealthMetrics(deps.repos) : null;
    const status = dbOk && engineOk ? "ok" : "degraded";

    // Opportunistic retention (bounded) — not a background scheduler
    if (dbOk && Math.random() < 0.05) {
      try {
        const purged = deps.repos.purgeOldJobs(deps.config.RETENTION_DAYS, 200);
        if (purged.jobs > 0 || purged.updates > 0) {
          log({
            msg: "retention_purge",
            status: "ok",
            purged_jobs: purged.jobs,
            purged_updates: purged.updates,
          });
        }
      } catch {
        /* ignore purge errors on health */
      }
    }

    return c.json({
      status,
      db: dbOk ? "ok" : "error",
      engine: engineOk ? "ok" : "error",
      flags: {
        new_sessions: deps.config.FEATURE_NEW_SESSIONS,
        llm_turns: deps.config.FEATURE_LLM_TURNS,
        miniapp_mutations: deps.config.FEATURE_MINIAPP_MUTATIONS,
      },
      worker: metrics
        ? {
            pending_jobs: metrics.pending_jobs,
            running_jobs: metrics.running_jobs,
            failed_delivery: metrics.failed_delivery,
            needs_manual_retry: metrics.needs_manual_retry,
            oldest_pending_age_sec: metrics.oldest_pending_age_sec,
          }
        : {
            pending_jobs: -1,
            running_jobs: -1,
          },
      // Aggregate counters only — no identities
      funnel: metrics?.counters ?? {},
    });
  });

  app.post("/telegram/webhook", async (c) => {
    const secret = c.req.header("X-Telegram-Bot-Api-Secret-Token");
    if (!verifyWebhookSecret(secret, deps.config.TELEGRAM_WEBHOOK_SECRET)) {
      log({ level: "warn", msg: "webhook_rejected", status: "bad_secret" });
      return c.json({ ok: false }, 401);
    }

    let update: Record<string, unknown>;
    try {
      update = (await c.req.json()) as Record<string, unknown>;
    } catch {
      return c.json({ ok: false }, 400);
    }

    const result = handleTelegramUpdate(deps.repos, update, {
      featureNewSessions: deps.config.FEATURE_NEW_SESSIONS,
    });

    if (result.accepted) {
      if (result.shouldAckQueued && result.chatId != null) {
        const lang: Language = result.language ?? "en";
        void deps.workerDeps.delivery
          .sendMessage(result.chatId, t(lang, "queued"))
          .catch(() => undefined);
      }
      deps.kickWorker?.();
      queueMicrotask(() => {
        void processQueue(deps.workerDeps).catch((err) => {
          log({
            level: "error",
            msg: "worker_error",
            status: "error",
            error_code: err instanceof Error ? err.message : "unknown",
          });
        });
      });
    }

    return c.json({ ok: true });
  });

  // Mini App API
  const mini = createMiniAppRouter({
    config: deps.config,
    repos: deps.repos,
    engine: deps.engine,
    workerDeps: deps.workerDeps,
    kickWorker: deps.kickWorker,
  });
  app.route("/miniapp", mini);

  // SPA static (built Vite output)
  const miniDir =
    deps.miniAppDir ?? resolve(process.cwd(), "dist/app");
  if (existsSync(miniDir)) {
    app.use(
      "/app/*",
      serveStatic({
        root: miniDir,
        rewriteRequestPath: (p) => p.replace(/^\/app/, "") || "/index.html",
      }),
    );
    app.get("/app", (c) => c.redirect("/app/"));
    app.get("/app/", serveStatic({ path: resolve(miniDir, "index.html") }));
  }

  return app;
}
