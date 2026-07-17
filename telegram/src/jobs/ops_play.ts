import { EngineError } from "../engine/client";
import type { JobPayload, JobRow, Language, StoredReply } from "../domain/types";
import { DAILY_LLM_LIMIT, FREE_CASE_ID } from "../domain/types";
import {
  CASE_COVER,
  isLocationId,
  isWitnessId,
  locationCopy,
  locationImageRel,
  WITNESS_NAMES,
  witnessImageRel,
  type WitnessId,
} from "../domain/case_meta";
import { t } from "../i18n/strings";
import {
  beginKeyboard,
  languageKeyboard,
  moveKeyboard,
  verdictSuspectKeyboard,
  witnessesKeyboard,
} from "../bot/keyboards";
import type { TelegramSnapshot } from "../engine/schemas";
import type { OpContext } from "./op_context";
import { invButtons, witButtons, sleep } from "./op_context";
import { presentPicker } from "./ops_local";

function evidenceNotice(lang: Language, ids: string[], names: Record<string, string>) {
  if (!ids.length) return undefined;
  return t(lang, "evidence_found", { list: ids.map((id) => names[id] ?? id).join(", ") });
}

export async function handleOnboard(
  ctx: OpContext,
  userId: number,
  lang: Language,
  payload: JobPayload,
): Promise<StoredReply> {
  if (!ctx.featureNewSessions && !ctx.repos.getUser(userId)?.player_id) {
    return { reply_text: t(lang, "sessions_disabled") };
  }

  const session = ctx.repos.getSession(userId);
  const step = session?.onboarding_step ?? "need_language";

  if (payload.kind === "command_start" && step === "active") {
    try {
      await ctx.engine.ensureSession(userId);
      const snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
      const loc = snap.current_location_view?.name ?? locationLabel(snap.current_location, lang);
      return {
        reply_text:
          t(lang, "resumed") +
          "\n\n" +
          t(lang, "location_line", { name: loc }),
        buttons:
          session?.mode === "witness" ? witButtons(lang, ctx.publicUrl) : invButtons(lang, ctx.publicUrl),
      };
    } catch {
      return {
        reply_text: t(lang, "resumed"),
        buttons: invButtons(lang, ctx.publicUrl),
      };
    }
  }

  if (step === "need_language") {
    return {
      reply_text: t(lang, "choose_language"),
      buttons: languageKeyboard(),
    };
  }

  if (step === "need_begin") {
    let cover = lang === "ru" ? CASE_COVER.ru : CASE_COVER.en;
    try {
      await ctx.engine.ensureSession(userId);
      const snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
      if (snap.case_title && snap.case_description) {
        cover = { title: snap.case_title, body: snap.case_description };
      }
    } catch {
      /* Static fallback only when engine is unavailable. */
    }
    return {
      reply_text: `*${cover.title}*\n\n${cover.body}\n\n${t(lang, "cover_prompt")}`.replace(
        /\*/g,
        "",
      ),
      buttons: beginKeyboard(lang),
    };
  }

  // active default
  return {
    reply_text: t(lang, "resumed"),
    buttons: invButtons(lang, ctx.publicUrl),
  };
}

export async function handleSettings(
  ctx: OpContext,
  job: JobRow,
  userId: number,
  lang: Language,
  payload: JobPayload,
): Promise<StoredReply> {
  const newLang = (payload.meta?.language === "ru" ? "ru" : "en") as Language;
  ctx.repos.setLanguage(userId, newLang);

  if (!ctx.featureNewSessions && !ctx.repos.getUser(userId)?.player_id) {
    return { reply_text: t(newLang, "sessions_disabled") };
  }

  await ctx.engine.ensureSession(userId);
  ctx.repos.markEngineDispatched(job.id);
  await ctx.engine.updateSettings(userId, {
    case_id: FREE_CASE_ID,
    language: newLang,
    slot: "autosave",
    request_id: job.request_id,
  });

  const session = ctx.repos.getSession(userId);
  if (session?.onboarding_step === "need_language") {
    ctx.repos.setOnboardingStep(userId, "need_begin");
  }

  let cover = newLang === "ru" ? CASE_COVER.ru : CASE_COVER.en;
  try {
    const snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
    if (snap.case_title && snap.case_description) {
      cover = { title: snap.case_title, body: snap.case_description };
    }
  } catch {
    /* Static fallback only when engine is unavailable. */
  }
  return {
    reply_text:
      t(newLang, "language_set") +
      `\n\n${cover.title}\n\n${cover.body}\n\n${t(newLang, "cover_prompt")}`,
    buttons: beginKeyboard(newLang),
  };
}

