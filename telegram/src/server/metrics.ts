/** Funnel + ops metrics. No player prose. */

import type { Repositories } from "../db/repositories";
import { log } from "./logger";

export type FunnelEvent =
  | "onboarding_started"
  | "onboarding_completed"
  | "first_clue"
  | "first_interview"
  | "first_verdict"
  | "case_solved"
  | "daily_cap"
  | "engine_error"
  | "delivery_error";

/** In-process counters (reset on restart — intentional for beta). */
const counters: Record<string, number> = {};

export function bump(name: string, n = 1): void {
  counters[name] = (counters[name] ?? 0) + n;
}

export function getCounters(): Record<string, number> {
  return { ...counters };
}

export function funnel(
  event: FunnelEvent,
  fields: {
    telegram_user_id?: number;
    request_id?: string;
    operation?: string;
    status?: string;
  } = {},
): void {
  bump(`funnel_${event}`);
  log({
    msg: "funnel",
    event,
    status: fields.status ?? "ok",
    // Hash-ish short id only — never raw user content
    user_hash: fields.telegram_user_id
      ? `u${(fields.telegram_user_id % 9973).toString(16)}`
      : undefined,
    request_id: fields.request_id,
    operation: fields.operation,
  });
}

export interface HealthMetrics {
  pending_jobs: number;
  running_jobs: number;
  failed_delivery: number;
  needs_manual_retry: number;
  oldest_pending_age_sec: number | null;
  counters: Record<string, number>;
}

export function collectHealthMetrics(repos: Repositories): HealthMetrics {
  return {
    pending_jobs: repos.countJobsByState("pending"),
    running_jobs: repos.countJobsByState("running"),
    failed_delivery: repos.countJobsByState("failed_delivery"),
    needs_manual_retry: repos.countJobsByState("needs_manual_retry"),
    oldest_pending_age_sec: repos.oldestPendingAgeSec(),
    counters: getCounters(),
  };
}
