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
 * Bounded delete (limit). MED-08: bulk DELETE instead of per-row loops.
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
    if (jobRows.length > 0) {
      const ids = jobRows.map((r) => r.id);
      const updateIds = jobRows.map((r) => r.update_id);
      const ph = ids.map(() => "?").join(",");
      db.run(`DELETE FROM jobs WHERE id IN (${ph})`, ids);
      db.run(`DELETE FROM updates WHERE update_id IN (${ph})`, updateIds);
      jobs = jobRows.length;
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
    if (orphan.length > 0) {
      const oids = orphan.map((u) => u.update_id);
      const ph = oids.map(() => "?").join(",");
      db.run(`DELETE FROM updates WHERE update_id IN (${ph})`, oids);
      updates = orphan.length;
    }
    return { jobs, updates };
  })();
}
