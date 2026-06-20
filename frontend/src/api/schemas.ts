/**
 * Zod Runtime Validation Schemas for API Responses
 *
 * This module provides runtime validation for all API responses
 * to ensure type safety beyond compile-time TypeScript checks.
 *
 * All schemas use .strict() to catch unexpected properties.
 *
 * @module api/schemas
 * @since Phase 5.8 - Runtime Validation
 */

import { z } from 'zod';

// ============================================
// Helper for parsing Zod errors to ApiError format
// ============================================

/**
 * Formats a ZodError into a human-readable string
 */
export function formatZodError(error: z.ZodError): string {
  return error.issues
    .map((issue) => `${issue.path.join('.')}: ${issue.message}`)
    .join('; ');
}

// ============================================
// Base/Shared Schemas
// ============================================

/**
 * Schema for ConversationMessage (used in LoadResponse)
 */
const ConversationMessageSchema = z
  .object({
    type: z.enum(['player', 'narrator', 'matthew', 'tom']),
    text: z.string(),
    timestamp: z.number(),
  })
  .strict();


// ============================================
// Phase 1: Core Investigation Schemas
// ============================================

/**
 * Schema for InvestigateResponse
 * Runtime validation for POST /api/investigate
 */
export const InvestigateResponseSchema = z
  .object({
    narrator_response: z.string(),
    new_evidence: z.array(z.string()),
    evidence_names: z.record(z.string(), z.string()).optional(),
    already_discovered: z.boolean(),
    location_changed: z.string().optional(),
    updated_state: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();


/**
 * Schema for SaveResponse
 * Runtime validation for POST /api/save
 */
export const SaveResponseSchema = z
  .object({
    success: z.boolean(),
    message: z.string().optional(),
  })
  .strict();


/**
 * Schema for LoadResponse
 * Runtime validation for GET /api/load/{case_id}
 */
export const LoadResponseSchema = z
  .object({
    case_id: z.string(),
    current_location: z.string(),
    discovered_evidence: z.array(z.string()),
    visited_locations: z.array(z.string()),
    conversation_history: z.array(ConversationMessageSchema).nullish(),
    narrator_verbosity: z.enum(['concise', 'storyteller', 'atmospheric']).optional(),
    language: z.string().optional(),
  })
  .strict();


/**
 * Schema for EvidenceResponse
 * Runtime validation for GET /api/evidence
 */
export const EvidenceResponseSchema = z
  .object({
    case_id: z.string(),
    discovered_evidence: z.array(z.string()),
  })
  .strict();


/**
 * Schema for EvidenceDetails
 * Runtime validation for GET /api/evidence/{id}
 */
export const EvidenceDetailsSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    location_found: z.string(),
    description: z.string(),
    type: z.string().optional(),
  })
  .strict();


/**
 * Schema for LocationResponse
 * Runtime validation for GET /api/case/{case_id}/location/{location_id}
 */
export const LocationResponseSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    description: z.string(),
    surface_elements: z.array(z.string()),
    witnesses_present: z.array(z.string()).nullish(),
  })
  .strict();


// ============================================
// Phase 2: Witness Schemas
// ============================================

/**
 * Schema for WitnessConversationItem
 */
const WitnessConversationItemSchema = z
  .object({
    question: z.string(),
    response: z.string(),
    timestamp: z.string(),
    trust_delta: z.number().optional(),
  })
  .strict();


/**
 * Schema for WitnessInfo
 * Runtime validation for GET /api/witness/{id} and GET /api/witnesses
 */
export const WitnessInfoSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    personality: z.string().nullable().optional(),
    trust: z.number(),
    conversation_history: z.array(WitnessConversationItemSchema).nullish(),
    secrets_revealed: z.array(z.string()),
    image_url: z.string().nullable().optional(),
  })
  .strict();


/**
 * Schema for InterrogateResponse
 * Runtime validation for POST /api/interrogate
 */
