import { describe, expect, it } from "bun:test";
import { getLaunchRedirect } from "../app/src/routes";

describe("Mini App launch routing", () => {
  it("keeps an explicit Casebook hash over a conflicting Telegram start parameter", () => {
    expect(
      getLaunchRedirect("?tgWebAppStartParam=evidence", "#/casebook"),
    ).toBeNull();
  });

  it("uses a valid start parameter when no hash route exists", () => {
    expect(getLaunchRedirect("?startapp=witnesses", "")).toBe("/witnesses");
  });

  it("defaults bare launches to Casebook", () => {
    expect(getLaunchRedirect("", "")).toBe("/casebook");
  });
});
