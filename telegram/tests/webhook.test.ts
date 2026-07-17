import { describe, it, expect, beforeEach } from "bun:test";
import { resetDbForTests } from "../src/db/connection";
import { Repositories } from "../src/db/repositories";
import { createApp } from "../src/server/app";
import { testConfig } from "../src/server/config";
import { handleTelegramUpdate, verifyWebhookSecret } from "../src/bot/webhook";
import type { EngineClient } from "../src/engine/client";
import type { WorkerDeps, TelegramDelivery } from "../src/jobs/worker";
import { processQueue, processUser } from "../src/jobs/worker";

function makeUpdate(
  updateId: number,
  userId: number,
  text: string,
  chatId = userId,
) {
  return {
    update_id: updateId,
    message: {
      message_id: 1,
      date: 1,
      text,
      from: { id: userId, is_bot: false, first_name: "T" },
      chat: { id: chatId, type: "private" },
    },
  };
}

describe("webhook secret", () => {
  it("rejects missing secret", () => {
    expect(verifyWebhookSecret(undefined, "secret-value-here")).toBe(false);
  });

  it("rejects wrong secret", () => {
    expect(verifyWebhookSecret("wrong-secret-xx", "secret-value-here")).toBe(
      false,
    );
  });

  it("accepts matching secret", () => {
    expect(verifyWebhookSecret("secret-value-here", "secret-value-here")).toBe(
      true,
    );
  });
});

describe("webhook route", () => {
  let repos: Repositories;
  let delivered: { chatId: number; text: string }[];
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    const db = resetDbForTests();
    repos = new Repositories(db);
    delivered = [];

    const delivery: TelegramDelivery = {
      async sendMessage(chatId, text) {
        delivered.push({ chatId, text });
      },
    };

    const engine = {
      async ensureSession() {
        return "tok";
      },
      async health() {
        return true;
      },
      async createSession() {
        return { player_id: "p", token: "tok" };
      },
    } as unknown as EngineClient;

    const workerDeps: WorkerDeps = {
      repos,
      engine,
      delivery,
      featureNewSessions: true,
      featureLlmTurns: true,
    };

    app = createApp({
      config: testConfig(),
      repos,
      engine,
      workerDeps,
    });
  });

  it("rejects invalid secret before body handling", async () => {
    const res = await app.request("/telegram/webhook", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Bot-Api-Secret-Token": "bad",
      },
      body: JSON.stringify(makeUpdate(1, 10, "/start")),
    });
    expect(res.status).toBe(401);
    expect(repos.hasUpdate(1)).toBe(false);
  });

  it("rejects missing secret", async () => {
    const res = await app.request("/telegram/webhook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(makeUpdate(2, 10, "/start")),
    });
    expect(res.status).toBe(401);
  });

  it("accepts valid secret and enqueues", async () => {
    const res = await app.request("/telegram/webhook", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Bot-Api-Secret-Token": testConfig().TELEGRAM_WEBHOOK_SECRET,
      },
      body: JSON.stringify(makeUpdate(3, 42, "/start")),
    });
    expect(res.status).toBe(200);
    // microtask worker may run
    await new Promise((r) => setTimeout(r, 20));
    expect(repos.hasUpdate(3)).toBe(true);
  });
});

describe("update dedupe and jobs", () => {
  let repos: Repositories;

  beforeEach(() => {
    repos = new Repositories(resetDbForTests());
  });

  it("duplicate update creates one job", () => {
    const update = makeUpdate(100, 1, "/start");
    const a = handleTelegramUpdate(repos, update, { featureNewSessions: true });
    const b = handleTelegramUpdate(repos, update, { featureNewSessions: true });
    expect(a.duplicate).toBe(false);
    expect(a.jobId).not.toBeNull();
    expect(b.duplicate).toBe(true);
    expect(b.jobId).toBeNull();
    expect(repos.countJobsByState("pending")).toBe(1);
  });
});

