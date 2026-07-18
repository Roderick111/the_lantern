import { describe, it, expect, beforeEach } from "bun:test";
import { resetDbForTests } from "../src/db/connection";
import { Repositories } from "../src/db/repositories";
import { createApp } from "../src/server/app";
import { testConfig } from "../src/server/config";
import type { EngineClient } from "../src/engine/client";
import type { WorkerDeps } from "../src/jobs/worker";
import {
  createSession,
  parseSession,
  signInitDataForTests,
  validateInitData,
  SESSION_COOKIE,
  AuthError,
  checkOrigin,
} from "../src/miniapp/auth";
import { assertCaseCatalogParity } from "../src/i18n/case_catalog";
import { assertMiniUiParity } from "../src/i18n/miniapp_ui";
import { VerdictRequestSchema } from "../src/miniapp/schemas";

const botToken = "123456:TEST-Token-For-Tests";
const secret = "test-miniapp-session-secret";
const publicUrl = "https://bot.thelantern.institute";

function makeInitData(overrides: Record<string, string> = {}): string {
  const authDate = String(Math.floor(Date.now() / 1000));
  return signInitDataForTests(
    {
      auth_date: authDate,
      user: JSON.stringify({ id: 42, first_name: "T" }),
      ...overrides,
    },
    botToken,
  );
}

function mockEngine(): EngineClient {
  return {
    async ensureSession() {
      return "tok";
    },
    async health() {
      return true;
    },
    async createSession(uid: number) {
      return { player_id: `p-${uid}`, token: `t-${uid}` };
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
        available_witnesses: [
          { id: "elena", name: "Elena Marsh" },
          { id: "wisp", name: "Wisp" },
        ],
        verdict_attempts_remaining: 10,
        case_solved: false,
      };
    },
    async submitVerdict(
      _uid: number,
      body: { accused_suspect_id: string },
    ) {
      return {
        correct: body.accused_suspect_id === "wisp",
        attempts_remaining: 9,
        case_solved: body.accused_suspect_id === "wisp",
        mentor_feedback: {
          analysis: "a",
          fallacies_detected: [],
          score: 1,
          quality: "ok",
          critique: "c",
          praise: "p",
          hint: null,
        },
        reveal: null,
      };
    },
  } as unknown as EngineClient;
}

describe("initData validation", () => {
  it("accepts valid initData", () => {
    const init = makeInitData();
    const u = validateInitData(init, botToken);
    expect(u.telegramUserId).toBe(42);
  });

  it("rejects tampered hash", () => {
    const init = makeInitData() + "x";
    expect(() => validateInitData(init, botToken)).toThrow(AuthError);
  });

  it("rejects missing hash", () => {
    expect(() =>
      validateInitData("auth_date=1&user=%7B%22id%22%3A1%7D", botToken),
    ).toThrow(AuthError);
  });

  it("rejects stale auth_date", () => {
    const old = String(Math.floor(Date.now() / 1000) - 200_000);
    const init = makeInitData({ auth_date: old });
    expect(() => validateInitData(init, botToken)).toThrow(AuthError);
  });
});

describe("session cookie", () => {
  it("roundtrips and expires", () => {
    const s = createSession(7, secret, 60);
    const p = parseSession(s.cookieValue, secret);
    expect(p.uid).toBe(7);
    expect(p.csrf).toBe(s.csrf);
    expect(() =>
      parseSession(s.cookieValue, secret, Math.floor(Date.now() / 1000) + 120),
    ).toThrow(AuthError);
  });

  it("rejects bad signature", () => {
    const s = createSession(1, secret);
    expect(() => parseSession(s.cookieValue + "x", secret)).toThrow(AuthError);
  });
});

describe("origin check", () => {
  it("accepts matching origin", () => {
    expect(
      checkOrigin(publicUrl, "bot.thelantern.institute", publicUrl),
    ).toBe(true);
  });
  it("rejects wrong origin", () => {
    expect(checkOrigin("https://evil.example", "evil.example", publicUrl)).toBe(
      false,
    );
  });
});

