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

describe("phase5 health + flags", () => {
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    const repos = new Repositories(resetDbForTests());
    const engine = mockEngine();
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
      }),
      repos,
      engine,
      workerDeps,
    });
  });

  it("health exposes flags and worker metrics", async () => {
    const res = await app.request("/health");
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      status: string;
      flags: { llm_turns: boolean; miniapp_mutations: boolean };
      worker: { pending_jobs: number };
      funnel: Record<string, number>;
    };
    expect(body.status).toBe("ok");
    expect(body.flags.llm_turns).toBe(false);
    expect(body.flags.miniapp_mutations).toBe(false);
    expect(typeof body.worker.pending_jobs).toBe("number");
    expect(body.funnel).toBeDefined();
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
