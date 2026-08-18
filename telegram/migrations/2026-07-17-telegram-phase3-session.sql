-- Phase 3: onboarding + pending multi-step flows on sessions.
-- Owner: run against telegram.db if already created from Phase 2 schema.
-- Fresh installs use SCHEMA_SQL (columns included).
-- Example:
--   sqlite3 /app/data/telegram.db < telegram/migrations/2026-07-17-telegram-phase3-session.sql

-- SQLite has no IF NOT EXISTS for ADD COLUMN; ignore errors if columns exist.
ALTER TABLE sessions ADD COLUMN onboarding_step TEXT NOT NULL DEFAULT 'need_language';
ALTER TABLE sessions ADD COLUMN pending_json TEXT;
