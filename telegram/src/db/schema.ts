/** Embedded schema — mirrors migrations for boot. */

export const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS users (
    telegram_user_id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    player_id TEXT,
    player_token TEXT,
    language TEXT NOT NULL DEFAULT 'en',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    telegram_user_id INTEGER PRIMARY KEY,
    case_id TEXT NOT NULL DEFAULT 'case_001',
    mode TEXT NOT NULL DEFAULT 'investigation',
    witness_id TEXT,
    onboarding_step TEXT NOT NULL DEFAULT 'need_language',
    pending_json TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
);

CREATE TABLE IF NOT EXISTS usage (
    telegram_user_id INTEGER NOT NULL,
    utc_date TEXT NOT NULL,
    llm_turns INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (telegram_user_id, utc_date),
    FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
);

CREATE TABLE IF NOT EXISTS updates (
    update_id INTEGER PRIMARY KEY,
    received_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    update_id INTEGER NOT NULL,
    telegram_user_id INTEGER NOT NULL,
    request_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    payload TEXT NOT NULL,
    state TEXT NOT NULL,
    engine_response TEXT,
    delivery_status TEXT,
    delivery_error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    engine_dispatched INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (update_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_user_state ON jobs(telegram_user_id, state);
CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);

CREATE TABLE IF NOT EXISTS entitlements (
    telegram_user_id INTEGER NOT NULL,
    case_id TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (telegram_user_id, case_id),
    FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
);

CREATE TABLE IF NOT EXISTS media_receipts (
    telegram_user_id INTEGER NOT NULL,
    media_kind TEXT NOT NULL,
    media_id TEXT NOT NULL,
    file_id TEXT,
    first_seen_at TEXT NOT NULL,
    PRIMARY KEY (telegram_user_id, media_kind, media_id),
    FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
);
`;

/** Best-effort column adds for DBs created before Phase 3. */
export const MIGRATE_SQL = `
PRAGMA foreign_keys=ON;
`;

export function migrateSchema(db: {
  query: (sql: string) => { all: () => unknown[] };
  exec: (sql: string) => void;
}): void {
  const cols = db
    .query("PRAGMA table_info(sessions)")
    .all() as { name: string }[];
  const names = new Set(cols.map((c) => c.name));
  if (!names.has("onboarding_step")) {
    db.exec(
      "ALTER TABLE sessions ADD COLUMN onboarding_step TEXT NOT NULL DEFAULT 'need_language'",
    );
  }
  if (!names.has("pending_json")) {
    db.exec("ALTER TABLE sessions ADD COLUMN pending_json TEXT");
  }
}
