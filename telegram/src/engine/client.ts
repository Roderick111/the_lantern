import {
  BriefingCompleteResponseSchema,
  ChangeLocationResponseSchema,
  InterrogateResponseSchema,
  InvestigateResponseSchema,
  PresentEvidenceResponseSchema,
  ResetResponseSchema,
  SessionResponseSchema,
  SubmitVerdictResponseSchema,
  TelegramSnapshotSchema,
  UpdateSettingsResponseSchema,
  type ChangeLocationResponse,
  type InterrogateResponse,
  type InvestigateResponse,
  type PresentEvidenceResponse,
  type ResetResponse,
  type SessionResponse,
  type SubmitVerdictResponse,
  type TelegramSnapshot,
  type UpdateSettingsResponse,
} from "./schemas";

export type EngineErrorCode =
  | "bad_request"
  | "unauthorized"
  | "conflict"
  | "rate_limited"
  | "server_error"
  | "transport"
  | "timeout"
  | "schema";

export class EngineError extends Error {
  constructor(
    public readonly code: EngineErrorCode,
    public readonly status: number | null,
    message: string,
  ) {
    super(message);
    this.name = "EngineError";
  }
}

export type FetchLike = (
  input: string | URL | Request,
  init?: RequestInit,
) => Promise<Response>;

export interface EngineClientOptions {
  baseUrl: string;
  timeoutMs: number;
  fetchImpl?: FetchLike;
}

export interface TokenStore {
  getToken(telegramUserId: number): string | null;
  getPlayerId(telegramUserId: number): string | null;
  setCredentials(
    telegramUserId: number,
    playerId: string,
    token: string,
  ): void;
}

export class EngineClient {
  private readonly fetchFn: FetchLike;
  /** MED-04/05: dedupe concurrent createSession / refresh per user */
  private sessionInflight = new Map<number, Promise<string>>();

  constructor(
    private readonly opts: EngineClientOptions,
    private readonly tokens: TokenStore,
  ) {
    this.fetchFn = opts.fetchImpl ?? ((input, init) => fetch(input, init));
  }

  async createSession(telegramUserId: number): Promise<SessionResponse> {
    const data = await this.requestJson(
      "POST",
      "/api/session",
      SessionResponseSchema,
      { body: {} },
    );
    this.tokens.setCredentials(telegramUserId, data.player_id, data.token);
    return data;
  }

  /** Force a new engine session; concurrent callers share one request. */
  private recreateSession(telegramUserId: number): Promise<string> {
    let p = this.sessionInflight.get(telegramUserId);
    if (!p) {
      p = this.createSession(telegramUserId)
        .then((s) => s.token)
        .finally(() => {
          this.sessionInflight.delete(telegramUserId);
        });
      this.sessionInflight.set(telegramUserId, p);
    }
    return p;
  }

  async ensureSession(telegramUserId: number): Promise<string> {
    const existing = this.tokens.getToken(telegramUserId);
    if (existing) return existing;
    return this.recreateSession(telegramUserId);
  }

  async investigate(
    telegramUserId: number,
    body: {
      player_input: string;
      case_id?: string;
      location_id?: string;
      slot?: string;
      request_id?: string;
    },
  ): Promise<InvestigateResponse> {
    return this.authedJson(
      telegramUserId,
      "POST",
      "/api/investigate",
      InvestigateResponseSchema,
      { body },
    );
  }

  async interrogate(
    telegramUserId: number,
    body: {
      witness_id: string;
      question: string;
      case_id?: string;
      slot?: string;
      request_id?: string;
    },
  ): Promise<InterrogateResponse> {
    return this.authedJson(
      telegramUserId,
      "POST",
      "/api/interrogate",
      InterrogateResponseSchema,
      { body },
    );
  }

  async presentEvidence(
    telegramUserId: number,
    body: {
      witness_id: string;
      evidence_id: string;
      case_id?: string;
      slot?: string;
      request_id?: string;
    },
  ): Promise<PresentEvidenceResponse> {
    return this.authedJson(
      telegramUserId,
      "POST",
      "/api/present-evidence",
      PresentEvidenceResponseSchema,
      { body },
    );
  }

  async changeLocation(
    telegramUserId: number,
    caseId: string,
    body: { location_id: string; slot?: string; request_id?: string },
  ): Promise<ChangeLocationResponse> {
    return this.authedJson(
      telegramUserId,
      "POST",
      `/api/case/${encodeURIComponent(caseId)}/change-location`,
      ChangeLocationResponseSchema,
      { body },
    );
  }

  async updateSettings(
    telegramUserId: number,
    body: {
      case_id?: string;
      language?: string;
      slot?: string;
      request_id?: string;
    },
  ): Promise<UpdateSettingsResponse> {
    return this.authedJson(
      telegramUserId,
      "POST",
      "/api/settings/update",
      UpdateSettingsResponseSchema,
      { body },
    );
  }

  async completeBriefing(
    telegramUserId: number,
    caseId: string,
    body: { request_id?: string } = {},
  ): Promise<unknown> {
    return this.authedJson(
      telegramUserId,
      "POST",
      `/api/briefing/${encodeURIComponent(caseId)}/complete`,
      BriefingCompleteResponseSchema,
      { body },
    );
  }

