import { Hono } from "hono";
import { getCookie } from "hono/cookie";
import type { AppConfig } from "../server/config";
import type { Repositories } from "../db/repositories";
import type { EngineClient } from "../engine/client";
import type { WorkerDeps } from "../jobs/worker";
import { processQueue } from "../jobs/worker";
import { DAILY_LLM_LIMIT, FREE_CASE_ID, type Language } from "../domain/types";
import { isWitnessId } from "../domain/case_meta";
import { CASE_META, RITES, pick } from "../i18n/case_catalog";
import {
  AuthError,
  CSRF_HEADER,
  SESSION_COOKIE,
  SESSION_TTL_SEC,
  checkOrigin,
  createSession,
  parseSession,
  sessionCookieHeader,
  validateInitData,
  type SessionPayload,
} from "./auth";
import {
  PresentEvidenceResponseSchema,
  SelectWitnessResponseSchema,
  SessionRequestSchema,
  SessionResponseSchema,
  VerdictRequestSchema,
  VerdictResponseSchema,
} from "./schemas";
import { EngineError } from "../engine/client";
import { log } from "../server/logger";

export interface MiniAppDeps {
  config: AppConfig;
  repos: Repositories;
  engine: EngineClient;
  workerDeps: WorkerDeps;
  kickWorker?: () => void;
}

type MaVars = { ma: SessionPayload };

function err(
  c: { json: (b: unknown, s?: number) => Response },
  code: string,
  status: number,
) {
  return c.json({ ok: false as const, error: code }, status);
}

function isSecure(publicUrl: string): boolean {
  return publicUrl.startsWith("https:");
}

function langOf(repos: Repositories, uid: number): Language {
  return (repos.getUser(uid)?.language as Language) ?? "en";
}

function syntheticUpdateId(): number {
  return -1 - Math.floor(Math.random() * 2_000_000_000);
}

