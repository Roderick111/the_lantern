/** grammY handlers — Phase 3 chat loop. */

import { Bot, type Context, InputFile } from "grammy";
import type { Repositories } from "../db/repositories";
import { handleTelegramUpdate } from "./webhook";
import type { WorkerDeps } from "../jobs/worker";
import { processUser } from "../jobs/worker";
import { t } from "../i18n/strings";
import type { Language } from "../domain/types";
import { existsSync } from "node:fs";

export function createBot(
  token: string,
  repos: Repositories,
  workerDeps: WorkerDeps,
  featureNewSessions: boolean,
): Bot {
  const bot = new Bot(token);

  bot.command("start", async (ctx) => {
    await enqueueFromContext(ctx, repos, workerDeps, featureNewSessions);
  });

  bot.command("help", async (ctx) => {
    await enqueueFromContext(ctx, repos, workerDeps, featureNewSessions);
  });

  bot.command("casebook", async (ctx) => {
    await enqueueFromContext(ctx, repos, workerDeps, featureNewSessions);
  });

  bot.command("language", async (ctx) => {
    await enqueueFromContext(ctx, repos, workerDeps, featureNewSessions);
  });

  bot.command("reset", async (ctx) => {
    await enqueueFromContext(ctx, repos, workerDeps, featureNewSessions);
  });

  bot.command("support", async (ctx) => {
    await enqueueFromContext(ctx, repos, workerDeps, featureNewSessions);
  });

  bot.command("terms", async (ctx) => {
    await enqueueFromContext(ctx, repos, workerDeps, featureNewSessions);
  });

  bot.on("message", async (ctx) => {
    if (ctx.message.text?.startsWith("/")) return;
    await enqueueFromContext(ctx, repos, workerDeps, featureNewSessions);
  });

  bot.on("callback_query", async (ctx) => {
    // Always ack immediately before engine/network work
    await ctx.answerCallbackQuery().catch(() => undefined);
    await enqueueFromContext(ctx, repos, workerDeps, featureNewSessions);
  });

  return bot;
}

async function enqueueFromContext(
  ctx: Context,
  repos: Repositories,
  workerDeps: WorkerDeps,
  featureNewSessions: boolean,
): Promise<void> {
  const update = ctx.update as unknown as Record<string, unknown>;
  const result = handleTelegramUpdate(repos, update, { featureNewSessions });

  if (result.shouldAckQueued && result.chatId != null) {
    const lang: Language = result.language ?? "en";
    await ctx.api
      .sendMessage(result.chatId, t(lang, "queued"))
      .catch(() => undefined);
  }

  if (result.jobId && ctx.from?.id) {
    await processUser(workerDeps, ctx.from.id);
  }
}

/** Real Telegram delivery bound to grammY bot. */
export function createGrammyDelivery(bot: Bot): WorkerDeps["delivery"] {
  return {
    async sendMessage(chatId, text, opts) {
      await bot.api.sendMessage(chatId, text, {
        parse_mode: opts?.parseMode,
        // web_app + callback_data union not fully expressed in grammY typings
        reply_markup: opts?.replyMarkup as never,
      });
    },
    async sendChatAction(chatId, action) {
      await bot.api.sendChatAction(chatId, action);
    },
    async sendPhoto(chatId, photo, caption) {
      if (photo.fileId) {
        const msg = await bot.api.sendPhoto(chatId, photo.fileId, { caption });
        const sizes = msg.photo;
        const fileId = sizes?.[sizes.length - 1]?.file_id;
        return { fileId };
      }
      if (photo.path && existsSync(photo.path)) {
        const msg = await bot.api.sendPhoto(chatId, new InputFile(photo.path), {
          caption,
        });
        const sizes = msg.photo;
        const fileId = sizes?.[sizes.length - 1]?.file_id;
        return { fileId };
      }
      return {};
    },
  };
}