describe("worker pipeline", () => {
  let repos: Repositories;
  let delivered: { chatId: number; text: string }[];
  let engineSessionCalls: number;
  let workerDeps: WorkerDeps;

  beforeEach(() => {
    repos = new Repositories(resetDbForTests());
    delivered = [];
    engineSessionCalls = 0;

    const delivery: TelegramDelivery = {
      async sendMessage(chatId, text) {
        delivered.push({ chatId, text });
      },
    };

    const engine = {
      async ensureSession() {
        engineSessionCalls += 1;
        return "tok";
      },
      async health() {
        return true;
      },
      async createSession(uid: number) {
        engineSessionCalls += 1;
        repos.setPlayerCredentials(uid, `player-${uid}`, `token-${uid}`);
        return { player_id: `player-${uid}`, token: `token-${uid}` };
      },
    } as unknown as EngineClient;

    workerDeps = {
      repos,
      engine,
      delivery,
      featureNewSessions: true,
      featureLlmTurns: true,
    };
  });

  it("webhook -> job -> delivery for /start", async () => {
    handleTelegramUpdate(repos, makeUpdate(1, 7, "/start"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    expect(delivered.length).toBe(1);
    expect(delivered[0].chatId).toBe(7);
    expect(delivered[0].text.length).toBeGreaterThan(0);
    expect(repos.countJobsByState("delivered")).toBe(1);
  });

  it("serial per user: two messages run in order", async () => {
    handleTelegramUpdate(repos, makeUpdate(1, 9, "/start"), {
      featureNewSessions: true,
    });
    handleTelegramUpdate(repos, makeUpdate(2, 9, "hello"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    expect(delivered.length).toBe(2);
    const jobs = [
      repos.getJob(1),
      repos.getJob(2),
    ];
    expect(jobs[0]?.state).toBe("delivered");
    expect(jobs[1]?.state).toBe("delivered");
    expect(jobs[0]!.id).toBeLessThan(jobs[1]!.id);
  });

  it("different users can both complete", async () => {
    handleTelegramUpdate(repos, makeUpdate(10, 100, "/start"), {
      featureNewSessions: true,
    });
    handleTelegramUpdate(repos, makeUpdate(11, 200, "/start"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    expect(delivered.length).toBe(2);
    const chats = delivered.map((d) => d.chatId).sort();
    expect(chats).toEqual([100, 200]);
  });

  it("delivery failure keeps stored response and retries without second engine", async () => {
    let attempts = 0;
    const flaky: TelegramDelivery = {
      async sendMessage(chatId, text) {
        attempts += 1;
        if (attempts === 1) {
          throw new Error("telegram down");
        }
        delivered.push({ chatId, text });
      },
    };
    workerDeps = { ...workerDeps, delivery: flaky };

    // Seed job already engine_complete (engine done; only delivery left)
    repos.ensureUser(55, 55);
    const enq = repos.tryEnqueueUpdate({
      updateId: 50,
      telegramUserId: 55,
      chatId: 55,
      requestId: "tg-50",
      operation: "start_placeholder",
      payload: { chatId: 55, kind: "command_start" },
    });
    const jobId = enq.jobId!;
    repos.markEngineDispatched(jobId);
    repos.markEngineComplete(jobId, { reply_text: "stored reply" });
    const callsBefore = engineSessionCalls;

    // First step: delivery fails
    await processUser(workerDeps, 55);
    expect(repos.getJob(jobId)?.state).toBe("failed_delivery");
    expect(engineSessionCalls).toBe(callsBefore);

    // Second step: delivery succeeds from stored response
    await processUser(workerDeps, 55);
    expect(repos.getJob(jobId)?.state).toBe("delivered");
    expect(delivered.some((d) => d.text === "stored reply")).toBe(true);
    expect(engineSessionCalls).toBe(callsBefore);
  });

  it("restart: running not dispatched returns to pending", () => {
    handleTelegramUpdate(repos, makeUpdate(60, 61, "/start"), {
      featureNewSessions: true,
    });
    const claimed = repos.claimNextJobForUser(61);
    expect(claimed?.state).toBe("running");
    expect(claimed?.engine_dispatched).toBe(0);
    const r = repos.recoverOnStartup();
    expect(r.resetToPending).toBe(1);
    expect(repos.getJob(claimed!.id)?.state).toBe("pending");
  });

  it("restart: running dispatched never auto re-runs", () => {
    handleTelegramUpdate(repos, makeUpdate(70, 71, "/start"), {
      featureNewSessions: true,
    });
    const claimed = repos.claimNextJobForUser(71)!;
    repos.markEngineDispatched(claimed.id);
    const r = repos.recoverOnStartup();
    expect(r.manual).toBe(1);
    expect(repos.getJob(claimed.id)?.state).toBe("needs_manual_retry");
  });
});
