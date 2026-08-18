import { describe, it, expect, beforeEach } from "bun:test";
import { EngineClient, type TokenStore } from "../src/engine/client";

function memoryTokens(): TokenStore & {
  map: Map<number, { playerId: string; token: string }>;
} {
  const map = new Map<number, { playerId: string; token: string }>();
  return {
    map,
    getToken(id) {
      return map.get(id)?.token ?? null;
    },
    getPlayerId(id) {
      return map.get(id)?.playerId ?? null;
    },
    setCredentials(id, playerId, token) {
      map.set(id, { playerId, token });
    },
  };
}

describe("EngineClient", () => {
  let tokens: ReturnType<typeof memoryTokens>;
  let calls: { url: string; headers: HeadersInit | undefined }[];

  beforeEach(() => {
    tokens = memoryTokens();
    calls = [];
  });

  it("refreshes token once on 401", async () => {
    let sessionPosts = 0;
    let investigateTries = 0;

    const fetchImpl = async (input: string | URL | Request, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, headers: init?.headers });
      if (url.endsWith("/api/session")) {
        sessionPosts += 1;
        return new Response(
          JSON.stringify({ player_id: "p1", token: `tok-${sessionPosts}` }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.includes("/api/investigate")) {
        investigateTries += 1;
        if (investigateTries === 1) {
          return new Response("nope", { status: 401 });
        }
        return new Response(
          JSON.stringify({
            narrator_response: "ok",
            new_evidence: [],
            evidence_names: {},
            already_discovered: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("missing", { status: 404 });
    };

    const client = new EngineClient(
      { baseUrl: "http://engine", timeoutMs: 2000, fetchImpl },
      tokens,
    );

    // Seed stale token
    tokens.setCredentials(1, "p1", "stale");

    const res = await client.investigate(1, {
      player_input: "look",
      request_id: "r1",
    });
    expect(res.narrator_response).toBe("ok");
    expect(sessionPosts).toBe(1); // one refresh
    expect(investigateTries).toBe(2);
    expect(tokens.getToken(1)).toBe("tok-1");
  });

  it("dedupes parallel ensureSession create calls", async () => {
    let sessionPosts = 0;
    let resolveSession: (() => void) | null = null;
    const gate = new Promise<void>((r) => {
      resolveSession = r;
    });

    const fetchImpl = async (input: string | URL | Request) => {
      const url = String(input);
      if (url.endsWith("/api/session")) {
        sessionPosts += 1;
        await gate;
        return new Response(
          JSON.stringify({ player_id: "p1", token: "shared-tok" }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("missing", { status: 404 });
    };

    const client = new EngineClient(
      { baseUrl: "http://engine", timeoutMs: 5000, fetchImpl },
      tokens,
    );

    const a = client.ensureSession(42);
    const b = client.ensureSession(42);
    resolveSession!();
    const [ta, tb] = await Promise.all([a, b]);
    expect(ta).toBe("shared-tok");
    expect(tb).toBe("shared-tok");
    expect(sessionPosts).toBe(1);
  });

  it("maps 409 to conflict", async () => {
    const fetchImpl = async () =>
      new Response(JSON.stringify({ detail: { code: "request_in_progress" } }), {
        status: 409,
      });
    const client = new EngineClient(
      { baseUrl: "http://engine", timeoutMs: 2000, fetchImpl },
      tokens,
    );
    tokens.setCredentials(1, "p", "t");
    await expect(
      client.investigate(1, { player_input: "x" }),
    ).rejects.toMatchObject({ code: "conflict", status: 409 });
  });
});
