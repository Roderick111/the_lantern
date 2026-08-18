import type { JobPayload, JobRow, StoredReply } from "../domain/types";
import { LLM_OPERATIONS } from "../domain/types";
import { t } from "../i18n/strings";
import { funnel } from "../server/metrics";
import type { OpContext } from "./op_context";
import { langOf } from "./op_context";
import { handleLocal } from "./ops_local";
import {
  handleBegin,
  handleCasebook,
  handleInvestigate,
  handleInterrogate,
  handleMove,
  handleOnboard,
  handlePresent,
  handleReset,
  handleSelectWitness,
  handleSettings,
  handleVerdict,
} from "./ops_play";

export type { OpContext } from "./op_context";

export async function executeJob(
  ctx: OpContext,
  job: JobRow,
): Promise<StoredReply> {
  const payload = JSON.parse(job.payload) as JobPayload;
  const userId = job.telegram_user_id;
  const lang = langOf(ctx.repos, userId);

  if (LLM_OPERATIONS.has(job.operation) && !ctx.featureLlmTurns) {
    return { reply_text: t(lang, "feature_disabled") };
  }

  switch (job.operation) {
    case "local_reply":
    case "start_placeholder":
      return handleLocal(ctx, userId, lang, payload);
    case "onboard": {
      if (payload.kind === "command_start") {
        const step = ctx.repos.getSession(userId)?.onboarding_step;
        if (step === "need_language") {
          funnel("onboarding_started", {
            telegram_user_id: userId,
            request_id: job.request_id,
          });
        }
      }
      return handleOnboard(ctx, userId, lang, payload);
    }
    case "settings_update":
      return handleSettings(ctx, job, userId, lang, payload);
    case "briefing_complete": {
      const reply = await handleBegin(ctx, job, userId, lang);
      funnel("onboarding_completed", {
        telegram_user_id: userId,
        request_id: job.request_id,
      });
      return reply;
    }
    case "investigate": {
      const reply = await handleInvestigate(ctx, job, userId, lang, payload);
      if (reply.notices?.length) {
        funnel("first_clue", {
          telegram_user_id: userId,
          request_id: job.request_id,
          operation: "investigate",
        });
      }
      return reply;
    }
    case "interrogate": {
      const reply = await handleInterrogate(ctx, job, userId, lang, payload);
      funnel("first_interview", {
        telegram_user_id: userId,
        request_id: job.request_id,
        operation: "interrogate",
      });
      return reply;
    }
    case "present_evidence":
      return handlePresent(ctx, job, userId, lang, payload);
    case "change_location":
      return handleMove(ctx, job, userId, lang, payload);
    case "select_witness":
      return handleSelectWitness(ctx, userId, lang, payload);
    case "casebook":
      return handleCasebook(ctx, userId, lang);
    case "reset_case":
      return handleReset(ctx, job, userId, lang);
    case "submit_verdict": {
      const reply = await handleVerdict(ctx, job, userId, lang, payload);
      funnel("first_verdict", {
        telegram_user_id: userId,
        request_id: job.request_id,
        operation: "submit_verdict",
      });
      if (reply.case_solved) {
        funnel("case_solved", {
          telegram_user_id: userId,
          request_id: job.request_id,
        });
      }
      return reply;
    }
    default:
      return { reply_text: t(lang, "unknown_callback") };
  }
}
