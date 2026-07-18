import type { Language } from "../../src/domain/types";

export type ApiError = { ok: false; error: string; status: number };

let csrf = "";
let language: Language = "en";

export function getLanguage(): Language {
  return language;
}

export function setLanguage(lang: Language): void {
  language = lang;
}

function tgInitData(): string {
  const w = window as unknown as {
    Telegram?: { WebApp?: { initData?: string } };
  };
  return w.Telegram?.WebApp?.initData ?? "";
}

export async function ensureSession(): Promise<{ language: Language } | ApiError> {
  if (!navigator.onLine) return { ok: false, error: "offline", status: 0 };
  const initData = tgInitData();
  if (!initData) {
    // Dev fallback: only works if server allows tests; show expired
    return { ok: false, error: "session_expired", status: 401 };
  }
  try {
    const res = await fetch("/miniapp/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ initData }),
    });
    const data = (await res.json()) as {
      ok?: boolean;
      csrf?: string;
      language?: Language;
      error?: string;
    };
    if (!res.ok || !data.ok || !data.csrf) {
      return {
        ok: false,
        error: data.error ?? "session_expired",
        status: res.status,
      };
    }
    csrf = data.csrf;
    language = data.language === "ru" ? "ru" : "en";
    return { language };
  } catch {
    return { ok: false, error: "offline", status: 0 };
  }
}

async function api<T>(
  path: string,
  init: RequestInit = {},
): Promise<T | ApiError> {
  if (!navigator.onLine) return { ok: false, error: "offline", status: 0 };
  try {
    const headers = new Headers(init.headers);
    if (init.method && init.method !== "GET") {
      headers.set("x-csrf-token", csrf);
      if (!headers.has("Content-Type") && init.body) {
        headers.set("Content-Type", "application/json");
      }
    }
    const res = await fetch(`/miniapp${path}`, {
      ...init,
      headers,
      credentials: "include",
    });
    const data = (await res.json()) as T & { ok?: boolean; error?: string };
    if (res.status === 401) {
      return { ok: false, error: "session_expired", status: 401 };
    }
    if (!res.ok) {
      return {
        ok: false,
        error: data.error ?? "error_generic",
        status: res.status,
      };
    }
    return data as T;
  } catch {
    return { ok: false, error: "offline", status: 0 };
  }
}

export function isApiError(v: unknown): v is ApiError {
  return (
    typeof v === "object" &&
    v !== null &&
    "ok" in v &&
    (v as ApiError).ok === false
  );
}

export const miniApi = {
  casebook: () => api<Casebook>("/casebook"),
  evidence: () => api<EvidenceList>("/evidence"),
  witnesses: () => api<WitnessList>("/witnesses"),
  selectWitness: (id: string) =>
    api<{ ok: true; close: true }>(`/witnesses/${id}/select`, { method: "POST" }),
  presentEvidence: (witnessId: string, evidenceId: string) =>
    api<{ ok: true; close: true }>(
      `/witnesses/${witnessId}/evidence/${evidenceId}`,
      { method: "POST" },
    ),
  verdictOptions: () => api<VerdictOptions>("/verdict/options"),
  submitVerdict: (body: {
    accused_suspect_id: string;
    evidence_cited: string[];
    reasoning: string;
    request_id: string;
  }) =>
    api<VerdictQueued>("/verdict", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export interface Casebook {
  case_id: string;
  title: string;
  synopsis: string;
  current_location: { id: string; name: string };
  visited_locations: { id: string; name: string }[];
  evidence_count: number;
  llm_turns_used: number;
  llm_turns_limit: number;
  verdict_attempts_remaining: number;
  case_solved: boolean;
  briefing_completed: boolean;
  rites: { id: string; name: string; help: string }[];
  language: Language;
}

export interface EvidenceList {
  evidence: {
    id: string;
    name: string;
    description: string;
    type: string;
    location_id: string;
    location_name: string;
  }[];
  language: Language;
}

export interface WitnessList {
  witnesses: { id: string; name: string; bio: string; selected: boolean }[];
  selected_witness_id: string | null;
  language: Language;
}

export interface VerdictOptions {
  suspects: { id: string; name: string }[];
  evidence: { id: string; name: string }[];
  attempts_remaining: number;
  case_solved: boolean;
  language: Language;
}

export interface VerdictQueued {
  ok: true;
  queued: boolean;
  request_id: string;
  close: true;
}

export function closeMiniApp(): void {
  const w = window as unknown as {
    Telegram?: { WebApp?: { close?: () => void } };
  };
  w.Telegram?.WebApp?.close?.();
}

export function readyMiniApp(): void {
  const w = window as unknown as {
    Telegram?: {
      WebApp?: {
        ready?: () => void;
        expand?: () => void;
        BackButton?: {
          show: () => void;
          hide: () => void;
          onClick: (cb: () => void) => void;
          offClick: (cb: () => void) => void;
        };
      };
    };
  };
  w.Telegram?.WebApp?.ready?.();
  w.Telegram?.WebApp?.expand?.();
}

export function newRequestId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
