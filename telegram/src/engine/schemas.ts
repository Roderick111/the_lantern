import { z } from "zod";

export const SessionResponseSchema = z
  .object({
    player_id: z.string(),
    token: z.string(),
  })
  .strict();

const StateDeltaSchema = z
  .object({
    case_id: z.string(),
    current_location: z.string(),
    discovered_evidence: z.array(z.string()).default([]),
    visited_locations: z.array(z.string()).default([]),
    save_revision: z.number().default(0),
  })
  .strict()
  .nullable()
  .optional();

export const InvestigateResponseSchema = z
  .object({
    narrator_response: z.string(),
    new_evidence: z.array(z.string()).default([]),
    evidence_names: z.record(z.string()).default({}),
    already_discovered: z.boolean().default(false),
    location_changed: z.string().nullable().optional(),
    updated_state: StateDeltaSchema,
  })
  .strict();

export const InterrogateResponseSchema = z
  .object({
    response: z.string(),
    trust: z.number(),
    trust_delta: z.number().default(0),
    secrets_revealed: z.array(z.string()).default([]),
    secret_texts: z.record(z.string()).default({}),
    updated_state: z.unknown().optional().nullable(),
  })
  .strict();

export const PresentEvidenceResponseSchema = InterrogateResponseSchema;

export const ChangeLocationResponseSchema = z
  .object({
    success: z.boolean(),
    location: z
      .object({
        id: z.string(),
        name: z.string(),
        description: z.string().optional().default(""),
        surface_elements: z.array(z.unknown()).optional(),
        witnesses_present: z.array(z.unknown()).optional(),
      })
      .passthrough(),
    updated_state: z.unknown().optional().nullable(),
  })
  .strict();

export const UpdateSettingsResponseSchema = z
  .object({
    success: z.boolean(),
    message: z.string(),
  })
  .strict();

export const BriefingCompleteResponseSchema = z
  .object({
    success: z.boolean(),
    updated_state: z.unknown().nullable().optional(),
  })
  .passthrough();

export const ResetResponseSchema = z
  .object({
    success: z.boolean(),
    message: z.string(),
  })
  .strict();

export const MentorFeedbackSchema = z
  .object({
    analysis: z.string(),
    fallacies_detected: z.array(z.unknown()).default([]),
    score: z.number(),
    quality: z.string(),
    critique: z.string(),
    praise: z.string(),
    hint: z.string().nullable().optional(),
  })
  .passthrough();

export const SubmitVerdictResponseSchema = z
  .object({
    correct: z.boolean(),
    attempts_remaining: z.number(),
    case_solved: z.boolean(),
    mentor_feedback: MentorFeedbackSchema,
    confrontation: z.unknown().nullable().optional(),
    reveal: z.string().nullable().optional(),
    wrong_suspect_response: z.string().nullable().optional(),
    updated_state: z.unknown().nullable().optional(),
  })
  .strict();

export const TelegramSnapshotSchema = z
  .object({
    case_id: z.string(),
    case_title: z.string().default(""),
    case_description: z.string().default(""),
    current_location: z.string(),
    current_location_view: z
      .object({
        id: z.string(),
        name: z.string(),
        description: z.string().default(""),
      })
      .nullable()
      .optional(),
    available_locations: z
      .array(
        z.object({ id: z.string(), name: z.string(), description: z.string().default("") }),
      )
      .default([]),
    visited_locations: z.array(z.string()).default([]),
    discovered_evidence: z.array(z.string()).default([]),
    evidence_details: z
      .array(
        z.object({
          id: z.string(),
          name: z.string(),
          description: z.string().default(""),
          location_found: z.string().default(""),
          type: z.string().default(""),
          location_name: z.string().default(""),
        }),
      )
      .default([]),
    briefing_completed: z.boolean().default(false),
    language: z.string().default("en"),
    save_revision: z.number().default(0),
    available_witnesses: z
      .array(
        z
          .object({ id: z.string(), name: z.string(), description: z.string().default("") })
          .strict(),
      )
      .default([]),
    verdict_attempts_remaining: z.number().default(10),
    case_solved: z.boolean().default(false),
  })
  .strict();

export type SessionResponse = z.infer<typeof SessionResponseSchema>;
export type InvestigateResponse = z.infer<typeof InvestigateResponseSchema>;
export type InterrogateResponse = z.infer<typeof InterrogateResponseSchema>;
export type PresentEvidenceResponse = z.infer<typeof PresentEvidenceResponseSchema>;
export type ChangeLocationResponse = z.infer<typeof ChangeLocationResponseSchema>;
export type UpdateSettingsResponse = z.infer<typeof UpdateSettingsResponseSchema>;
export type ResetResponse = z.infer<typeof ResetResponseSchema>;
export type SubmitVerdictResponse = z.infer<typeof SubmitVerdictResponseSchema>;
export type TelegramSnapshot = z.infer<typeof TelegramSnapshotSchema>;
