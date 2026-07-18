import type { Repositories } from "../db/repositories";
import type { JobOperation, JobPayload } from "../domain/types";
import { parseCallback } from "../domain/callbacks";

export type ExtractedUpdate = {
  telegramUserId: number;
  chatId: number;
  requestId: string;
  operation: JobOperation;
  payload: JobPayload;
};

export function extractUserAndOp(
  repos: Repositories,
  update: Record<string, unknown>,
): {
  telegramUserId: number;
  chatId: number;
  requestId: string;
  operation: JobOperation;
  payload: JobPayload;
} | null {
  if (update.message && typeof update.message === "object") {
    return extractMessage(repos, update);
  }
  if (update.callback_query && typeof update.callback_query === "object") {
    return extractCallback(repos, update);
  }
  if (update.my_chat_member && typeof update.my_chat_member === "object") {
    const m = update.my_chat_member as {
      from?: { id?: number };
      chat?: { id?: number };
    };
    if (!m.from?.id || m.chat?.id === undefined) return null;
    const updateId = update.update_id as number;
    return {
      telegramUserId: m.from.id,
      chatId: m.chat.id,
      requestId: `tg-mcm-${updateId}`,
      operation: "local_reply",
      payload: { chatId: m.chat.id, kind: "my_chat_member" },
    };
  }
  return null;
}
function extractMessage(
  repos: Repositories,
  update: Record<string, unknown>,
): {
  telegramUserId: number;
  chatId: number;
  requestId: string;
  operation: JobOperation;
  payload: JobPayload;
} | null {
  const msg = update.message as Record<string, unknown>;
  const from = msg.from as { id?: number } | undefined;
  const chat = msg.chat as { id?: number; type?: string } | undefined;
  if (!from?.id || chat?.id === undefined) return null;

  // Private chats only
  if (chat.type && chat.type !== "private") {
    return {
      telegramUserId: from.id,
      chatId: chat.id,
      requestId: `tg-${update.update_id as number}`,
      operation: "local_reply",
      payload: { chatId: chat.id, kind: "non_private" },
    };
  }

  const text = typeof msg.text === "string" ? msg.text : undefined;
  const hasUnsupportedMedia =
    msg.photo || msg.voice || msg.video || msg.document || msg.sticker;

  const updateId = update.update_id as number;
  const requestId = `tg-${updateId}`;
  const session = repos.getSession(from.id);
  const onboarding = session?.onboarding_step ?? "need_language";
  // MED-10: corrupt pending_json must not crash webhook
  let pending: { kind?: string } | null = null;
  if (session?.pending_json) {
    try {
      pending = JSON.parse(session.pending_json) as { kind?: string };
    } catch {
      pending = null;
    }
  }

  if (hasUnsupportedMedia && !text) {
    return {
      telegramUserId: from.id,
      chatId: chat.id,
      requestId,
      operation: "local_reply",
      payload: { chatId: chat.id, kind: "unsupported_media" },
    };
  }

  if (text?.startsWith("/")) {
    const cmd = text.split(/\s+/)[0].split("@")[0].toLowerCase();
    return commandJob(from.id, chat.id, requestId, cmd);
  }

  if (!text) {
    return {
      telegramUserId: from.id,
      chatId: chat.id,
      requestId,
      operation: "local_reply",
      payload: { chatId: chat.id, kind: "unsupported_media" },
    };
  }

  // Verdict reasoning step
  if (pending?.kind === "awaiting_verdict_reasoning") {
    return {
      telegramUserId: from.id,
      chatId: chat.id,
      requestId,
      operation: "submit_verdict",
      payload: { chatId: chat.id, text, kind: "verdict_reasoning" },
    };
  }

  if (onboarding === "need_language") {
    return {
      telegramUserId: from.id,
      chatId: chat.id,
      requestId,
      operation: "onboard",
      payload: { chatId: chat.id, text, kind: "need_language" },
    };
  }

  if (onboarding === "need_begin") {
    return {
      telegramUserId: from.id,
      chatId: chat.id,
      requestId,
      operation: "local_reply",
      payload: { chatId: chat.id, kind: "need_begin" },
    };
  }

  // Active play: route by mode
  if (session?.mode === "witness" && session.witness_id) {
    return {
      telegramUserId: from.id,
      chatId: chat.id,
      requestId,
      operation: "interrogate",
      payload: {
        chatId: chat.id,
        text,
        kind: "interrogate",
        meta: { witnessId: session.witness_id },
      },
    };
  }

  return {
    telegramUserId: from.id,
    chatId: chat.id,
    requestId,
    operation: "investigate",
    payload: { chatId: chat.id, text, kind: "investigate" },
  };
}

function commandJob(
  userId: number,
  chatId: number,
  requestId: string,
  cmd: string,
): {
  telegramUserId: number;
  chatId: number;
  requestId: string;
  operation: JobOperation;
  payload: JobPayload;
} {
  switch (cmd) {
    case "/start":
      return {
        telegramUserId: userId,
        chatId,
        requestId,
        operation: "onboard",
        payload: { chatId, kind: "command_start" },
      };
    case "/help":
      return {
        telegramUserId: userId,
        chatId,
        requestId,
        operation: "local_reply",
        payload: { chatId, kind: "command_help" },
      };
    case "/casebook":
      return {
        telegramUserId: userId,
        chatId,
        requestId,
        operation: "casebook",
        payload: { chatId, kind: "command_casebook" },
      };
    case "/language":
      return {
        telegramUserId: userId,
        chatId,
        requestId,
        operation: "local_reply",
        payload: { chatId, kind: "command_language" },
      };
    case "/reset":
      return {
        telegramUserId: userId,
        chatId,
        requestId,
        operation: "local_reply",
        payload: { chatId, kind: "command_reset" },
      };
    case "/support":
      return {
        telegramUserId: userId,
        chatId,
        requestId,
        operation: "local_reply",
        payload: { chatId, kind: "command_support" },
      };
    case "/terms":
      return {
        telegramUserId: userId,
        chatId,
        requestId,
        operation: "local_reply",
        payload: { chatId, kind: "command_terms" },
      };
    default:
      return {
        telegramUserId: userId,
        chatId,
        requestId,
        operation: "local_reply",
        payload: { chatId, kind: "command_help" },
      };
  }
}

