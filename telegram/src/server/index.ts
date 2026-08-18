import { loadConfig } from "./config";
import { closeDb, getDb } from "../db/connection";
import { Repositories } from "../db/repositories";
import { EngineClient, repoTokenStore } from "../engine/client";
import { createApp } from "./app";
import { processQueue, type WorkerDeps } from "../jobs/worker";
import { createBot, createGrammyDelivery } from "../bot/handlers";
import { log } from "./logger";
import { Bot } from "grammy";
import { resolve } from "node:path";

/** MED-12: close SQLite on process exit */
function registerShutdown(): void {
  const shutdown = () => {
    try {
      closeDb();
    } catch {
      /* ignore */
    }
    process.exit(0);
  };
  process.once("SIGINT", shutdown);
  process.once("SIGTERM", shutdown);
}

async function main(): Promise<void> {
  const config = loadConfig();
  const db = getDb(config.TELEGRAM_DB_PATH);
  const repos = new Repositories(db);

  const recovery = repos.recoverOnStartup();
  log({
    msg: "startup_recovery",
    status: "ok",
    reset_to_pending: recovery.resetToPending,
    manual_retry: recovery.manual,
  });

  const engine = new EngineClient(
    { baseUrl: config.LANTERN_ENGINE_URL, timeoutMs: config.ENGINE_TIMEOUT_MS },
    repoTokenStore(repos),
  );

  let bot: Bot | null = null;
  if (config.TELEGRAM_MODE === "polling" || config.TELEGRAM_MODE === "webhook") {
    bot = new Bot(config.TELEGRAM_BOT_TOKEN);
  }

  const delivery = bot
    ? createGrammyDelivery(bot)
    : {
        async sendMessage() {
          throw new Error("bot not initialized");
        },
      };

  const assetsPath = resolve(process.cwd(), config.ASSETS_PATH);

  const workerDeps: WorkerDeps = {
    repos,
    engine,
    delivery,
    featureNewSessions: config.FEATURE_NEW_SESSIONS,
    featureLlmTurns: config.FEATURE_LLM_TURNS,
    assetsPath,
    publicUrl: config.TELEGRAM_PUBLIC_URL,
  };

  let workerRunning = false;
  let kickRequested = false;
  const kickWorker = () => {
    kickRequested = true;
    if (workerRunning) return;
    workerRunning = true;
    void (async () => {
      try {
        while (kickRequested) {
          kickRequested = false;
          await processQueue(workerDeps);
        }
      } catch (err) {
        log({
          level: "error",
          msg: "worker_error",
          status: "error",
          error_code: err instanceof Error ? err.message : "unknown",
        });
      } finally {
        workerRunning = false;
        if (kickRequested) kickWorker();
      }
    })();
  };

  registerShutdown();

  if (config.TELEGRAM_MODE === "polling") {
    log({ msg: "start_polling", status: "ok" });
    const pollBot = createBot(
      config.TELEGRAM_BOT_TOKEN,
      repos,
      workerDeps,
      config.FEATURE_NEW_SESSIONS,
    );
    await pollBot.start({
      onStart: () => log({ msg: "polling_active", status: "ok" }),
    });
    return;
  }

  const miniAppDir = resolve(process.cwd(), "dist/app");
  const app = createApp({
    config,
    repos,
    engine,
    workerDeps,
    kickWorker,
    miniAppDir,
  });

  // Retention off the health path (HIGH-07)
  const retentionMs = 15 * 60 * 1000;
  setInterval(() => {
    try {
      const purged = repos.purgeOldJobs(config.RETENTION_DAYS, 200);
      if (purged.jobs > 0 || purged.updates > 0) {
        log({
          msg: "retention_purge",
          status: "ok",
          purged_jobs: purged.jobs,
          purged_updates: purged.updates,
        });
      }
    } catch {
      /* ignore */
    }
  }, retentionMs);

  log({
    msg: "start_webhook_server",
    status: "ok",
    port: config.PORT,
  });

  Bun.serve({
    port: config.PORT,
    fetch: app.fetch,
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
