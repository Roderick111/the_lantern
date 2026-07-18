/** Process-local cache for engine health probes (MED-01). */

const TTL_MS = 15_000;

let cached: { ok: boolean; at: number } | null = null;

export async function getEngineHealth(
  check: () => Promise<boolean>,
): Promise<boolean> {
  const now = Date.now();
  if (cached && now - cached.at < TTL_MS) return cached.ok;
  const ok = await check();
  cached = { ok, at: now };
  return ok;
}

/** Test helper — clear cached health state. */
export function resetEngineHealthCache(): void {
  cached = null;
}