export async function handleBegin(
  ctx: OpContext,
  job: JobRow,
  userId: number,
  lang: Language,
): Promise<StoredReply> {
  await ctx.engine.ensureSession(userId);
  ctx.repos.markEngineDispatched(job.id);
  try {
    await ctx.engine.completeBriefing(userId, FREE_CASE_ID, {
      request_id: job.request_id,
    });
  } catch (err) {
    // Briefing may already be complete
    if (!(err instanceof EngineError && err.code === "bad_request")) {
      // still allow enter
    }
  }
  ctx.repos.setOnboardingStep(userId, "active");
  ctx.repos.setSessionMode(userId, "investigation", null);

  // Starting location (usually library) — image once, localized blurb
  let locationId = "library";
  let snap: TelegramSnapshot | null = null;
  try {
    snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
    if (snap.current_location) locationId = snap.current_location;
  } catch {
    /* default library */
  }
  let copy = locationCopy(locationId, lang);
  try {
    const location = snap?.current_location_view;
    if (location?.id === locationId) {
      copy = { name: location.name, description: location.description };
    }
  } catch {
    /* Static fallback only when engine is unavailable. */
  }
  const reply: StoredReply = {
    reply_text:
      t(lang, "investigation_started") +
      "\n\n" +
      t(lang, "moved_to", {
        name: copy.name,
        description: copy.description,
      }),
    buttons: invButtons(lang, ctx.publicUrl),
  };
  attachLocationPhotoIfNew(ctx, userId, locationId, copy.name, reply);
  return reply;
}

export async function handleInvestigate(
  ctx: OpContext,
  job: JobRow,
  userId: number,
  lang: Language,
  payload: JobPayload,
): Promise<StoredReply> {
  const text = payload.text ?? "";
  await ctx.engine.ensureSession(userId);
  ctx.repos.markEngineDispatched(job.id);

  const res = await callWithConflictRetry(ctx, userId, () =>
    ctx.engine.investigate(userId, {
      player_input: text,
      case_id: FREE_CASE_ID,
      slot: "autosave",
      request_id: job.request_id,
    }),
  );

  ctx.repos.incrementLlmTurns(userId);
  const notice = evidenceNotice(lang, res.new_evidence, res.evidence_names);
  return {
    reply_text: res.narrator_response,
    notices: notice ? [notice] : undefined,
    buttons: invButtons(lang, ctx.publicUrl),
  };
}

export async function handleInterrogate(
  ctx: OpContext,
  job: JobRow,
  userId: number,
  lang: Language,
  payload: JobPayload,
): Promise<StoredReply> {
  const text = payload.text ?? "";
  const witnessId =
    payload.meta?.witnessId ?? ctx.repos.getSession(userId)?.witness_id ?? "";
  if (!witnessId) {
    return {
      reply_text: t(lang, "witnesses_prompt"),
      buttons: witnessesKeyboard(lang),
    };
  }

  await ctx.engine.ensureSession(userId);
  ctx.repos.markEngineDispatched(job.id);

  const res = await callWithConflictRetry(ctx, userId, () =>
    ctx.engine.interrogate(userId, {
      witness_id: witnessId,
      question: text,
      case_id: FREE_CASE_ID,
      slot: "autosave",
      request_id: job.request_id,
    }),
  );

  ctx.repos.incrementLlmTurns(userId);
  return {
    reply_text: res.response,
    buttons: witButtons(lang, ctx.publicUrl),
  };
}

