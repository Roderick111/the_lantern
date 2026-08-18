import { z } from "zod";

export const SessionRequestSchema = z
  .object({
    initData: z.string().min(1).max(4096),
  })
  .strict();

export const SessionResponseSchema = z
  .object({
    ok: z.literal(true),
    language: z.enum(["en", "ru"]),
    csrf: z.string(),
    expires_at: z.number(),
  })
  .strict();

export const CasebookResponseSchema = z
  .object({
    case_id: z.string(),
    title: z.string(),
    synopsis: z.string(),
    current_location: z.object({ id: z.string(), name: z.string() }).strict(),
    visited_locations: z.array(
      z.object({ id: z.string(), name: z.string() }).strict(),
    ),
    evidence_count: z.number(),
    llm_turns_used: z.number(),
    llm_turns_limit: z.number(),
    verdict_attempts_remaining: z.number(),
    case_solved: z.boolean(),
    briefing_completed: z.boolean(),
    rites: z.array(
      z.object({ id: z.string(), name: z.string(), help: z.string() }).strict(),
    ),
    language: z.enum(["en", "ru"]),
  })
  .strict();

export const EvidenceItemSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    description: z.string(),
    type: z.string(),
    location_id: z.string(),
    location_name: z.string(),
  })
  .strict();

export const EvidenceResponseSchema = z
  .object({
    case_id: z.string(),
    evidence: z.array(EvidenceItemSchema),
    language: z.enum(["en", "ru"]),
  })
  .strict();

export const WitnessItemSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    bio: z.string(),
    selected: z.boolean(),
  })
  .strict();

export const WitnessesResponseSchema = z
  .object({
    case_id: z.string(),
    witnesses: z.array(WitnessItemSchema),
    selected_witness_id: z.string().nullable(),
    language: z.enum(["en", "ru"]),
  })
  .strict();

export const SelectWitnessResponseSchema = z
  .object({
    ok: z.literal(true),
    witness_id: z.string(),
    close: z.literal(true),
  })
  .strict();

export const PresentEvidenceResponseSchema = z
  .object({
    ok: z.literal(true),
    queued: z.boolean(),
    request_id: z.string(),
    close: z.literal(true),
  })
  .strict();

export const VerdictOptionsSchema = z
  .object({
    suspects: z.array(
      z.object({ id: z.string(), name: z.string() }).strict(),
    ),
    evidence: z.array(
      z.object({ id: z.string(), name: z.string() }).strict(),
    ),
    attempts_remaining: z.number(),
    case_solved: z.boolean(),
    language: z.enum(["en", "ru"]),
  })
  .strict();

export const VerdictRequestSchema = z
  .object({
    accused_suspect_id: z.string().min(1).max(64).regex(/^[a-zA-Z0-9_-]+$/),
    evidence_cited: z.array(z.string().max(64)).max(40).default([]),
    reasoning: z.string().min(1).max(2000),
    request_id: z.string().min(1).max(128).regex(/^[\x20-\x7E]+$/),
  })
  .strict();

export const VerdictResponseSchema = z
  .object({
    ok: z.literal(true),
    queued: z.boolean(),
    request_id: z.string(),
    close: z.literal(true),
  })
  .strict();

export const ErrorBodySchema = z
  .object({
    ok: z.literal(false),
    error: z.string(),
  })
  .strict();
