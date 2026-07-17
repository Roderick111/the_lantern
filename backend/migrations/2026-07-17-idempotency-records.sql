-- Phase 1: Idempotency foundation for Telegram durable jobs.
-- Keyed by (player_id, operation, request_id).
-- Owner: run against production/staging lantern.db. Coding agent does not execute this.
--
-- Example:
--   sqlite3 /path/to/lantern.db < backend/migrations/2026-07-17-idempotency-records.sql

CREATE TABLE IF NOT EXISTS idempotency_records (
    player_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    request_id TEXT NOT NULL,
    status TEXT NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (player_id, operation, request_id)
);

CREATE INDEX IF NOT EXISTS idx_idempotency_updated_at
    ON idempotency_records(updated_at);
