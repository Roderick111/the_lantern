import type { Database } from "bun:sqlite";
import {
  FREE_CASE_ID,
  type EntitlementStatus,
  type JobOperation,
  type JobPayload,
  type JobRow,
  type JobState,
  type Language,
  type OnboardingStep,
  type PendingVerdict,
  type SessionRow,
  type TelegramUserRow,
} from "../domain/types";
import { oldestPendingAgeSec as oldestPendingAgeSecImpl, purgeOldJobs as purgeOldJobsImpl } from "./retention";

function nowIso(): string {
  return new Date().toISOString();
}

function utcDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export class Repositories {
  constructor(private readonly db: Database) {}

  hasUpdate(updateId: number): boolean {
    const row = this.db
      .query("SELECT update_id FROM updates WHERE update_id = ?")
      .get(updateId) as { update_id: number } | null;
    return row !== null;
  }

  tryEnqueueUpdate(input: {
    updateId: number;
    telegramUserId: number;
    chatId: number;
    requestId: string;
    operation: JobOperation;
    payload: JobPayload;
  }): { created: boolean; jobId: number | null } {
    const tx = this.db.transaction(() => {
      if (this.hasUpdate(input.updateId)) {
        return { created: false, jobId: null };
      }

      const ts = nowIso();
      this.db.run("INSERT INTO updates (update_id, received_at) VALUES (?, ?)", [
        input.updateId,
        ts,
      ]);

      this.ensureUser(input.telegramUserId, input.chatId);

      const result = this.db
        .query(
          `INSERT INTO jobs (
            update_id, telegram_user_id, request_id, operation, payload,
            state, attempts, engine_dispatched, created_at, updated_at
          ) VALUES (?, ?, ?, ?, ?, 'pending', 0, 0, ?, ?)`,
        )
        .run(
          input.updateId,
          input.telegramUserId,
          input.requestId,
          input.operation,
          JSON.stringify(input.payload),
          ts,
          ts,
        );

      return { created: true, jobId: Number(result.lastInsertRowid) };
    });

    return tx();
  }

  /** True if user has pending/running/delivery/manual work ahead of this job. */
  hasActiveWorkAhead(telegramUserId: number, jobId: number): boolean {
    const row = this.db
      .query(
        `SELECT id FROM jobs
         WHERE telegram_user_id = ?
           AND id < ?
           AND state IN (
             'pending', 'running', 'engine_complete',
             'failed_delivery', 'needs_manual_retry'
           )
         LIMIT 1`,
      )
      .get(telegramUserId, jobId) as { id: number } | null;
    return row !== null;
  }

  ensureUser(telegramUserId: number, chatId: number): TelegramUserRow {
    const ts = nowIso();
    const row = this.db
      .query("SELECT * FROM users WHERE telegram_user_id = ?")
      .get(telegramUserId) as TelegramUserRow | null;

    if (row) {
      this.db.run(
        "UPDATE users SET chat_id = ?, updated_at = ? WHERE telegram_user_id = ?",
        [chatId, ts, telegramUserId],
      );
      return { ...row, chat_id: chatId, updated_at: ts };
    }

    this.db.run(
      `INSERT INTO users (
        telegram_user_id, chat_id, player_id, player_token, language, created_at, updated_at
      ) VALUES (?, ?, NULL, NULL, 'en', ?, ?)`,
      [telegramUserId, chatId, ts, ts],
    );

    this.db.run(
      `INSERT INTO sessions (
        telegram_user_id, case_id, mode, witness_id, onboarding_step, pending_json, updated_at
      ) VALUES (?, 'case_001', 'investigation', NULL, 'need_language', NULL, ?)`,
      [telegramUserId, ts],
    );

    this.db.run(
      `INSERT INTO entitlements (telegram_user_id, case_id, status) VALUES (?, ?, 'free')`,
      [telegramUserId, FREE_CASE_ID],
    );

    return this.db
      .query("SELECT * FROM users WHERE telegram_user_id = ?")
      .get(telegramUserId) as TelegramUserRow;
  }

  getUser(telegramUserId: number): TelegramUserRow | null {
    return this.db
      .query("SELECT * FROM users WHERE telegram_user_id = ?")
      .get(telegramUserId) as TelegramUserRow | null;
  }

  setPlayerCredentials(
    telegramUserId: number,
    playerId: string,
    playerToken: string,
  ): void {
    this.db.run(
      "UPDATE users SET player_id = ?, player_token = ?, updated_at = ? WHERE telegram_user_id = ?",
      [playerId, playerToken, nowIso(), telegramUserId],
    );
  }

  setLanguage(telegramUserId: number, language: Language): void {
    this.db.run(
      "UPDATE users SET language = ?, updated_at = ? WHERE telegram_user_id = ?",
      [language, nowIso(), telegramUserId],
    );
  }

  getSession(telegramUserId: number): SessionRow | null {
    return this.db
      .query("SELECT * FROM sessions WHERE telegram_user_id = ?")
      .get(telegramUserId) as SessionRow | null;
  }

  setSessionMode(
    telegramUserId: number,
    mode: "investigation" | "witness",
    witnessId: string | null = null,
  ): void {
    this.db.run(
      `UPDATE sessions SET mode = ?, witness_id = ?, updated_at = ?
       WHERE telegram_user_id = ?`,
      [mode, witnessId, nowIso(), telegramUserId],
    );
  }

  setOnboardingStep(telegramUserId: number, step: OnboardingStep): void {
    this.db.run(
      `UPDATE sessions SET onboarding_step = ?, updated_at = ? WHERE telegram_user_id = ?`,
      [step, nowIso(), telegramUserId],
    );
  }

  setPendingJson(telegramUserId: number, data: unknown | null): void {
    this.db.run(
      `UPDATE sessions SET pending_json = ?, updated_at = ? WHERE telegram_user_id = ?`,
      [data === null ? null : JSON.stringify(data), nowIso(), telegramUserId],
    );
  }

  getPendingVerdict(telegramUserId: number): PendingVerdict | null {
    const s = this.getSession(telegramUserId);
    if (!s?.pending_json) return null;
    try {
      const p = JSON.parse(s.pending_json) as PendingVerdict & { kind?: string };
      if (p.accused_suspect_id) {
        return {
          accused_suspect_id: p.accused_suspect_id,
          evidence_cited: p.evidence_cited ?? [],
        };
      }
    } catch {
      /* ignore */
    }
    return null;
  }

  getEntitlement(
    telegramUserId: number,
    caseId: string,
  ): EntitlementStatus {
    const row = this.db
      .query(
        "SELECT status FROM entitlements WHERE telegram_user_id = ? AND case_id = ?",
      )
      .get(telegramUserId, caseId) as { status: EntitlementStatus } | null;
    if (row) return row.status;
    if (caseId === FREE_CASE_ID) return "free";
    return "locked";
  }

  setEntitlement(
    telegramUserId: number,
    caseId: string,
    status: EntitlementStatus,
  ): void {
    this.db.run(
      `INSERT INTO entitlements (telegram_user_id, case_id, status) VALUES (?, ?, ?)
       ON CONFLICT(telegram_user_id, case_id) DO UPDATE SET status = excluded.status`,
      [telegramUserId, caseId, status],
    );
  }

  /** Atomic increment of LLM turns. Returns new count. */
  incrementLlmTurns(telegramUserId: number): number {
    const date = utcDate();
    const tx = this.db.transaction(() => {
      this.db.run(
        `INSERT INTO usage (telegram_user_id, utc_date, llm_turns) VALUES (?, ?, 0)
         ON CONFLICT(telegram_user_id, utc_date) DO NOTHING`,
        [telegramUserId, date],
      );
      this.db.run(
        `UPDATE usage SET llm_turns = llm_turns + 1
         WHERE telegram_user_id = ? AND utc_date = ?`,
        [telegramUserId, date],
      );
      const row = this.db
        .query(
          "SELECT llm_turns FROM usage WHERE telegram_user_id = ? AND utc_date = ?",
        )
        .get(telegramUserId, date) as { llm_turns: number };
      return row.llm_turns;
    });
    return tx();
  }

  /**
   * Atomic check-and-increment under daily cap.
   * Returns false if already at/over limit (no increment).
   */
  tryReserveLlmTurn(telegramUserId: number, limit: number): boolean {
    const date = utcDate();
    return this.db.transaction(() => {
      this.db.run(
        `INSERT INTO usage (telegram_user_id, utc_date, llm_turns) VALUES (?, ?, 0)
         ON CONFLICT(telegram_user_id, utc_date) DO NOTHING`,
        [telegramUserId, date],
      );
      const row = this.db
        .query(
          "SELECT llm_turns FROM usage WHERE telegram_user_id = ? AND utc_date = ?",
        )
        .get(telegramUserId, date) as { llm_turns: number };
      if (row.llm_turns >= limit) return false;
      this.db.run(
        `UPDATE usage SET llm_turns = llm_turns + 1
         WHERE telegram_user_id = ? AND utc_date = ?`,
        [telegramUserId, date],
      );
      return true;
    })();
  }

  /** Undo a reserve (pre-dispatch failure only). */
  refundLlmTurn(telegramUserId: number): void {
    const date = utcDate();
    this.db.run(
      `UPDATE usage SET llm_turns = MAX(0, llm_turns - 1)
       WHERE telegram_user_id = ? AND utc_date = ?`,
      [telegramUserId, date],
    );
  }

  getLlmTurns(telegramUserId: number): number {
    const row = this.db
      .query(
        "SELECT llm_turns FROM usage WHERE telegram_user_id = ? AND utc_date = ?",
      )
      .get(telegramUserId, utcDate()) as { llm_turns: number } | null;
    return row?.llm_turns ?? 0;
  }

  /** Soft read: false if at/over daily cap. Prefer tryReserveLlmTurn for mutations. */
  canUseLlmTurn(telegramUserId: number, limit: number): boolean {
    return this.getLlmTurns(telegramUserId) < limit;
  }

  hasMediaReceipt(
    telegramUserId: number,
    mediaKind: string,
    mediaId: string,
  ): boolean {
    const row = this.db
      .query(
        `SELECT 1 AS ok FROM media_receipts
         WHERE telegram_user_id = ? AND media_kind = ? AND media_id = ?`,
      )
      .get(telegramUserId, mediaKind, mediaId) as { ok: number } | null;
    return row !== null;
  }

  getMediaFileId(
    telegramUserId: number,
    mediaKind: string,
    mediaId: string,
  ): string | null {
    const row = this.db
      .query(
        `SELECT file_id FROM media_receipts
         WHERE telegram_user_id = ? AND media_kind = ? AND media_id = ?`,
      )
      .get(telegramUserId, mediaKind, mediaId) as { file_id: string | null } | null;
    return row?.file_id ?? null;
  }

  recordMediaReceipt(
    telegramUserId: number,
    mediaKind: string,
    mediaId: string,
    fileId: string | null = null,
  ): void {
    this.db.run(
      `INSERT INTO media_receipts (telegram_user_id, media_kind, media_id, file_id, first_seen_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(telegram_user_id, media_kind, media_id) DO UPDATE SET
         file_id = COALESCE(excluded.file_id, media_receipts.file_id)`,
      [telegramUserId, mediaKind, mediaId, fileId, nowIso()],
    );
  }

  /** Reset Telegram case progress (keep identity + entitlements). */
  resetTelegramCase(telegramUserId: number, caseId: string): void {
    const ts = nowIso();
    this.db.run(
      `UPDATE sessions SET mode = 'investigation', witness_id = NULL,
         onboarding_step = 'need_begin', pending_json = NULL, case_id = ?, updated_at = ?
       WHERE telegram_user_id = ?`,
      [caseId, ts, telegramUserId],
    );
    this.db.run(
      `DELETE FROM media_receipts WHERE telegram_user_id = ?`,
      [telegramUserId],
    );
  }

  getJob(id: number): JobRow | null {
    return this.db.query("SELECT * FROM jobs WHERE id = ?").get(id) as JobRow | null;
  }

  claimNextJobForUser(telegramUserId: number): JobRow | null {
    const tx = this.db.transaction(() => {
      const active = this.db
        .query(
          `SELECT id, state FROM jobs
           WHERE telegram_user_id = ?
             AND state IN (
               'running', 'engine_complete', 'failed_delivery', 'needs_manual_retry'
             )
           ORDER BY id ASC LIMIT 1`,
        )
        .get(telegramUserId) as { id: number; state: string } | null;

      const next = this.db
        .query(
          `SELECT * FROM jobs
           WHERE telegram_user_id = ? AND state = 'pending'
           ORDER BY id ASC LIMIT 1`,
        )
        .get(telegramUserId) as JobRow | null;
      if (!next) return null;

      if (active) {
        // Only retry_hint may pass a stuck needs_manual_retry (ack "cannot retry").
        if (active.state !== "needs_manual_retry") return null;
        let kind = "";
        try {
          kind = (JSON.parse(next.payload) as JobPayload).kind ?? "";
        } catch {
          return null;
        }
        if (kind !== "retry_hint") return null;
      }

      const ts = nowIso();
      this.db.run(
        `UPDATE jobs SET state = 'running', attempts = attempts + 1, updated_at = ?
         WHERE id = ? AND state = 'pending'`,
        [ts, next.id],
      );
      return this.getJob(next.id);
    });
    return tx();
  }

  listUsersWithWork(): number[] {
    const rows = this.db
      .query(
        `SELECT DISTINCT telegram_user_id FROM jobs
         WHERE state IN ('pending', 'engine_complete', 'failed_delivery')
         ORDER BY telegram_user_id`,
      )
      .all() as { telegram_user_id: number }[];
    return rows.map((r) => r.telegram_user_id);
  }

  markEngineDispatched(jobId: number): void {
    this.db.run(
      `UPDATE jobs SET engine_dispatched = 1, updated_at = ? WHERE id = ?`,
      [nowIso(), jobId],
    );
  }

  markEngineComplete(jobId: number, engineResponse: unknown): void {
    this.db.run(
      `UPDATE jobs SET state = 'engine_complete', engine_response = ?, updated_at = ?
       WHERE id = ?`,
      [JSON.stringify(engineResponse), nowIso(), jobId],
    );
  }

  markDelivered(jobId: number): void {
    this.db.run(
      `UPDATE jobs SET state = 'delivered', delivery_status = 'ok', delivery_error = NULL,
         updated_at = ? WHERE id = ?`,
      [nowIso(), jobId],
    );
  }

  markDeliveryFailed(jobId: number, error: string): void {
    this.db.run(
      `UPDATE jobs SET state = 'failed_delivery', delivery_status = 'error',
         delivery_error = ?, updated_at = ? WHERE id = ?`,
      [error.slice(0, 200), nowIso(), jobId],
    );
  }

  markNeedsManualRetry(jobId: number, note: string): void {
    this.db.run(
      `UPDATE jobs SET state = 'needs_manual_retry', delivery_error = ?, updated_at = ?
       WHERE id = ?`,
      [note.slice(0, 200), nowIso(), jobId],
    );
  }

  /** Re-queue undispatched running job as pending (known pre-mutation failure). */
  requeuePending(jobId: number): void {
    this.db.run(
      `UPDATE jobs SET state = 'pending', engine_dispatched = 0, updated_at = ?
       WHERE id = ? AND engine_dispatched = 0`,
      [nowIso(), jobId],
    );
  }

  /**
   * Requeue oldest needs_manual_retry job for user.
   * - engine_response set → engine_complete (re-deliver only)
   * - engine_dispatched = 0 → pending (safe re-run)
   * - else → null (ambiguous post-dispatch; user must re-issue action)
   */
  requeueOldestManualJob(telegramUserId: number): number | null {
    const job = this.db
      .query(
        `SELECT * FROM jobs
         WHERE telegram_user_id = ? AND state = 'needs_manual_retry'
         ORDER BY id ASC LIMIT 1`,
      )
      .get(telegramUserId) as JobRow | null;
    if (!job) return null;

    const ts = nowIso();
    if (job.engine_response) {
      this.db.run(
        `UPDATE jobs SET state = 'engine_complete', delivery_error = NULL, updated_at = ?
         WHERE id = ?`,
        [ts, job.id],
      );
      return job.id;
    }
    if (job.engine_dispatched === 0) {
      this.db.run(
        `UPDATE jobs SET state = 'pending', delivery_error = NULL, updated_at = ?
         WHERE id = ?`,
        [ts, job.id],
      );
      return job.id;
    }
    return null;
  }

  /** Persist updated engine_response (delivery progress trimming). */
  updateEngineResponse(jobId: number, engineResponse: unknown): void {
    this.db.run(
      `UPDATE jobs SET engine_response = ?, updated_at = ? WHERE id = ?`,
      [JSON.stringify(engineResponse), nowIso(), jobId],
    );
  }

  recoverOnStartup(): { resetToPending: number; manual: number } {
    const ts = nowIso();
    const reset = this.db
      .query(
        `UPDATE jobs SET state = 'pending', updated_at = ?
         WHERE state = 'running' AND engine_dispatched = 0`,
      )
      .run(ts);
    const manual = this.db
      .query(
        `UPDATE jobs SET state = 'needs_manual_retry',
           delivery_error = 'ambiguous after restart', updated_at = ?
         WHERE state = 'running' AND engine_dispatched = 1`,
      )
      .run(ts);
    return {
      resetToPending: reset.changes,
      manual: manual.changes,
    };
  }

  countJobsByState(state: JobState): number {
    const row = this.db
      .query("SELECT COUNT(*) AS c FROM jobs WHERE state = ?")
      .get(state) as { c: number };
    return row.c;
  }

  getDeliveryRetryJob(telegramUserId: number): JobRow | null {
    return this.db
      .query(
        `SELECT * FROM jobs
         WHERE telegram_user_id = ?
           AND state IN ('engine_complete', 'failed_delivery')
         ORDER BY id ASC LIMIT 1`,
      )
      .get(telegramUserId) as JobRow | null;
  }

  oldestPendingAgeSec(): number | null {
    return oldestPendingAgeSecImpl(this.db);
  }

  purgeOldJobs(days = 7, limit = 500): { jobs: number; updates: number } {
    return purgeOldJobsImpl(this.db, days, limit);
  }
}
