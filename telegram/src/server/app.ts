import { Hono } from "hono";
import { bodyLimit } from "hono/body-limit";
import { HTTPException } from "hono/http-exception";
import { serveStatic } from "hono/bun";
import type { AppConfig } from "./config";
import type { Repositories } from "../db/repositories";
import type { EngineClient } from "../engine/client";
import { handleTelegramUpdate, verifyWebhookSecret } from "../bot/webhook";
import type { WorkerDeps } from "../jobs/worker";
import { log } from "./logger";
import { t } from "../i18n/strings";
import type { Language } from "../domain/types";
import { createMiniAppRouter } from "../miniapp/routes";
import { collectHealthMetrics } from "./metrics";
import { getEngineHealth } from "./engine_health_cache";
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

  // MED-02: cap request bodies (Telegram updates + Mini App JSON)
  app.use("*", bodyLimit({ maxSize: 100 * 1024 }));

  // MED-11: structured error logging (preserve HTTPException status e.g. 413)
  app.onError((err, c) => {
    if (err instanceof HTTPException) {
      return err.getResponse();
    }
    log({
      level: "error",
      msg: "http_error",
      status: "error",
      path: c.req.path,
      error: err instanceof Error ? err.message : String(err),
    });
    return c.json({ ok: false }, 500);
  });

  // Make a root URL configured in BotFather recover gracefully to the Mini App.
  app.get("/", (c) => c.redirect("/app/"));

  // LOW-01: public liveness only — no queue/funnel disclosure
  app.get("/health", async (c) => {
    let dbOk = false;
    try {
      deps.repos.countJobsByState("pending");
      dbOk = true;
    } catch {
      dbOk = false;
    }

    // MED-01: cached engine probe (15s TTL)
    const engineOk = await getEngineHealth(() => deps.engine.health());
    const healthy = dbOk && engineOk;
    const status = healthy ? "ok" : "degraded";

    return c.json(
      {
        status,
        db: dbOk ? "ok" : "error",
        engine: engineOk ? "ok" : "error",
      },
      healthy ? 200 : 503,
    );
  });

  // LOW-01: ops metrics behind optional METRICS_TOKEN
  app.get("/metrics", (c) => {
    const token = deps.config.METRICS_TOKEN;
    if (!token) {
      return c.json({ ok: false }, 404);
    }
    const header = c.req.header("X-Metrics-Token");
    if (!header || header !== token) {
      return c.json({ ok: false }, 401);
    }

    let dbOk = false;
    try {
      deps.repos.countJobsByState("pending");
      dbOk = true;
    } catch {
      dbOk = false;
    }
    const metrics = dbOk ? collectHealthMetrics(deps.repos) : null;

    return c.json({
      status: "ok",
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
  } else {
    // MED-13: surface missing SPA build instead of silent 404
    log({
      level: "warn",
      msg: "miniapp_dist_missing",
      path: miniDir,
      status: "warn",
    });
  }

  return app;
}
