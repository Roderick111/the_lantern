import type { Repositories } from "../db/repositories";
import type { EngineClient } from "../engine/client";
import type { Language } from "../domain/types";
import { investigationKeyboard, witnessKeyboard } from "../bot/keyboards";

export interface OpContext {
  repos: Repositories;
  engine: EngineClient;
  featureNewSessions: boolean;
  featureLlmTurns: boolean;
  assetsPath: string;
  publicUrl?: string;
}

export function langOf(repos: Repositories, userId: number): Language {
  return (repos.getUser(userId)?.language as Language) ?? "en";
}

export function invButtons(lang: Language, publicUrl?: string) {
  return investigationKeyboard(lang, publicUrl);
}

export function witButtons(lang: Language, publicUrl?: string) {
  return witnessKeyboard(lang, publicUrl);
}

export function nextUtcMidnightLabel(): string {
  const d = new Date();
  d.setUTCHours(24, 0, 0, 0);
  return d.toISOString().slice(0, 16) + "Z";
}

export function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