describe("miniapp HTTP", () => {
  let repos: Repositories;
  let app: ReturnType<typeof createApp>;
  let csrf: string;
  let cookie: string;

  beforeEach(async () => {
    repos = new Repositories(resetDbForTests());
    const engine = mockEngine();
    const workerDeps: WorkerDeps = {
      repos,
      engine,
      delivery: { async sendMessage() {} },
      featureNewSessions: true,
      featureLlmTurns: true,
      publicUrl,
    };
    app = createApp({
      config: testConfig({
        TELEGRAM_BOT_TOKEN: botToken,
        MINIAPP_SESSION_SECRET: secret,
        TELEGRAM_PUBLIC_URL: publicUrl,
      }),
      repos,
      engine,
      workerDeps,
    });

    const res = await app.request("/miniapp/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ initData: makeInitData() }),
    });
    expect(res.status).toBe(200);
    const body = (await res.json()) as { csrf: string };
    csrf = body.csrf;
    const setCookie = res.headers.get("set-cookie") ?? "";
    cookie = setCookie.split(";")[0];
    expect(cookie.startsWith(`${SESSION_COOKIE}=`)).toBe(true);
  });

  it("redirects the gateway root to the Mini App", async () => {
    const res = await app.request("/");
    expect(res.status).toBe(302);
    expect(res.headers.get("location")).toBe("/app/");
  });

  it("rejects casebook without session", async () => {
    const res = await app.request("/miniapp/casebook");
    expect(res.status).toBe(401);
  });

  it("serves casebook with session", async () => {
    const res = await app.request("/miniapp/casebook", {
      headers: { Cookie: cookie },
    });
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      case_id: string;
      title: string;
      evidence_count: number;
    };
    expect(body.case_id).toBe("case_001");
    expect(body.evidence_count).toBe(1);
    expect(body.title.length).toBeGreaterThan(0);
  });

  it("rejects mutation without csrf", async () => {
    const res = await app.request("/miniapp/witnesses/elena/select", {
      method: "POST",
      headers: {
        Cookie: cookie,
        Origin: publicUrl,
      },
    });
    expect(res.status).toBe(403);
  });

  it("rejects mutation with bad origin", async () => {
    const res = await app.request("/miniapp/witnesses/elena/select", {
      method: "POST",
      headers: {
        Cookie: cookie,
        Origin: "https://evil.example",
        "x-csrf-token": csrf,
      },
    });
    expect(res.status).toBe(403);
  });

  it("selects witness with csrf+origin", async () => {
    const res = await app.request("/miniapp/witnesses/elena/select", {
      method: "POST",
      headers: {
        Cookie: cookie,
        Origin: publicUrl,
        "x-csrf-token": csrf,
      },
    });
    expect(res.status).toBe(200);
    // Mode set only after worker runs select_witness (no optimistic split-brain).
    expect(repos.getSession(42)?.mode).not.toBe("witness");
    expect(repos.getSession(42)?.witness_id).toBeNull();
  });

  it("submits verdict with stable request_id", async () => {
    const res = await app.request("/miniapp/verdict", {
      method: "POST",
      headers: {
        Cookie: cookie,
        Origin: publicUrl,
        "x-csrf-token": csrf,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        accused_suspect_id: "wisp",
        evidence_cited: ["dropped_badge"],
        reasoning: "Kitchen log and frostbite and order.",
        request_id: "ma-verdict-stable-1",
      }),
    });
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      ok: true;
      queued: boolean;
      request_id: string;
      close: true;
    };
    expect(body.ok).toBe(true);
    expect(body.queued).toBe(true);
    expect(body.request_id).toBe("ma-verdict-stable-1");
    expect(body.close).toBe(true);
  });

  it("rejects verdict extra fields", () => {
    const r = VerdictRequestSchema.safeParse({
      accused_suspect_id: "wisp",
      reasoning: "x",
      request_id: "r1",
      secret: "nope",
    });
    expect(r.success).toBe(false);
  });
});

describe("catalog parity", () => {
  it("case catalog en/ru complete", () => {
    expect(() => assertCaseCatalogParity()).not.toThrow();
  });
  it("mini ui en/ru complete", () => {
    expect(() => assertMiniUiParity()).not.toThrow();
  });
});
