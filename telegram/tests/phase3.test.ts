import { describe, it, expect, beforeEach } from "bun:test";
import { resetDbForTests } from "../src/db/connection";
import { Repositories } from "../src/db/repositories";
import { handleTelegramUpdate } from "../src/bot/webhook";
import { processQueue, type TelegramDelivery, type WorkerDeps } from "../src/jobs/worker";
import type { EngineClient } from "../src/engine/client";
import { DAILY_LLM_LIMIT } from "../src/domain/types";
import { escapeHtml, splitMessage } from "../src/bot/format";
import { parseCallback, encodeLang, encodeBegin, encodeWitness, encodeEndWitness, encodeMove } from "../src/domain/callbacks";
import { assertCatalogParity } from "../src/i18n/strings";

function makeUpdate(updateId: number, userId: number, text: string, chatId = userId) {
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

function makeCallback(
  updateId: number,
  userId: number,
  data: string,
  chatId = userId,
) {
  return {
    update_id: updateId,
    callback_query: {
      id: "cq1",
      from: { id: userId, is_bot: false, first_name: "T" },
      data,
      message: {
        message_id: 1,
        date: 1,
        chat: { id: chatId, type: "private" },
      },
    },
  };
}

function mockEngine(calls: string[]): EngineClient {
  return {
    async ensureSession() {
      return "tok";
    },
    async health() {
      return true;
    },
    async createSession(uid: number) {
      calls.push(`session:${uid}`);
      return { player_id: `p-${uid}`, token: `t-${uid}` };
    },
    async investigate(
      _uid: number,
      body: { player_input: string; request_id?: string },
    ) {
      calls.push(`investigate:${body.player_input}:${body.request_id}`);
      return {
        narrator_response: `Narrator: ${body.player_input}`,
        new_evidence: body.player_input.includes("clue") ? ["dropped_badge"] : [],
        evidence_names: { dropped_badge: "Elena's Badge" },
        already_discovered: false,
      };
    },
    async interrogate(
      _uid: number,
      body: { witness_id: string; question: string },
    ) {
      calls.push(`interrogate:${body.witness_id}:${body.question}`);
      return {
        response: `Witness ${body.witness_id}: ${body.question}`,
        trust: 50,
        trust_delta: 0,
        secrets_revealed: [],
        secret_texts: {},
      };
    },
    async presentEvidence(
      _uid: number,
      body: { witness_id: string; evidence_id: string },
    ) {
      calls.push(`present:${body.witness_id}:${body.evidence_id}`);
      return {
        response: `Presented ${body.evidence_id}`,
        trust: 55,
        trust_delta: 5,
        secrets_revealed: [],
        secret_texts: {},
      };
    },
    async changeLocation(
      _uid: number,
      _caseId: string,
      body: { location_id: string },
    ) {
      calls.push(`move:${body.location_id}`);
      return {
        success: true,
        location: {
          id: body.location_id,
          name: body.location_id,
          description: "desc",
        },
      };
    },
    async updateSettings(_uid: number, body: { language?: string }) {
      calls.push(`settings:${body.language}`);
      return { success: true, message: "ok" };
    },
    async completeBriefing() {
      calls.push("briefing");
      return { success: true };
    },
    async resetCase() {
      calls.push("reset");
      return { success: true, message: "reset" };
    },
    async submitVerdict(
      _uid: number,
      body: { accused_suspect_id: string },
    ) {
      calls.push(`verdict:${body.accused_suspect_id}`);
      return {
        correct: body.accused_suspect_id === "wisp",
        attempts_remaining: 9,
        case_solved: body.accused_suspect_id === "wisp",
        mentor_feedback: {
          analysis: "analysis",
          fallacies_detected: [],
          score: 80,
          quality: "good",
          critique: "c",
          praise: "p",
          hint: null,
        },
      };
    },
    async snapshot() {
      return {
        case_id: "case_001",
        current_location: "library",
        visited_locations: ["library"],
        discovered_evidence: ["dropped_badge"],
        briefing_completed: true,
        language: "en",
        save_revision: 1,
        available_witnesses: [{ id: "elena", name: "Elena Marsh" }],
        verdict_attempts_remaining: 10,
        case_solved: false,
      };
    },
  } as unknown as EngineClient;
}

describe("phase3 routing", () => {
  let repos: Repositories;
  let delivered: { chatId: number; text: string }[];
  let engineCalls: string[];
  let workerDeps: WorkerDeps;

  beforeEach(() => {
    repos = new Repositories(resetDbForTests());
    delivered = [];
    engineCalls = [];
    const delivery: TelegramDelivery = {
      async sendMessage(chatId, text) {
        delivered.push({ chatId, text });
      },
    };
    workerDeps = {
      repos,
      engine: mockEngine(engineCalls),
      delivery,
      featureNewSessions: true,
      featureLlmTurns: true,
      assetsPath: "",
    };
  });

  it("fresh EN onboarding: language -> begin", async () => {
    handleTelegramUpdate(repos, makeUpdate(1, 1, "/start"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    expect(delivered[0].text).toContain("Choose language");

    handleTelegramUpdate(
      repos,
      makeCallback(2, 1, encodeLang("en")),
      { featureNewSessions: true },
    );
    await processQueue(workerDeps);
    expect(repos.getUser(1)?.language).toBe("en");
    expect(repos.getSession(1)?.onboarding_step).toBe("need_begin");
    expect(engineCalls.some((c) => c.startsWith("settings:en"))).toBe(true);

    handleTelegramUpdate(
      repos,
      makeCallback(3, 1, encodeBegin()),
      { featureNewSessions: true },
    );
    await processQueue(workerDeps);
    expect(repos.getSession(1)?.onboarding_step).toBe("active");
    expect(engineCalls).toContain("briefing");
    expect(delivered.at(-1)?.text).toMatch(/enter the case|investigation/i);
  });

  it("fresh RU onboarding", async () => {
    handleTelegramUpdate(repos, makeUpdate(10, 2, "/start"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    handleTelegramUpdate(
      repos,
      makeCallback(11, 2, encodeLang("ru")),
      { featureNewSessions: true },
    );
    await processQueue(workerDeps);
    expect(repos.getUser(2)?.language).toBe("ru");
    expect(delivered.at(-1)?.text).toMatch(/язык|Расследован|стеллаж/i);
  });

  it("/start resumes rather than resets", async () => {
    repos.ensureUser(3, 3);
    repos.setOnboardingStep(3, "active");
    repos.setPlayerCredentials(3, "p3", "t3");
    handleTelegramUpdate(repos, makeUpdate(20, 3, "/start"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    expect(engineCalls).not.toContain("reset");
    expect(delivered.at(-1)?.text).toMatch(/Welcome back|С возвращением/i);
  });

  it("mode routes identical text to correct endpoint", async () => {
    repos.ensureUser(4, 4);
    repos.setOnboardingStep(4, "active");
    repos.setPlayerCredentials(4, "p4", "t4");

    handleTelegramUpdate(repos, makeUpdate(30, 4, "look around"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    expect(engineCalls.some((c) => c.startsWith("investigate:look around"))).toBe(
      true,
    );

    handleTelegramUpdate(
      repos,
      makeCallback(31, 4, encodeWitness("elena")),
      { featureNewSessions: true },
    );
    await processQueue(workerDeps);
    expect(repos.getSession(4)?.mode).toBe("witness");
    expect(repos.getSession(4)?.witness_id).toBe("elena");

    handleTelegramUpdate(repos, makeUpdate(32, 4, "where were you"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    expect(
      engineCalls.some((c) => c.startsWith("interrogate:elena:where were you")),
    ).toBe(true);

    handleTelegramUpdate(
      repos,
      makeCallback(33, 4, encodeEndWitness()),
      { featureNewSessions: true },
    );
    await processQueue(workerDeps);
    expect(repos.getSession(4)?.mode).toBe("investigation");

    handleTelegramUpdate(repos, makeUpdate(34, 4, "look around"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    const inv = engineCalls.filter((c) => c.startsWith("investigate:"));
    expect(inv.length).toBe(2);
  });

  it("rites pass through unchanged", async () => {
    repos.ensureUser(5, 5);
    repos.setOnboardingStep(5, "active");
    repos.setPlayerCredentials(5, "p5", "t5");
    const rite = "I cast the Rite of Clarity over the frost";
    handleTelegramUpdate(repos, makeUpdate(40, 5, rite), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    expect(engineCalls.some((c) => c.includes(rite))).toBe(true);
  });

  it("navigation move calls change-location", async () => {
    repos.ensureUser(6, 6);
    repos.setOnboardingStep(6, "active");
    repos.setPlayerCredentials(6, "p6", "t6");
    handleTelegramUpdate(
      repos,
      makeCallback(50, 6, encodeMove("kitchens")),
      { featureNewSessions: true },
    );
    await processQueue(workerDeps);
    expect(engineCalls).toContain("move:kitchens");
  });

  it("evidence discovery notice", async () => {
    repos.ensureUser(7, 7);
    repos.setOnboardingStep(7, "active");
    repos.setPlayerCredentials(7, "p7", "t7");
    handleTelegramUpdate(repos, makeUpdate(60, 7, "find clue here"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    const texts = delivered.map((d) => d.text).join("\n");
    expect(texts).toMatch(/Evidence discovered|Elena/i);
  });

  it("reset confirm/cancel", async () => {
    repos.ensureUser(8, 8);
    repos.setOnboardingStep(8, "active");
    repos.setPlayerCredentials(8, "p8", "t8");

    handleTelegramUpdate(repos, makeUpdate(70, 8, "/reset"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    expect(delivered.at(-1)?.text).toMatch(/Reset case|Сбросить/i);

    handleTelegramUpdate(
      repos,
      makeCallback(71, 8, "reset:no"),
      { featureNewSessions: true },
    );
    await processQueue(workerDeps);
    expect(repos.getSession(8)?.onboarding_step).toBe("active");

    handleTelegramUpdate(
      repos,
      makeCallback(72, 8, "reset:yes"),
      { featureNewSessions: true },
    );
    await processQueue(workerDeps);
    expect(engineCalls).toContain("reset");
    expect(repos.getSession(8)?.onboarding_step).toBe("need_begin");
  });

  it("reset re-applies gateway language to engine", async () => {
    repos.ensureUser(88, 88);
    repos.setLanguage(88, "ru");
    repos.setOnboardingStep(88, "active");
    repos.setPlayerCredentials(88, "p88", "t88");

    handleTelegramUpdate(
      repos,
      makeCallback(720, 88, "reset:yes"),
      { featureNewSessions: true },
    );
    await processQueue(workerDeps);
    expect(engineCalls).toContain("reset");
    expect(engineCalls).toContain("settings:ru");
    expect(repos.getSession(88)?.onboarding_step).toBe("need_begin");
    expect(repos.getUser(88)?.language).toBe("ru");
  });

  it("daily cap blocks 41st LLM turn", async () => {
    repos.ensureUser(9, 9);
    repos.setOnboardingStep(9, "active");
    repos.setPlayerCredentials(9, "p9", "t9");
    for (let i = 0; i < DAILY_LLM_LIMIT; i++) {
      repos.incrementLlmTurns(9);
    }
    expect(repos.getLlmTurns(9)).toBe(40);
    handleTelegramUpdate(repos, makeUpdate(80, 9, "one more look"), {
      featureNewSessions: true,
    });
    await processQueue(workerDeps);
    expect(engineCalls.some((c) => c.startsWith("investigate:"))).toBe(false);
    expect(delivered.at(-1)?.text).toMatch(/limit|лимит/i);
  });

  it("long reply splits; buttons only on final chunk concept", () => {
    const long = Array.from({ length: 50 }, (_, i) => `Paragraph ${i}.`).join(
      "\n\n",
    );
    const chunks = splitMessage(long, 200);
    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.every((c) => c.length <= 200)).toBe(true);
  });

  it("escape html", () => {
    expect(escapeHtml("a<b>&c")).toBe("a&lt;b&gt;&amp;c");
  });

  it("callback parse roundtrip", () => {
    expect(parseCallback(encodeLang("ru"))).toEqual({
      type: "lang",
      language: "ru",
    });
    expect(parseCallback(encodeWitness("wisp"))).toEqual({
      type: "wit",
      witnessId: "wisp",
    });
  });

  it("i18n parity still holds", () => {
    expect(() => assertCatalogParity()).not.toThrow();
  });
});

describe("phase3 verdict mock flow", () => {
  it("submit verdict after suspect + reasoning", async () => {
    const repos = new Repositories(resetDbForTests());
    const engineCalls: string[] = [];
    const delivered: { chatId: number; text: string }[] = [];
    const workerDeps: WorkerDeps = {
      repos,
      engine: mockEngine(engineCalls),
      delivery: {
        async sendMessage(chatId, text) {
          delivered.push({ chatId, text });
        },
      },
      featureNewSessions: true,
      featureLlmTurns: true,
    };

    repos.ensureUser(100, 100);
    repos.setOnboardingStep(100, "active");
    repos.setPlayerCredentials(100, "p100", "t100");
    repos.setPendingJson(100, {
      kind: "awaiting_verdict_reasoning",
      accused_suspect_id: "wisp",
      evidence_cited: ["dropped_badge"],
    });

    handleTelegramUpdate(
      repos,
      makeUpdate(200, 100, "Wisp was ordered to protect Cassian"),
      { featureNewSessions: true },
    );
    await processQueue(workerDeps);
    expect(engineCalls.some((c) => c.startsWith("verdict:wisp"))).toBe(true);
    expect(delivered.at(-1)?.text).toMatch(/Correct|analysis/i);
  });
});