  async resetCase(telegramUserId: number, caseId: string): Promise<ResetResponse> {
    return this.authedJson(
      telegramUserId,
      "POST",
      `/api/case/${encodeURIComponent(caseId)}/reset`,
      ResetResponseSchema,
    );
  }

  async submitVerdict(
    telegramUserId: number,
    body: {
      case_id?: string;
      slot?: string;
      accused_suspect_id: string;
      reasoning: string;
      evidence_cited?: string[];
      request_id?: string;
    },
  ): Promise<SubmitVerdictResponse> {
    return this.authedJson(
      telegramUserId,
      "POST",
      "/api/submit-verdict",
      SubmitVerdictResponseSchema,
      { body },
    );
  }

  async snapshot(
    telegramUserId: number,
    caseId: string,
    slot = "autosave",
  ): Promise<TelegramSnapshot> {
    return this.authedJson(
      telegramUserId,
      "GET",
      `/api/telegram/snapshot/${caseId}?slot=${encodeURIComponent(slot)}`,
      TelegramSnapshotSchema,
    );
  }

  async health(): Promise<boolean> {
    try {
      const res = await this.fetchWithTimeout(
        `${this.opts.baseUrl.replace(/\/$/, "")}/health`,
        { method: "GET" },
      );
      return res.ok;
    } catch {
      return false;
    }
  }

  private async authedJson<T>(
    telegramUserId: number,
    method: string,
    path: string,
    schema: { parse: (v: unknown) => T },
    init: { body?: unknown } = {},
  ): Promise<T> {
    // MED-07: use token returned from ensureSession (no second getToken)
    const token = await this.ensureSession(telegramUserId);
    try {
      return await this.requestJson(method, path, schema, {
        ...init,
        token,
      });
    } catch (err) {
      if (err instanceof EngineError && err.code === "unauthorized") {
        // MED-05: concurrent 401s share one recreateSession
        const fresh = await this.recreateSession(telegramUserId);
        return await this.requestJson(method, path, schema, {
          ...init,
          token: fresh,
        });
      }
      throw err;
    }
  }

  private async requestJson<T>(
    method: string,
    path: string,
    schema: { parse: (v: unknown) => T },
    init: { body?: unknown; token?: string } = {},
  ): Promise<T> {
    const url = `${this.opts.baseUrl.replace(/\/$/, "")}${path}`;
    const headers: Record<string, string> = {
      Accept: "application/json",
    };
    if (init.token) {
      headers["X-Player-Token"] = init.token;
    }
    let body: string | undefined;
    if (init.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(init.body);
    }

    let res: Response;
    try {
      res = await this.fetchWithTimeout(url, { method, headers, body });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "transport error";
      if (msg.includes("timeout") || msg.includes("Timeout")) {
        throw new EngineError("timeout", null, msg);
      }
      throw new EngineError("transport", null, msg);
    }

    if (res.status === 400) {
      throw new EngineError("bad_request", 400, await safeText(res));
    }
    if (res.status === 401) {
      throw new EngineError("unauthorized", 401, "engine unauthorized");
    }
    if (res.status === 409) {
      throw new EngineError("conflict", 409, await safeText(res));
    }
    if (res.status === 429) {
      throw new EngineError("rate_limited", 429, "engine rate limited");
    }
    if (res.status >= 500) {
      throw new EngineError("server_error", res.status, "engine server error");
    }
    if (!res.ok) {
      throw new EngineError("server_error", res.status, `engine HTTP ${res.status}`);
    }

    // Some endpoints return empty / non-strict extras; parse JSON then schema
    let json: unknown;
    try {
      json = await res.json();
    } catch {
      throw new EngineError("schema", res.status, "invalid JSON");
    }

    try {
      return schema.parse(json);
    } catch (e) {
      throw new EngineError(
        "schema",
        res.status,
        e instanceof Error ? e.message : "schema mismatch",
      );
    }
  }

  private async fetchWithTimeout(
    url: string,
    init: RequestInit,
  ): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.opts.timeoutMs);
    try {
      return await this.fetchFn(url, { ...init, signal: controller.signal });
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") {
        throw new Error("timeout");
      }
      throw e;
    } finally {
      clearTimeout(timer);
    }
  }
}

async function safeText(res: Response): Promise<string> {
  try {
    return (await res.text()).slice(0, 200);
  } catch {
    return "error";
  }
}

export function repoTokenStore(repos: {
  getUser: (id: number) => { player_id: string | null; player_token: string | null } | null;
  setPlayerCredentials: (id: number, playerId: string, token: string) => void;
}): TokenStore {
  return {
    getToken(telegramUserId) {
      return repos.getUser(telegramUserId)?.player_token ?? null;
    },
    getPlayerId(telegramUserId) {
      return repos.getUser(telegramUserId)?.player_id ?? null;
    },
    setCredentials(telegramUserId, playerId, token) {
      repos.setPlayerCredentials(telegramUserId, playerId, token);
    },
  };
}
