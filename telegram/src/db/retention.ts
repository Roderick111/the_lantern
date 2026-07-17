import type { Database } from "bun:sqlite";

/** Age of oldest pending job in seconds, or null if none. */
export function oldestPendingAgeSec(db: Database): number | null {
  const row = db
    .query(
      `SELECT created_at FROM jobs WHERE state = 'pending'
       ORDER BY id ASC LIMIT 1`,
    )
    .get() as { created_at: string } | null;
  if (!row?.created_at) return null;
  const ms = Date.now() - Date.parse(row.created_at);
  if (!Number.isFinite(ms) || ms < 0) return 0;
  return Math.floor(ms / 1000);
}

/**
 * Opportunistic retention: terminal jobs + orphan updates older than days.
 * Bounded delete (limit).
 */
export function purgeOldJobs(
  db: Database,
  days = 7,
  limit = 500,
): { jobs: number; updates: number } {
  const cutoff = new Date(Date.now() - days * 86_400_000).toISOString();
  return db.transaction(() => {
    const jobRows = db
      .query(
        `SELECT id, update_id FROM jobs
         WHERE state IN ('delivered', 'needs_manual_retry')
           AND updated_at < ?
         ORDER BY id ASC LIMIT ?`,
      )
      .all(cutoff, limit) as { id: number; update_id: number }[];

    let jobs = 0;
    for (const row of jobRows) {
      db.run("DELETE FROM jobs WHERE id = ?", [row.id]);
      db.run("DELETE FROM updates WHERE update_id = ?", [row.update_id]);
      jobs += 1;
    }

    const orphan = db
      .query(
        `SELECT update_id FROM updates
         WHERE received_at < ?
           AND update_id NOT IN (SELECT update_id FROM jobs)
         LIMIT ?`,
      )
      .all(cutoff, limit) as { update_id: number }[];
    let updates = 0;
    for (const u of orphan) {
      db.run("DELETE FROM updates WHERE update_id = ?", [u.update_id]);
      updates += 1;
    }
    return { jobs, updates };
  })();
}
