import type { JobPayload, Language, PendingVerdict, StoredReply } from "../domain/types";
import { FREE_CASE_ID } from "../domain/types";
import { isWitnessId, WITNESS_NAMES } from "../domain/case_meta";
import { t } from "../i18n/strings";
import {
  beginKeyboard,
  languageKeyboard,
  moveKeyboard,
  presentEvidenceKeyboard,
  resetKeyboard,
  retryKeyboard,
  verdictEvidenceKeyboard,
  verdictSuspectKeyboard,
  witnessesKeyboard,
} from "../bot/keyboards";
import type { OpContext } from "./op_context";
import { invButtons, witButtons } from "./op_context";

export async function handleLocal(
  ctx: OpContext,
  userId: number,
  lang: Language,
  payload: JobPayload,
): Promise<StoredReply> {
  const kind = payload.kind;

  if (kind === "unsupported_media" || kind === "non_private") {
    return { reply_text: t(lang, "unsupported_media") };
  }
  if (kind === "command_help" || kind === "my_chat_member") {
    return { reply_text: t(lang, "help") };
  }
  if (kind === "command_support") {
    return { reply_text: t(lang, "support") };
  }
  if (kind === "command_terms") {
    return { reply_text: t(lang, "terms") };
  }
  if (kind === "command_language") {
    return {
      reply_text: t(lang, "choose_language"),
      buttons: languageKeyboard(),
    };
  }
  if (kind === "command_reset") {
    return {
      reply_text: t(lang, "reset_confirm"),
      buttons: resetKeyboard(lang),
    };
  }
  if (kind === "reset_cancel") {
    return { reply_text: t(lang, "reset_cancelled"), buttons: invButtons(lang, ctx.publicUrl) };
  }
  if (kind === "need_begin") {
    return {
      reply_text: t(lang, "need_begin"),
      buttons: beginKeyboard(lang),
    };
  }
  if (kind === "nav_move") {
    try {
      await ctx.engine.ensureSession(userId);
      const snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
      return {
        reply_text: t(lang, "move_prompt"),
        buttons: moveKeyboard(lang, snap.available_locations),
      };
    } catch {
      return { reply_text: t(lang, "move_prompt"), buttons: moveKeyboard(lang) };
    }
  }
  if (kind === "nav_witnesses") {
    try {
      await ctx.engine.ensureSession(userId);
      const snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
      return {
        reply_text: t(lang, "witnesses_prompt"),
        buttons: witnessesKeyboard(lang, snap.available_witnesses),
      };
    } catch {
      return {
        reply_text: t(lang, "witnesses_prompt"),
        buttons: witnessesKeyboard(lang),
      };
    }
  }
  if (kind === "nav_verdict") {
    ctx.repos.setPendingJson(userId, null);
    return {
      reply_text: t(lang, "verdict_suspect"),
      buttons: verdictSuspectKeyboard(lang),
    };
  }
  if (kind === "nav_present") {
    return presentPicker(ctx, userId, lang);
  }
  if (kind === "end_witness") {
    ctx.repos.setSessionMode(userId, "investigation", null);
    return {
      reply_text: t(lang, "interview_ended"),
      buttons: invButtons(lang, ctx.publicUrl),
    };
  }
  if (kind === "verdict_suspect" && payload.meta?.id) {
    const pending: PendingVerdict & { kind: string } = {
      kind: "verdict_pick",
      accused_suspect_id: payload.meta.id,
      evidence_cited: [],
    };
    ctx.repos.setPendingJson(userId, pending);
    return enrichVerdictEvidence(ctx, userId, lang, pending);
  }
  if (kind === "verdict_toggle_ev" && payload.meta?.id) {
    const cur = ctx.repos.getPendingVerdict(userId);
    if (!cur) {
      return {
        reply_text: t(lang, "verdict_suspect"),
        buttons: verdictSuspectKeyboard(lang),
      };
    }
    const set = new Set(cur.evidence_cited);
    if (set.has(payload.meta.id)) set.delete(payload.meta.id);
    else set.add(payload.meta.id);
    const next = {
      kind: "verdict_pick",
      accused_suspect_id: cur.accused_suspect_id,
      evidence_cited: [...set],
    };
    ctx.repos.setPendingJson(userId, next);
    return enrichVerdictEvidence(ctx, userId, lang, next);
  }
  if (kind === "verdict_confirm") {
    const cur = ctx.repos.getPendingVerdict(userId);
    if (!cur) {
      return {
        reply_text: t(lang, "verdict_suspect"),
        buttons: verdictSuspectKeyboard(lang),
      };
    }
    ctx.repos.setPendingJson(userId, {
      kind: "awaiting_verdict_reasoning",
      ...cur,
    });
    return { reply_text: t(lang, "verdict_need_reasoning") };
  }
  if (kind === "verdict_cancel") {
    ctx.repos.setPendingJson(userId, null);
    return {
      reply_text: t(lang, "reset_cancelled"),
      buttons: invButtons(lang, ctx.publicUrl),
    };
  }
  if (kind === "retry_hint") {
    return {
      reply_text: t(lang, "engine_unknown"),
      buttons: invButtons(lang, ctx.publicUrl),
    };
  }
  if (kind === "unknown_callback") {
    return { reply_text: t(lang, "unknown_callback") };
  }

  return { reply_text: t(lang, "help") };
}

export async function presentPicker(
  ctx: OpContext,
  userId: number,
  lang: Language,
): Promise<StoredReply> {
  const session = ctx.repos.getSession(userId);
  const witnessId = session?.witness_id;
  if (!witnessId) {
    return {
      reply_text: t(lang, "witnesses_prompt"),
      buttons: witnessesKeyboard(lang),
    };
  }
  const wname =
    isWitnessId(witnessId) && lang === "ru"
      ? WITNESS_NAMES[witnessId].ru
      : isWitnessId(witnessId)
        ? WITNESS_NAMES[witnessId].en
        : witnessId;

  try {
    await ctx.engine.ensureSession(userId);
    const snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
    if (!snap.discovered_evidence.length) {
      return { reply_text: t(lang, "present_none"), buttons: witButtons(lang, ctx.publicUrl) };
    }
    const names = Object.fromEntries(snap.evidence_details.map((evidence) => [evidence.id, evidence.name]));
    return {
      reply_text: t(lang, "present_prompt", { name: wname }),
      buttons: presentEvidenceKeyboard(snap.discovered_evidence, names),
    };
  } catch {
    return { reply_text: t(lang, "engine_error"), buttons: retryKeyboard(lang) };
  }
}


/** Fix verdict evidence picker with full discovered list. */
export async function enrichVerdictEvidence(
  ctx: OpContext,
  userId: number,
  lang: Language,
  pending: PendingVerdict,
): Promise<StoredReply> {
  try {
    await ctx.engine.ensureSession(userId);
    const snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
    const names = Object.fromEntries(snap.evidence_details.map((evidence) => [evidence.id, evidence.name]));
    const list =
      snap.discovered_evidence.length > 0
        ? snap.discovered_evidence
        : pending.evidence_cited;
    return {
      reply_text: t(lang, "verdict_evidence"),
      buttons: verdictEvidenceKeyboard(
        list,
        names,
        new Set(pending.evidence_cited),
        lang,
      ),
    };
  } catch {
    return {
      reply_text: t(lang, "verdict_evidence"),
      buttons: verdictEvidenceKeyboard(
        pending.evidence_cited,
        Object.fromEntries(pending.evidence_cited.map((id) => [id, id])),
        new Set(pending.evidence_cited),
        lang,
      ),
    };
  }
}
