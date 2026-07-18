import { describe, it, expect, beforeEach } from "bun:test";
import { resetDbForTests } from "../src/db/connection";
import { Repositories } from "../src/db/repositories";
import { FREE_CASE_ID } from "../src/domain/types";
import { assertCatalogParity } from "../src/i18n/strings";
import { redactString, sanitizeFields, log } from "../src/server/logger";

describe("entitlements", () => {
  let repos: Repositories;

  beforeEach(() => {
    repos = new Repositories(resetDbForTests());
  });

  it("defaults case_001 free and others locked", () => {
    repos.ensureUser(1, 1);
    expect(repos.getEntitlement(1, FREE_CASE_ID)).toBe("free");
    expect(repos.getEntitlement(1, "case_002")).toBe("locked");
    repos.setEntitlement(1, "case_002", "owned");
    expect(repos.getEntitlement(1, "case_002")).toBe("owned");
  });
});

describe("usage", () => {
  it("increments llm turns atomically", () => {
    const repos = new Repositories(resetDbForTests());
    repos.ensureUser(5, 5);
    expect(repos.incrementLlmTurns(5)).toBe(1);
    expect(repos.incrementLlmTurns(5)).toBe(2);
    expect(repos.getLlmTurns(5)).toBe(2);
  });

  it("tryReserveLlmTurn respects cap", () => {
    const repos = new Repositories(resetDbForTests());
    repos.ensureUser(6, 6);
    expect(repos.tryReserveLlmTurn(6, 2)).toBe(true);
    expect(repos.tryReserveLlmTurn(6, 2)).toBe(true);
    expect(repos.tryReserveLlmTurn(6, 2)).toBe(false);
    expect(repos.getLlmTurns(6)).toBe(2);
    repos.refundLlmTurn(6);
    expect(repos.getLlmTurns(6)).toBe(1);
    expect(repos.tryReserveLlmTurn(6, 2)).toBe(true);
  });
});

describe("i18n", () => {
  it("en/ru keys match", () => {
    expect(() => assertCatalogParity()).not.toThrow();
  });
});

describe("logger redaction", () => {
  it("redacts bot tokens and keys", () => {
    const s = redactString("token bot123456:AA-secret-token-value-here sk-abcdefghij");
    expect(s).not.toContain("AA-secret");
    expect(s).toContain("[REDACTED]");
  });

  it("sanitizes secret field names", () => {
    const out = sanitizeFields({
      player_token: "secret-token",
      update_id: 1,
      text: "player said something long",
    });
    expect(out.player_token).toBe("[REDACTED]");
    expect(out.text).toBe("[REDACTED]");
    expect(out.update_id).toBe(1);
  });

  it("log does not throw with secrets", () => {
    expect(() =>
      log({
        msg: "test",
        player_token: "nope",
        request_id: "r1",
        update_id: 1,
      }),
    ).not.toThrow();
  });
});
