import { z } from "zod";

const boolFromEnv = z
  .union([z.boolean(), z.string()])
  .transform((v) => {
    if (typeof v === "boolean") return v;
    return !["0", "false", "no", "off"].includes(v.toLowerCase());
  });

const ConfigSchema = z.object({
  TELEGRAM_BOT_TOKEN: z.string().min(1),
  TELEGRAM_WEBHOOK_SECRET: z.string().min(8),
  TELEGRAM_PUBLIC_URL: z
    .string()
    .url()
    .default("https://bot.thelantern.institute"),
  TELEGRAM_DB_PATH: z.string().min(1).default("/app/data/telegram.db"),
  MINIAPP_SESSION_SECRET: z.string().min(16),
  LANTERN_ENGINE_URL: z.string().url().default("http://backend:8000"),
  TELEGRAM_MODE: z.enum(["webhook", "polling"]).default("webhook"),
  PORT: z.coerce.number().int().positive().default(8080),
  FEATURE_NEW_SESSIONS: boolFromEnv.default(true),
  FEATURE_LLM_TURNS: boolFromEnv.default(true),
  /** Kill switch: block Mini App present/select/verdict mutations. */
  FEATURE_MINIAPP_MUTATIONS: boolFromEnv.default(true),
  ENGINE_TIMEOUT_MS: z.coerce.number().int().positive().default(60_000),
  /** Path to frontend/public (locations + portraits). */
  ASSETS_PATH: z.string().default("../frontend/public"),
  /** Retention for terminal jobs/updates (days). */
  RETENTION_DAYS: z.coerce.number().int().positive().default(7),
  /** Optional token for GET /metrics (empty/absent = endpoint disabled). */
  METRICS_TOKEN: z
    .preprocess(
      (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
      z.string().min(8).optional(),
    ),
  /** Allow localhost Origin for Mini App when developing locally. */
  TELEGRAM_ALLOW_LOCAL_ORIGIN: boolFromEnv.default(false),
});

export type AppConfig = z.infer<typeof ConfigSchema>;

export function loadConfig(env: Record<string, string | undefined> = process.env): AppConfig {
  const parsed = ConfigSchema.safeParse({
    TELEGRAM_BOT_TOKEN: env.TELEGRAM_BOT_TOKEN,
    TELEGRAM_WEBHOOK_SECRET: env.TELEGRAM_WEBHOOK_SECRET,
    TELEGRAM_PUBLIC_URL: env.TELEGRAM_PUBLIC_URL,
    TELEGRAM_DB_PATH: env.TELEGRAM_DB_PATH,
    MINIAPP_SESSION_SECRET: env.MINIAPP_SESSION_SECRET,
    LANTERN_ENGINE_URL: env.LANTERN_ENGINE_URL,
    TELEGRAM_MODE: env.TELEGRAM_MODE,
    PORT: env.PORT,
    FEATURE_NEW_SESSIONS: env.FEATURE_NEW_SESSIONS,
    FEATURE_LLM_TURNS: env.FEATURE_LLM_TURNS,
    FEATURE_MINIAPP_MUTATIONS: env.FEATURE_MINIAPP_MUTATIONS,
    ENGINE_TIMEOUT_MS: env.ENGINE_TIMEOUT_MS,
    ASSETS_PATH: env.ASSETS_PATH,
    RETENTION_DAYS: env.RETENTION_DAYS,
    METRICS_TOKEN: env.METRICS_TOKEN,
    TELEGRAM_ALLOW_LOCAL_ORIGIN: env.TELEGRAM_ALLOW_LOCAL_ORIGIN,
  });
  if (!parsed.success) {
    const msg = parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
    throw new Error(`Invalid config: ${msg}`);
  }
  return parsed.data;
}

/** Test helper — full valid config with overrides. */
export function testConfig(overrides: Partial<AppConfig> = {}): AppConfig {
  return {
    TELEGRAM_BOT_TOKEN: "123456:TEST-Token-For-Tests",
    TELEGRAM_WEBHOOK_SECRET: "test-webhook-secret-value",
    TELEGRAM_PUBLIC_URL: "https://bot.thelantern.institute",
    TELEGRAM_DB_PATH: ":memory:",
    MINIAPP_SESSION_SECRET: "test-miniapp-session-secret",
    LANTERN_ENGINE_URL: "http://localhost:8000",
    TELEGRAM_MODE: "webhook",
    PORT: 8080,
    FEATURE_NEW_SESSIONS: true,
    FEATURE_LLM_TURNS: true,
    FEATURE_MINIAPP_MUTATIONS: true,
    ENGINE_TIMEOUT_MS: 5_000,
    ASSETS_PATH: "../frontend/public",
    RETENTION_DAYS: 7,
    METRICS_TOKEN: undefined,
    TELEGRAM_ALLOW_LOCAL_ORIGIN: false,
    ...overrides,
  };
}