export const InterrogateResponseSchema = z
  .object({
    response: z.string(),
    trust: z.number(),
    trust_delta: z.number(),
    secrets_revealed: z.array(z.string()),
    secret_texts: z.record(z.string(), z.string()),
    updated_state: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();


/**
 * Schema for PresentEvidenceResponse
 * Runtime validation for POST /api/present-evidence
 */
export const PresentEvidenceResponseSchema = z
  .object({
    response: z.string(),
    trust: z.number(),
    trust_delta: z.number(),
    secrets_revealed: z.array(z.string()),
    secret_texts: z.record(z.string(), z.string()),
    updated_state: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();


// ============================================
// Phase 3: Verdict Schemas
// ============================================

/**
 * Schema for Fallacy
 */
const FallacySchema = z
  .object({
    name: z.string(),
    description: z.string(),
    example: z.string().optional(), // Backend: example: str = "" (has default)
  })
  .strict();


/**
 * Schema for MentorFeedbackData
 */
const MentorFeedbackDataSchema = z
  .object({
    analysis: z.string(),
    fallacies_detected: z.array(FallacySchema),
    score: z.number(),
    quality: z.string(),
    critique: z.string(),
    praise: z.string(),
    hint: z.string().nullable(), // Backend: hint: str | None = None (nullable)
  })
  .strict();


/**
 * Schema for DialogueLine
 */
const DialogueLineSchema = z
  .object({
    speaker: z.string(),
    text: z.string(),
    tone: z.string().optional(),
  })
  .strict();


/**
 * Schema for ConfrontationDialogueData
 */
const ConfrontationDialogueDataSchema = z
  .object({
    dialogue: z.array(DialogueLineSchema),
    aftermath: z.string(),
  })
  .strict();


/**
 * Schema for SubmitVerdictResponse
 * Runtime validation for POST /api/submit-verdict
 */
export const SubmitVerdictResponseSchema = z
  .object({
    correct: z.boolean(),
    attempts_remaining: z.number(),
    case_solved: z.boolean(),
    mentor_feedback: MentorFeedbackDataSchema,
    confrontation: ConfrontationDialogueDataSchema.nullable(),
    reveal: z.string().nullable(),
    wrong_suspect_response: z.string().nullable(),
    updated_state: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();


// ============================================
// Phase 3.5: Briefing Schemas
// ============================================

/**
 * Schema for TeachingChoice
 */
const TeachingChoiceSchema = z
  .object({
    id: z.string(),
    text: z.string(),
    response: z.string(),
  })
  .strict();


/**
 * Schema for TeachingQuestion
 */
const TeachingQuestionSchema = z
  .object({
    prompt: z.string(),
    choices: z.array(TeachingChoiceSchema),
    concept_summary: z.string(),
  })
  .strict();


/**
 * Schema for CaseDossier
 */
const CaseDossierSchema = z
  .object({
    title: z.string(),
    victim: z.string(),
    location: z.string(),
    time: z.string(),
    status: z.string(),
    synopsis: z.string(),
  })
  .strict();


/**
 * Schema for BriefingContent
 * Runtime validation for GET /api/briefing/{case_id}
 */
export const BriefingContentSchema = z
  .object({
    case_id: z.string(),
    dossier: CaseDossierSchema,
    teaching_questions: z.array(TeachingQuestionSchema),
    transition: z.string().optional(),
    briefing_completed: z.boolean(),
    // Deprecated fields (optional for backward compatibility)
    case_assignment: z.string().optional(),
    teaching_question: TeachingQuestionSchema.optional(),
    rationality_concept: z.string().optional(),
    concept_description: z.string().optional(),
  })
  .strict();


/**
 * Schema for BriefingQuestionResponse
 * Runtime validation for POST /api/briefing/{case_id}/question
 */
export const BriefingQuestionResponseSchema = z
  .object({
    answer: z.string(),
    updated_state: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();


/**
 * Schema for BriefingCompleteResponse
 * Runtime validation for POST /api/briefing/{case_id}/complete
 *
 * Backend returns {success, updated_state} after persisting briefing_completed flag.
 */
export const BriefingCompleteResponseSchema = z
  .object({
    success: z.boolean(),
    updated_state: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();


// ============================================
// Phase 4: Matthew spirit companion schemas
// ============================================

/**
 * Schema for MatthewTriggerType
 */
const MatthewTriggerTypeSchema = z.enum([
  'helpful',
  'misleading',
  'self_aware',
  'dark_humor',
  'emotional',
]);

/**
 * Schema for MatthewTrigger
 * Runtime validation for POST /api/case/{case_id}/matthew/triggers/check
 */
export const MatthewTriggerSchema = z
  .object({
    id: z.string(),
    text: z.string(),
    type: MatthewTriggerTypeSchema,
    tier: z.union([z.literal(1), z.literal(2), z.literal(3)]),
  })
  .strict();


/**
 * Schema for MatthewResponse
 * Runtime validation for Matthew LLM endpoints (auto-comment and direct chat)
 */
export const MatthewResponseSchema = z
  .object({
    text: z.string(),
    mode: z.string(),
    trust_level: z.number(),
    updated_state: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();


// ============================================
// Phase 5.2: Location Management Schemas
// ============================================

/**
 * Schema for LocationInfo
 * Runtime validation for GET /api/case/{case_id}/locations
 */
export const LocationInfoSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    type: z.string(),
  })
  .strict();


/**
 * Schema for ChangeLocationResponse
 * Runtime validation for POST /api/case/{case_id}/change-location
 */
export const ChangeLocationResponseSchema = z
  .object({
    success: z.boolean(),
    location: z
      .object({
        id: z.string(),
        name: z.string(),
        description: z.string(),
        surface_elements: z.array(z.string()).optional(),
        witnesses_present: z.array(z.string()).optional(),
      })
      .strict(),
    message: z.string().optional(),
    updated_state: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();


// ============================================
// Phase 5.3: Save/Load System Schemas
// ============================================

/**
 * Schema for SaveSlotMetadata
 */
const SaveSlotMetadataSchema = z
  .object({
    slot: z.string(),
    case_id: z.string(),
    timestamp: z.string().nullable(),
    location: z.string(),
    evidence_count: z.number(),
    witnesses_interrogated: z.number().optional(),
    progress_percent: z.number().optional(),
    version: z.string(),
  })
  .strict();


/**
 * Schema for SaveSlotsListResponse
 * Runtime validation for GET /api/case/{case_id}/saves/list
 */
export const SaveSlotsListResponseSchema = z
  .object({
    case_id: z.string(),
    saves: z.array(SaveSlotMetadataSchema),
  })
  .strict();


/**
 * Schema for SaveSlotResponse
 * Runtime validation for POST /api/save (with slot)
 */
export const SaveSlotResponseSchema = z
  .object({
    success: z.boolean(),
    message: z.string(),
    slot: z.string().optional(),
  })
  .strict();


/**
 * Schema for DeleteSlotResponse
 * Runtime validation for DELETE /api/case/{case_id}/saves/{slot}
 */
export const DeleteSlotResponseSchema = z
  .object({
    success: z.boolean(),
    slot: z.string(),
    message: z.string().nullable(),
  })
  .strict();


// ============================================
// Phase 5.3.1: Landing Page Schemas
// ============================================

/**
 * Schema for ApiCaseMetadata
 */
const ApiCaseMetadataSchema = z
  .object({
    id: z.string(),
    title: z.string(),
    difficulty: z.enum(['beginner', 'intermediate', 'advanced']),
    description: z.string(),
  })
  .strict();


/**
 * Schema for CaseListResponse
 * Runtime validation for GET /api/cases
 */
export const CaseListResponseSchema = z
  .object({
    cases: z.array(ApiCaseMetadataSchema),
    count: z.number(),
    errors: z.array(z.string()).nullable().optional(),
  })
  .strict();


// ============================================
// Settings Schemas
// ============================================

/**
 * Schema for UpdateSettingsResponse
 * Runtime validation for POST /api/settings/update
 */
export const UpdateSettingsResponseSchema = z
  .object({
    success: z.boolean(),
    message: z.string(),
  })
  .strict();


// ============================================
// Phase 3: Reset Case Response Schema
// ============================================

/**
 * Schema for ResetResponse
 * Runtime validation for POST /api/case/{case_id}/reset
 */
export const ResetResponseSchema = z
  .object({
    success: z.boolean(),
    message: z.string(),
  })
  .strict();