export function createMiniAppRouter(deps: MiniAppDeps): Hono {
  const root = new Hono();

  root.post("/session", async (c) => {
    let body: unknown;
    try {
      body = await c.req.json();
    } catch {
      return err(c, "bad_json", 400);
    }
    const parsed = SessionRequestSchema.safeParse(body);
    if (!parsed.success) return err(c, "invalid_body", 400);

    try {
      const user = validateInitData(
        parsed.data.initData,
        deps.config.TELEGRAM_BOT_TOKEN,
      );
      deps.repos.ensureUser(user.telegramUserId, user.telegramUserId);
      const session = createSession(
        user.telegramUserId,
        deps.config.MINIAPP_SESSION_SECRET,
      );
      const language = langOf(deps.repos, user.telegramUserId);
      const res = SessionResponseSchema.parse({
        ok: true,
        language,
        csrf: session.csrf,
        expires_at: session.exp,
      });
      c.header(
        "Set-Cookie",
        sessionCookieHeader(
          session.cookieValue,
          SESSION_TTL_SEC,
          isSecure(deps.config.TELEGRAM_PUBLIC_URL),
        ),
      );
      return c.json(res);
    } catch (e) {
      if (e instanceof AuthError) return err(c, e.code, e.status);
      log({ level: "error", msg: "miniapp_session_error", status: "error" });
      return err(c, "server_error", 500);
    }
  });

  const authed = new Hono<{ Variables: MaVars }>();

  authed.use("*", async (c, next) => {
    try {
      const cookie = getCookie(c, SESSION_COOKIE);
      const session = parseSession(cookie, deps.config.MINIAPP_SESSION_SECRET);
      c.set("ma", session);
    } catch (e) {
      if (e instanceof AuthError) return err(c, e.code, e.status);
      return err(c, "unauthorized", 401);
    }
    await next();
  });

  function requireMutation(c: {
    req: { header: (n: string) => string | undefined; method: string };
    get: (k: "ma") => SessionPayload;
    json: (b: unknown, s?: number) => Response;
  }): Response | null {
    const origin = c.req.header("origin");
    const host = c.req.header("host");
    if (!checkOrigin(origin, host, deps.config.TELEGRAM_PUBLIC_URL)) {
      return err(c, "bad_origin", 403);
    }
    const csrf = c.req.header(CSRF_HEADER);
    const session = c.get("ma");
    if (!csrf || csrf !== session.csrf) {
      return err(c, "bad_csrf", 403);
    }
    return null;
  }

  authed.get("/casebook", async (c) => {
    const session = c.get("ma");
    const lang = langOf(deps.repos, session.uid);
    try {
      await deps.engine.ensureSession(session.uid);
      const snap = await deps.engine.snapshot(session.uid, FREE_CASE_ID);
      const availableLocations = snap.available_locations ?? [];
      const used = deps.repos.getLlmTurns(session.uid);
      return c.json({
        case_id: snap.case_id,
        title: snap.case_title || pick(lang, CASE_META.title),
        synopsis: snap.case_description || pick(lang, CASE_META.synopsis),
        current_location: {
          id: snap.current_location,
          name: snap.current_location_view?.name ?? snap.current_location,
        },
        visited_locations: snap.visited_locations.map((id) => ({
          id,
          name:
            availableLocations.find((location) => location.id === id)?.name ?? id,
        })),
        evidence_count: snap.discovered_evidence.length,
        llm_turns_used: used,
        llm_turns_limit: DAILY_LLM_LIMIT,
        verdict_attempts_remaining: snap.verdict_attempts_remaining,
        case_solved: snap.case_solved,
        briefing_completed: snap.briefing_completed,
        rites: RITES.map((r) => ({
          id: r.id,
          name: pick(lang, r.name),
          help: pick(lang, r.help),
        })),
        language: lang,
      });
    } catch (e) {
      if (e instanceof EngineError && e.code === "conflict") {
        return err(c, "conflict", 409);
      }
      return err(c, "engine_error", 502);
    }
  });

  authed.get("/evidence", async (c) => {
    const session = c.get("ma");
    const lang = langOf(deps.repos, session.uid);
    try {
      await deps.engine.ensureSession(session.uid);
      const snap = await deps.engine.snapshot(session.uid, FREE_CASE_ID);
      const evidence = (snap.evidence_details ?? []).map((item) => ({
        id: item.id,
        name: item.name,
        description: item.description,
        type: item.type,
        location_id: item.location_found,
        location_name: item.location_name,
      }));
      return c.json({ case_id: FREE_CASE_ID, evidence, language: lang });
    } catch {
      return err(c, "engine_error", 502);
    }
  });

  authed.get("/witnesses", async (c) => {
    const session = c.get("ma");
    const lang = langOf(deps.repos, session.uid);
    const tgSession = deps.repos.getSession(session.uid);
    const selected = tgSession?.mode === "witness" ? tgSession.witness_id : null;
    try {
      await deps.engine.ensureSession(session.uid);
      const snap = await deps.engine.snapshot(session.uid, FREE_CASE_ID);
      const witnesses = (snap.available_witnesses ?? []).map((witness) => ({
        id: witness.id,
        name: witness.name,
        bio: witness.description,
        selected: selected === witness.id,
      }));
      return c.json({
        case_id: FREE_CASE_ID,
        witnesses,
        selected_witness_id: selected,
        language: lang,
      });
    } catch {
      return err(c, "engine_error", 502);
    }
  });

  authed.post("/witnesses/:id/select", async (c) => {
    const blocked = requireMutation(c);
    if (blocked) return blocked;
    if (!deps.config.FEATURE_MINIAPP_MUTATIONS) {
      return err(c, "mutations_disabled", 503);
    }
    const session = c.get("ma");
    const id = c.req.param("id");
    if (!isWitnessId(id)) return err(c, "unknown_witness", 400);

    deps.repos.ensureUser(session.uid, session.uid);
    deps.repos.setSessionMode(session.uid, "witness", id);
    deps.repos.setOnboardingStep(session.uid, "active");

    const chatId = deps.repos.getUser(session.uid)?.chat_id ?? session.uid;
    const updateId = syntheticUpdateId();
    const requestId = `ma-wit-${session.uid}-${id}-${Date.now()}`;
    deps.repos.tryEnqueueUpdate({
      updateId,
      telegramUserId: session.uid,
      chatId,
      requestId,
      operation: "select_witness",
      payload: {
        chatId,
        kind: "select_witness",
        meta: { witnessId: id },
        callbackData: `wit:${id}`,
      },
    });
    deps.kickWorker?.();
    void processQueue(deps.workerDeps).catch(() => undefined);

    return c.json(
      SelectWitnessResponseSchema.parse({
        ok: true,
        witness_id: id,
        close: true,
      }),
    );
  });

  authed.post("/witnesses/:id/evidence/:evidenceId", async (c) => {
    const blocked = requireMutation(c);
    if (blocked) return blocked;
    if (!deps.config.FEATURE_MINIAPP_MUTATIONS) {
      return err(c, "mutations_disabled", 503);
    }
    const session = c.get("ma");
    const witnessId = c.req.param("id");
    const evidenceId = c.req.param("evidenceId");
    if (!isWitnessId(witnessId)) return err(c, "unknown_witness", 400);
    if (!/^[a-zA-Z0-9_-]+$/.test(evidenceId)) return err(c, "unknown_evidence", 400);
    await deps.engine.ensureSession(session.uid);
    const snap = await deps.engine.snapshot(session.uid, FREE_CASE_ID);
    if (!snap.discovered_evidence.includes(evidenceId)) {
      return err(c, "evidence_not_discovered", 400);
    }

    if (!deps.repos.canUseLlmTurn(session.uid, DAILY_LLM_LIMIT)) {
      return err(c, "cap_reached", 429);
    }

    const chatId = deps.repos.getUser(session.uid)?.chat_id ?? session.uid;
    const updateId = syntheticUpdateId();
    const requestId = `ma-ev-${session.uid}-${evidenceId}-${Date.now()}`;
    deps.repos.setSessionMode(session.uid, "witness", witnessId);
    const enq = deps.repos.tryEnqueueUpdate({
      updateId,
      telegramUserId: session.uid,
      chatId,
      requestId,
      operation: "present_evidence",
      payload: {
        chatId,
        kind: "present_evidence",
        meta: { witnessId, evidenceId },
      },
    });
    deps.kickWorker?.();
    void processQueue(deps.workerDeps).catch(() => undefined);

    return c.json(
      PresentEvidenceResponseSchema.parse({
        ok: true,
        queued: enq.created,
        request_id: requestId,
        close: true,
      }),
    );
  });

  authed.get("/verdict/options", async (c) => {
    const session = c.get("ma");
    const lang = langOf(deps.repos, session.uid);
    try {
      await deps.engine.ensureSession(session.uid);
      const snap = await deps.engine.snapshot(session.uid, FREE_CASE_ID);
      return c.json({
        suspects: snap.available_witnesses.map((witness) => ({
          id: witness.id,
          name: witness.name,
        })),
        evidence: (snap.evidence_details ?? []).map((evidence) => ({
          id: evidence.id,
          name: evidence.name,
        })),
        attempts_remaining: snap.verdict_attempts_remaining,
        case_solved: snap.case_solved,
        language: lang,
      });
    } catch {
      return err(c, "engine_error", 502);
    }
  });

  authed.post("/verdict", async (c) => {
    const blocked = requireMutation(c);
    if (blocked) return blocked;
    if (!deps.config.FEATURE_MINIAPP_MUTATIONS) {
      return err(c, "mutations_disabled", 503);
    }
    const session = c.get("ma");
    let raw: unknown;
    try {
      raw = await c.req.json();
    } catch {
      return err(c, "bad_json", 400);
    }
    const parsed = VerdictRequestSchema.safeParse(raw);
    if (!parsed.success) return err(c, "invalid_body", 400);

    if (!deps.repos.canUseLlmTurn(session.uid, DAILY_LLM_LIMIT)) {
      return err(c, "cap_reached", 429);
    }

    try {
      await deps.engine.ensureSession(session.uid);
      const res = await deps.engine.submitVerdict(session.uid, {
        case_id: FREE_CASE_ID,
        slot: "autosave",
        accused_suspect_id: parsed.data.accused_suspect_id,
        reasoning: parsed.data.reasoning,
        evidence_cited: parsed.data.evidence_cited,
        request_id: parsed.data.request_id,
      });
      deps.repos.incrementLlmTurns(session.uid);
      return c.json(
        VerdictResponseSchema.parse({
          ok: true,
          correct: res.correct,
          attempts_remaining: res.attempts_remaining,
          case_solved: res.case_solved,
          analysis: res.mentor_feedback.analysis,
          critique: res.mentor_feedback.critique,
          praise: res.mentor_feedback.praise,
          hint: res.mentor_feedback.hint ?? null,
          reveal: res.reveal ?? null,
        }),
      );
    } catch (e) {
      if (e instanceof EngineError && e.code === "conflict") {
        return err(c, "conflict", 409);
      }
      return err(c, "engine_error", 502);
    }
  });

  root.route("/", authed);
  return root;
}
