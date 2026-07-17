/** Callback data encoding — ASCII, short, no player prose. */

export const CB = {
  LANG: "lang",
  BEGIN: "begin",
  NAV: "nav",
  MOVE: "move",
  WIT: "wit",
  END_WIT: "end_wit",
  EV: "ev",
  VERDICT: "verdict",
  RESET: "reset",
  RETRY: "retry",
} as const;

export type CallbackAction =
  | { type: "lang"; language: "en" | "ru" }
  | { type: "begin" }
  | { type: "nav"; target: "casebook" | "witnesses" | "move" | "verdict" | "present" }
  | { type: "move"; locationId: string }
  | { type: "wit"; witnessId: string }
  | { type: "end_wit" }
  | { type: "ev"; evidenceId: string }
  | { type: "verdict"; step: "suspect" | "toggle_ev" | "confirm" | "cancel"; id?: string }
  | { type: "reset"; confirm: boolean }
  | { type: "retry" }
  | { type: "unknown"; raw: string };

export function encodeLang(lang: "en" | "ru"): string {
  return `${CB.LANG}:${lang}`;
}

export function encodeBegin(): string {
  return CB.BEGIN;
}

export function encodeNav(
  target: "casebook" | "witnesses" | "move" | "verdict" | "present",
): string {
  return `${CB.NAV}:${target}`;
}

export function encodeMove(locationId: string): string {
  return `${CB.MOVE}:${locationId}`;
}

export function encodeWitness(witnessId: string): string {
  return `${CB.WIT}:${witnessId}`;
}

export function encodeEndWitness(): string {
  return CB.END_WIT;
}

export function encodePresentEvidence(evidenceId: string): string {
  return `${CB.EV}:${evidenceId}`;
}

export function encodeVerdictSuspect(id: string): string {
  return `${CB.VERDICT}:s:${id}`;
}

export function encodeVerdictToggleEv(id: string): string {
  return `${CB.VERDICT}:e:${id}`;
}

export function encodeVerdictConfirm(): string {
  return `${CB.VERDICT}:ok`;
}

export function encodeVerdictCancel(): string {
  return `${CB.VERDICT}:x`;
}

export function encodeReset(confirm: boolean): string {
  return confirm ? `${CB.RESET}:yes` : `${CB.RESET}:no`;
}

export function encodeRetry(): string {
  return CB.RETRY;
}

export function parseCallback(data: string | undefined): CallbackAction {
  if (!data) return { type: "unknown", raw: "" };
  const parts = data.split(":");
  const head = parts[0];

  if (head === CB.LANG && (parts[1] === "en" || parts[1] === "ru")) {
    return { type: "lang", language: parts[1] };
  }
  if (head === CB.BEGIN) return { type: "begin" };
  if (head === CB.NAV) {
    const t = parts[1];
    if (
      t === "casebook" ||
      t === "witnesses" ||
      t === "move" ||
      t === "verdict" ||
      t === "present"
    ) {
      return { type: "nav", target: t };
    }
  }
  if (head === CB.MOVE && parts[1]) return { type: "move", locationId: parts[1] };
  if (head === CB.WIT && parts[1]) return { type: "wit", witnessId: parts[1] };
  if (head === CB.END_WIT) return { type: "end_wit" };
  if (head === CB.EV && parts[1]) return { type: "ev", evidenceId: parts[1] };
  if (head === CB.VERDICT) {
    if (parts[1] === "s" && parts[2]) {
      return { type: "verdict", step: "suspect", id: parts[2] };
    }
    if (parts[1] === "e" && parts[2]) {
      return { type: "verdict", step: "toggle_ev", id: parts[2] };
    }
    if (parts[1] === "ok") return { type: "verdict", step: "confirm" };
    if (parts[1] === "x") return { type: "verdict", step: "cancel" };
  }
  if (head === CB.RESET) {
    return { type: "reset", confirm: parts[1] === "yes" };
  }
  if (head === CB.RETRY) return { type: "retry" };

  return { type: "unknown", raw: data.slice(0, 64) };
}
