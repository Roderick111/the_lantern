/** Domain types for Telegram gateway. */

export type ChatMode =
  | { kind: "investigation" }
  | { kind: "witness"; witnessId: string };

export type EntitlementStatus = "free" | "owned" | "locked";

export type JobState =
  | "pending"
  | "running"
  | "engine_complete"
  | "delivered"
  | "failed_delivery"
  | "needs_manual_retry";

export type JobOperation =
  | "local_reply"
  | "onboard"
  | "investigate"
  | "interrogate"
  | "present_evidence"
  | "submit_verdict"
  | "change_location"
  | "briefing_complete"
  | "settings_update"
  | "reset_case"
  | "select_witness"
  | "casebook"
  | "start_placeholder"; // legacy Phase 2; treated as onboard/local

export type Language = "en" | "ru";

export type OnboardingStep = "need_language" | "need_begin" | "active";

export interface TelegramUserRow {
  telegram_user_id: number;
  chat_id: number;
  player_id: string | null;
  player_token: string | null;
  language: Language;
  created_at: string;
  updated_at: string;
}

export interface SessionRow {
  telegram_user_id: number;
  case_id: string;
  mode: "investigation" | "witness";
  witness_id: string | null;
  onboarding_step: OnboardingStep;
  pending_json: string | null;
  updated_at: string;
}

export interface JobRow {
  id: number;
  update_id: number;
  telegram_user_id: number;
  request_id: string;
  operation: JobOperation;
  payload: string;
  state: JobState;
  engine_response: string | null;
  delivery_status: string | null;
  delivery_error: string | null;
  attempts: number;
  engine_dispatched: number;
  created_at: string;
  updated_at: string;
}

export interface InlineButton {
  text: string;
  callback_data?: string;
  web_app?: { url: string };
}

export interface StoredReply {
  reply_text: string;
  /** Extra notices (e.g. evidence discovery), sent as separate messages before main. */
  notices?: string[];
  buttons?: InlineButton[][];
  /** Optional photo to send before text (path or file_id). */
  photo?: {
    kind: "location" | "witness";
    mediaId: string;
    path?: string;
    fileId?: string;
    caption?: string;
  };
  parse_mode?: "HTML";
}

export interface JobPayload {
  chatId: number;
  /** Player text — needed for engine; never log. */
  text?: string;
  callbackData?: string;
  kind: string;
  /** Extra structured fields for multi-step flows. */
  meta?: Record<string, string>;
}

export interface PendingVerdict {
  accused_suspect_id: string;
  evidence_cited: string[];
}

export const DAILY_LLM_LIMIT = 40;
export const FREE_CASE_ID = "case_001";
export const TELEGRAM_MAX_MESSAGE = 4096;

export const LLM_OPERATIONS = new Set<JobOperation>([
  "investigate",
  "interrogate",
  "present_evidence",
  "submit_verdict",
]);