function extractCallback(
  repos: Repositories,
  update: Record<string, unknown>,
): {
  telegramUserId: number;
  chatId: number;
  requestId: string;
  operation: JobOperation;
  payload: JobPayload;
} | null {
  const cq = update.callback_query as Record<string, unknown>;
  const from = cq.from as { id?: number } | undefined;
  const message = cq.message as { chat?: { id?: number } } | undefined;
  const chatId = message?.chat?.id;
  if (!from?.id || chatId === undefined) return null;

  const updateId = update.update_id as number;
  const data = typeof cq.data === "string" ? cq.data.slice(0, 64) : undefined;
  const action = parseCallback(data);
  const requestId = `tg-cb-${updateId}`;

  // Ensure session row exists for mode reads
  repos.ensureUser(from.id, chatId);
  const session = repos.getSession(from.id);

  switch (action.type) {
    case "lang":
      return {
        telegramUserId: from.id,
        chatId,
        requestId,
        operation: "settings_update",
        payload: {
          chatId,
          callbackData: data,
          kind: "set_language",
          meta: { language: action.language },
        },
      };
    case "begin":
      return {
        telegramUserId: from.id,
        chatId,
        requestId,
        operation: "briefing_complete",
        payload: { chatId, callbackData: data, kind: "begin" },
      };
    case "nav":
      if (action.target === "casebook") {
        return {
          telegramUserId: from.id,
          chatId,
          requestId,
          operation: "casebook",
          payload: { chatId, callbackData: data, kind: "nav_casebook" },
        };
      }
      if (action.target === "move") {
        return {
          telegramUserId: from.id,
          chatId,
          requestId,
          operation: "local_reply",
          payload: { chatId, callbackData: data, kind: "nav_move" },
        };
      }
      if (action.target === "witnesses") {
        return {
          telegramUserId: from.id,
          chatId,
          requestId,
          operation: "local_reply",
          payload: { chatId, callbackData: data, kind: "nav_witnesses" },
        };
      }
      if (action.target === "present") {
        return {
          telegramUserId: from.id,
          chatId,
          requestId,
          operation: "local_reply",
          payload: { chatId, callbackData: data, kind: "nav_present" },
        };
      }
      if (action.target === "verdict") {
        return {
          telegramUserId: from.id,
          chatId,
          requestId,
          operation: "local_reply",
          payload: { chatId, callbackData: data, kind: "nav_verdict" },
        };
      }
      break;
    case "move":
      return {
        telegramUserId: from.id,
        chatId,
        requestId,
        operation: "change_location",
        payload: {
          chatId,
          callbackData: data,
          kind: "change_location",
          meta: { locationId: action.locationId },
        },
      };
    case "wit":
      return {
        telegramUserId: from.id,
        chatId,
        requestId,
        operation: "select_witness",
        payload: {
          chatId,
          callbackData: data,
          kind: "select_witness",
          meta: { witnessId: action.witnessId },
        },
      };
    case "end_wit":
      return {
        telegramUserId: from.id,
        chatId,
        requestId,
        operation: "local_reply",
        payload: { chatId, callbackData: data, kind: "end_witness" },
      };
    case "ev":
      return {
        telegramUserId: from.id,
        chatId,
        requestId,
        operation: "present_evidence",
        payload: {
          chatId,
          callbackData: data,
          kind: "present_evidence",
          meta: {
            evidenceId: action.evidenceId,
            witnessId: session?.witness_id ?? "",
          },
        },
      };
    case "verdict":
      return {
        telegramUserId: from.id,
        chatId,
        requestId,
        operation: "local_reply",
        payload: {
          chatId,
          callbackData: data,
          kind: `verdict_${action.step}`,
          meta: action.id ? { id: action.id } : undefined,
        },
      };
    case "reset":
      if (action.confirm) {
        return {
          telegramUserId: from.id,
          chatId,
          requestId,
          operation: "reset_case",
          payload: { chatId, callbackData: data, kind: "reset_confirm" },
        };
      }
      return {
        telegramUserId: from.id,
        chatId,
        requestId,
        operation: "local_reply",
        payload: { chatId, callbackData: data, kind: "reset_cancel" },
      };
    case "retry": {
      // Requeue before enqueue so needs_manual_retry does not block claim.
      const requeued = repos.requeueOldestManualJob(from.id);
      return {
        telegramUserId: from.id,
        chatId,
        requestId,
        operation: "local_reply",
        payload: {
          chatId,
          callbackData: data,
          kind: requeued != null ? "retry_job" : "retry_hint",
          meta: requeued != null ? { requeuedJobId: String(requeued) } : undefined,
        },
      };
    }
    default:
      break;
  }

  return {
    telegramUserId: from.id,
    chatId,
    requestId,
    operation: "local_reply",
    payload: { chatId, callbackData: data, kind: "unknown_callback" },
  };
}
