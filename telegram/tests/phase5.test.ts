import { describe, it, expect, beforeEach } from "bun:test";
import { resetDbForTests } from "../src/db/connection";
import { Repositories } from "../src/db/repositories";
import { createApp } from "../src/server/app";
import { testConfig } from "../src/server/config";
import type { EngineClient } from "../src/engine/client";
import type { WorkerDeps } from "../src/jobs/worker";
import { bump, funnel, getCounters } from "../src/server/metrics";

function mockEngine(): EngineClient {
  return {
    async ensureSession() {
      return "tok";
    },
    async health() {
      return true;
    },
  } as unknown as EngineClient;
}

describe("phase5 retention", () => {
  it("purges old terminal jobs and updates", () => {
    const repos = new Repositories(resetDbForTests());
    repos.ensureUser(1, 1);
    const enq = repos.tryEnqueueUpdate({
      updateId: 9001,
      telegramUserId: 1,
      chatId: 1,
      requestId: "old-1",
      operation: "local_reply",
      payload: { chatId: 1, kind: "command_help" },
    });
    const id = enq.jobId!;
    repos.markEngineComplete(id, { reply_text: "x" });
    repos.markDelivered(id);

    // Backdate via private db handle
    const db = (repos as unknown as {
      db: { run: (sql: string, params?: unknown[]) => void };
    }).db;
    db.run(`UPDATE jobs SET updated_at = '2020-01-01T00:00:00.000Z' WHERE id = ?`, [
      id,
    ]);
    db.run(
      `UPDATE updates SET received_at = '2020-01-01T00:00:00.000Z' WHERE update_id = 9001`,
    );

    const r = repos.purgeOldJobs(7, 100);
    expect(r.jobs).toBe(1);
    expect(repos.getJob(id)).toBeNull();
    expect(repos.hasUpdate(9001)).toBe(false);
  });
});

describe("phase5 health + metrics", () => {
  let app: ReturnType<typeof createApp>;
  let healthCalls: number;

  beforeEach(() => {
    healthCalls = 0;
    const repos = new Repositories(resetDbForTests());
    const engine = {
      async ensureSession() {
        return "tok";
      },
      async health() {
        healthCalls += 1;
        return true;
      },
    } as unknown as EngineClient;
    const workerDeps: WorkerDeps = {
      repos,
      engine,
      delivery: { async sendMessage() {} },
      featureNewSessions: true,
      featureLlmTurns: false,
    };
    app = createApp({
      config: testConfig({
        FEATURE_LLM_TURNS: false,
        FEATURE_MINIAPP_MUTATIONS: false,
        METRICS_TOKEN: "metrics-secret-token",
      }),
      repos,
      engine,
      workerDeps,
    });
  });

  it("health is slim liveness only", async () => {
    const { resetEngineHealthCache } = await import(
      "../src/server/engine_health_cache"
    );
    resetEngineHealthCache();
    healthCalls = 0;

    const res = await app.request("/health");
    expect(res.status).toBe(200);
    const body = (await res.json()) as Record<string, unknown>;
    expect(body.status).toBe("ok");
    expect(body.db).toBe("ok");
    expect(body.engine).toBe("ok");
    expect(body.funnel).toBeUndefined();
    expect(body.worker).toBeUndefined();
    expect(body.flags).toBeUndefined();
  });

  it("caches engine health within TTL", async () => {
    const { resetEngineHealthCache } = await import(
      "../src/server/engine_health_cache"
    );
    resetEngineHealthCache();
    healthCalls = 0;

    await app.request("/health");
    await app.request("/health");
    expect(healthCalls).toBe(1);
  });

  it("metrics requires token when configured", async () => {
    const denied = await app.request("/metrics");
    expect(denied.status).toBe(401);

    const ok = await app.request("/metrics", {
      headers: { "X-Metrics-Token": "metrics-secret-token" },
    });
    expect(ok.status).toBe(200);
    const body = (await ok.json()) as {
      flags: { llm_turns: boolean };
      worker: { pending_jobs: number };
      funnel: Record<string, number>;
    };
    expect(body.flags.llm_turns).toBe(false);
    expect(typeof body.worker.pending_jobs).toBe("number");
    expect(body.funnel).toBeDefined();
  });

  it("metrics 404 when token unset", async () => {
    const repos = new Repositories(resetDbForTests());
    const engine = mockEngine();
    const bare = createApp({
      config: testConfig({ METRICS_TOKEN: undefined }),
      repos,
      engine,
      workerDeps: {
        repos,
        engine,
        delivery: { async sendMessage() {} },
        featureNewSessions: true,
        featureLlmTurns: true,
      },
    });
    const res = await bare.request("/metrics");
    expect(res.status).toBe(404);
  });
});

describe("phase5 funnel counters", () => {
  it("bumps without prose fields", () => {
    const before = getCounters().funnel_daily_cap ?? 0;
    funnel("daily_cap", { telegram_user_id: 12345, operation: "investigate" });
    expect(getCounters().funnel_daily_cap).toBe(before + 1);
    bump("custom_metric", 2);
    expect(getCounters().custom_metric).toBeGreaterThanOrEqual(2);
  });
});