export async function handlePresent(
  ctx: OpContext,
  job: JobRow,
  userId: number,
  lang: Language,
  payload: JobPayload,
): Promise<StoredReply> {
  const evidenceId = payload.meta?.evidenceId ?? "";
  const witnessId =
    payload.meta?.witnessId || ctx.repos.getSession(userId)?.witness_id || "";
  if (!evidenceId || !witnessId) {
    return presentPicker(ctx, userId, lang);
  }

  await ctx.engine.ensureSession(userId);
  ctx.repos.markEngineDispatched(job.id);

  const res = await callWithConflictRetry(ctx, userId, () =>
    ctx.engine.presentEvidence(userId, {
      witness_id: witnessId,
      evidence_id: evidenceId,
      case_id: FREE_CASE_ID,
      slot: "autosave",
      request_id: job.request_id,
    }),
  );

  ctx.repos.incrementLlmTurns(userId);
  return {
    reply_text: res.response,
    buttons: witButtons(lang, ctx.publicUrl),
  };
}

export async function handleMove(
  ctx: OpContext,
  job: JobRow,
  userId: number,
  lang: Language,
  payload: JobPayload,
): Promise<StoredReply> {
  const locationId = payload.meta?.locationId ?? "";
  if (!isLocationId(locationId)) {
    return { reply_text: t(lang, "move_prompt"), buttons: moveKeyboard(lang) };
  }

  await ctx.engine.ensureSession(userId);

  let snap: TelegramSnapshot | null = null;
  try {
    snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
  } catch {
    /* ignore */
  }

  let copy = locationCopy(locationId, lang);

  if (snap?.current_location === locationId) {
    return {
      reply_text: t(lang, "already_there", { name: copy.name }),
      buttons: invButtons(lang, ctx.publicUrl),
    };
  }

  ctx.repos.markEngineDispatched(job.id);
  const changed = await ctx.engine.changeLocation(userId, FREE_CASE_ID, {
    location_id: locationId,
    slot: "autosave",
    request_id: job.request_id,
  });
  copy = {
    name: changed.location.name,
    description: changed.location.description ?? "",
  };

  const reply: StoredReply = {
    reply_text: t(lang, "moved_to", {
      name: copy.name,
      description: copy.description,
    }),
    buttons: invButtons(lang, ctx.publicUrl),
  };
  attachLocationPhotoIfNew(ctx, userId, locationId, copy.name, reply);
  return reply;
}

/** First Telegram send of location image (receipt), not engine visit list. */
function attachLocationPhotoIfNew(
  ctx: OpContext,
  userId: number,
  locationId: string,
  caption: string,
  reply: StoredReply,
): void {
  if (!isLocationId(locationId)) return;
  if (ctx.repos.hasMediaReceipt(userId, "location", locationId)) return;
  reply.photo = {
    kind: "location",
    mediaId: locationId,
    path: `${ctx.assetsPath}/${locationImageRel(locationId)}`,
    fileId: ctx.repos.getMediaFileId(userId, "location", locationId) ?? undefined,
    caption,
  };
}

export async function handleSelectWitness(
  ctx: OpContext,
  userId: number,
  lang: Language,
  payload: JobPayload,
): Promise<StoredReply> {
  const witnessId = payload.meta?.witnessId ?? "";
  if (!isWitnessId(witnessId)) {
    return {
      reply_text: t(lang, "witnesses_prompt"),
      buttons: witnessesKeyboard(lang),
    };
  }

  ctx.repos.setSessionMode(userId, "witness", witnessId);
  let name: string = witnessId;
  try {
    await ctx.engine.ensureSession(userId);
    const snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
    name = snap.available_witnesses.find((witness) => witness.id === witnessId)?.name ?? name;
  } catch {
    const names = WITNESS_NAMES[witnessId as WitnessId];
    name = lang === "ru" ? names.ru : names.en;
  }

  const reply: StoredReply = {
    reply_text: t(lang, "witness_header", { name }),
    buttons: witButtons(lang, ctx.publicUrl),
  };

  if (!ctx.repos.hasMediaReceipt(userId, "witness", witnessId)) {
    reply.photo = {
      kind: "witness",
      mediaId: witnessId,
      path: `${ctx.assetsPath}/${witnessImageRel(witnessId)}`,
      fileId: ctx.repos.getMediaFileId(userId, "witness", witnessId) ?? undefined,
      caption: name,
    };
  }

  return reply;
}

export async function handleCasebook(
  ctx: OpContext,
  userId: number,
  lang: Language,
): Promise<StoredReply> {
  try {
    await ctx.engine.ensureSession(userId);
    const snap = await ctx.engine.snapshot(userId, FREE_CASE_ID);
    const loc = snap.current_location_view?.name ?? locationLabel(snap.current_location, lang);
    const used = ctx.repos.getLlmTurns(userId);
    const evidenceNames = Object.fromEntries(
      snap.evidence_details.map((evidence) => [evidence.id, evidence.name]),
    );
    const list =
      snap.discovered_evidence.length > 0
        ? snap.discovered_evidence.map((id) => evidenceNames[id] ?? id).join(", ")
        : t(lang, "evidence_none");
    const text = [
      t(lang, "casebook_title"),
      t(lang, "location_line", { name: loc }),
      t(lang, "evidence_line", {
        n: snap.discovered_evidence.length,
        list,
      }),
      t(lang, "turns_line", { used, limit: DAILY_LLM_LIMIT }),
      `Attempts left: ${snap.verdict_attempts_remaining}`,
      snap.case_solved ? "Case solved." : "",
    ]
      .filter(Boolean)
      .join("\n");

    const session = ctx.repos.getSession(userId);
    return {
      reply_text: text,
      buttons:
        session?.mode === "witness" ? witButtons(lang, ctx.publicUrl) : invButtons(lang, ctx.publicUrl),
    };
  } catch {
    return { reply_text: t(lang, "casebook_empty"), buttons: beginKeyboard(lang) };
  }
}

export async function handleReset(
  ctx: OpContext,
  userId: number,
  lang: Language,
): Promise<StoredReply> {
  try {
    await ctx.engine.ensureSession(userId);
    await ctx.engine.resetCase(userId, FREE_CASE_ID);
  } catch {
    /* no save is ok */
  }
  ctx.repos.resetTelegramCase(userId, FREE_CASE_ID);
  return {
    reply_text: t(lang, "reset_done"),
    buttons: beginKeyboard(lang),
  };
}

export async function handleVerdict(
  ctx: OpContext,
  job: JobRow,
  userId: number,
  lang: Language,
  payload: JobPayload,
): Promise<StoredReply> {
  const pending = ctx.repos.getPendingVerdict(userId);
  if (!pending) {
    return {
      reply_text: t(lang, "verdict_suspect"),
      buttons: verdictSuspectKeyboard(lang),
    };
  }
  const reasoning = payload.text ?? "Telegram verdict";
  await ctx.engine.ensureSession(userId);
  ctx.repos.markEngineDispatched(job.id);

  const res = await callWithConflictRetry(ctx, userId, () =>
    ctx.engine.submitVerdict(userId, {
      case_id: FREE_CASE_ID,
      slot: "autosave",
      accused_suspect_id: pending.accused_suspect_id,
      reasoning,
      evidence_cited: pending.evidence_cited,
      request_id: job.request_id,
    }),
  );

  ctx.repos.incrementLlmTurns(userId);
  ctx.repos.setPendingJson(userId, null);

  const mentor = res.mentor_feedback;
  const header = res.correct
    ? t(lang, "verdict_result_correct")
    : t(lang, "verdict_result_wrong", { n: res.attempts_remaining });

  const parts = [
    header,
    mentor.analysis,
    mentor.critique,
    mentor.praise,
    mentor.hint ?? "",
    res.reveal ?? "",
    res.wrong_suspect_response ?? "",
  ].filter(Boolean);

  return {
    reply_text: parts.join("\n\n"),
    buttons: invButtons(lang, ctx.publicUrl),
  };
}

function locationLabel(id: string, lang: Language): string {
  return locationCopy(id, lang).name;
}

async function callWithConflictRetry<T>(
  ctx: OpContext,
  userId: number,
  fn: () => Promise<T>,
): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    if (err instanceof EngineError && err.code === "conflict") {
      await sleep(800);
      try {
        return await fn();
      } catch (err2) {
        if (err2 instanceof EngineError && err2.code === "conflict") {
          try {
            await ctx.engine.snapshot(userId, FREE_CASE_ID);
          } catch {
            /* ignore */
          }
        }
        throw err2;
      }
    }
    throw err;
  }
}
