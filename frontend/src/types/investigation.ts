/**
 * Types for the Phase 1 Investigation API
 *
 * These types match the backend Pydantic models for type-safe
 * communication between frontend and backend.
 *
 * @module types/investigation
 * @since Phase 1
 */

// ============================================
// API Request Types
// ============================================

/** Valid save slot names (matches backend SaveSlotName Literal). */
export type SaveSlotName = 'autosave' | 'slot_1' | 'slot_2' | 'slot_3';

/**
 * Request payload for the /api/investigate endpoint
 */
export interface InvestigateRequest {
  /** Freeform player action (e.g., "I check under the desk") */
  player_input: string;
  /** Current case ID (defaults to "case_001") */
  case_id?: string;
  /** Current location ID (defaults to "library") */
  location_id?: string;
  /** Save slot for state persistence (defaults to "autosave") */
  slot?: SaveSlotName;
}

/**
 * Request payload for the /api/save endpoint
 */
export interface SaveStateRequest {
  /** Player identifier */
  player_id: string;
  /** Current player state to persist */
  state: InvestigationState;
}

// ============================================
// API Response Types
// ============================================

/**
 * Response from the /api/investigate endpoint
 */
export interface InvestigateResponse {
  /** LLM narrator response (2-4 sentences) */
  narrator_response: string;
  /** Array of newly discovered evidence IDs */
  new_evidence: string[];
  /** Whether the player attempted to examine already-discovered evidence */
  already_discovered: boolean;
}

/**
 * Response from the /api/save endpoint
 */
export interface SaveResponse {
  /** Whether the save was successful */
  success: boolean;
  /** Optional message (error details or confirmation) */
  message?: string;
}

/**
 * Conversation message from backend (for persistence)
 */
export interface ConversationMessage {
  /** Message type */
  type: 'player' | 'narrator' | 'matthew' | 'tom';
  /** Message text content */
  text: string;
  /** Unix timestamp in milliseconds */
  timestamp: number;
}

/**
 * Response from the /api/load/{case_id} endpoint
 */
export interface LoadResponse {
  /** Case ID */
  case_id: string;
  /** Current location ID */
  current_location: string;
  /** Array of discovered evidence IDs */
  discovered_evidence: string[];
  /** Array of visited location IDs */
  visited_locations: string[];
  /** Conversation history (Phase 4.4 - persistence) */
  conversation_history?: ConversationMessage[] | null;
  /** Narrator verbosity style (Phase 5.7) */
  narrator_verbosity?: 'concise' | 'storyteller' | 'atmospheric';
  /** Game response language */
  language?: string;
}

/**
 * Response from the /api/evidence endpoint
 */
export interface EvidenceResponse {
  /** Case ID */
  case_id: string;
  /** Array of discovered evidence IDs */
  discovered_evidence: string[];
}

/**
 * Full evidence details from /api/evidence/{id}
 */
export interface EvidenceDetails {
  /** Evidence ID */
  readonly id: string;
  /** Display name */
  readonly name: string;
  /** Location where evidence was found */
  readonly location_found: string;
  /** Full description of the evidence */
  readonly description: string;
}

/**
 * Response from the /api/case/{case_id}/location/{location_id} endpoint
 */
export interface LocationResponse {
  /** Location ID */
  readonly id: string;
  /** Display name for the location */
  readonly name: string;
  /** Full description of the location */
  readonly description: string;
  /** Array of always-visible elements in the location */
  readonly surface_elements: readonly string[];
}

// ============================================
// State Types
// ============================================

/**
 * Player investigation state (for persistence)
 */
export interface InvestigationState {
  /** Current case ID */
  readonly case_id: string;
  /** Current location ID */
  readonly current_location: string;
  /** Array of discovered evidence IDs */
  readonly discovered_evidence: readonly string[];
  /** Array of visited location IDs */
  readonly visited_locations: readonly string[];
  /** Narrator verbosity style */
  readonly narrator_verbosity?: 'concise' | 'storyteller' | 'atmospheric';
  /** Game response language */
  readonly language?: string;
}

/**
 * Conversation history item for displaying in LocationView
 */
export interface ConversationItem {
  /** Unique ID for React key */
  id: string;
  /** Player's action text */
  action: string;
  /** LLM narrator response */
  response: string;
  /** Evidence discovered during this interaction (if any) */
  evidence_discovered: string[];
  /** Evidence ID → display name map */
  evidence_names?: Record<string, string>;
  /** Timestamp of the interaction */
  timestamp: Date;
}

// ============================================
// Error Types
// ============================================

/**
 * API error response structure
 */
export interface ApiError {
  /** HTTP status code */
  status: number;
  /** Error message */
  message: string;
  /** Optional error details */
  details?: string;
}

/**
 * Type guard to check if an error is an ApiError
 */
export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    'message' in error
  );
}

// ============================================
// Phase 2: Witness Types
// ============================================

/**
 * Single conversation exchange with a witness
 */
export interface WitnessConversationItem {
  /** Player's question */
  question: string;
  /** Witness response */
  response: string;
  /** ISO timestamp of the exchange */
  timestamp: string;
  /** Trust change from this exchange */
  trust_delta?: number;
}

/**
 * Witness information from GET /api/witness/{id}
 */
export interface WitnessInfo {
  /** Witness identifier */
  readonly id: string;
  /** Display name */
  readonly name: string;
  /** Personality type (empathetic, nervous, etc.) */
  readonly personality?: string | null;
  /** Current trust level (0-100) */
  readonly trust: number;
  /** Conversation history with this witness */
  readonly conversation_history?: readonly WitnessConversationItem[] | null;
  /** Secrets revealed by this witness */
  readonly secrets_revealed: readonly string[];
  /** Optional URL/path to witness portrait image */
  readonly image_url?: string | null;
}

/**
 * Request payload for POST /api/interrogate
 */
export interface InterrogateRequest {
  /** Witness identifier */
  witness_id: string;
  /** Player's question */
  question: string;
  /** Case identifier */
  case_id?: string;
  /** Save slot (defaults to "autosave") */
  slot?: SaveSlotName;
}

/**
 * Response from POST /api/interrogate
 */
export interface InterrogateResponse {
  /** Witness response text */
  response: string;
  /** Current trust level (0-100) */
  trust: number;
  /** Trust change from this interaction */
  trust_delta?: number;
  /** Secrets revealed in this response */
  secrets_revealed?: string[];
  /** Maps secret_id to full text description (Phase 4.6) */
  secret_texts?: Record<string, string>;
}

/**
 * Request payload for POST /api/present-evidence
 */
export interface PresentEvidenceRequest {
  /** Witness identifier */
  witness_id: string;
  /** Evidence ID to present */
  evidence_id: string;
  /** Case identifier */
  case_id?: string;
  /** Save slot (defaults to "autosave") */
  slot?: SaveSlotName;
}

/**
 * Response from POST /api/present-evidence
 */
export interface PresentEvidenceResponse {
  /** Witness response text */
  response: string;
  /** Current trust level (0-100) */
  trust: number;
  /** Trust change from this interaction */
  trust_delta?: number;
  /** Secrets revealed in this response */
  secrets_revealed?: string[];
}

// ============================================
// Phase 3: Verdict Types
// ============================================

/**
 * Logical fallacy detected in reasoning
 */
export interface Fallacy {
  /** Fallacy name (e.g., "Confirmation Bias") */
  name: string;
  /** Description of the fallacy */
  description: string;
  /** Example from player's reasoning (if applicable) */
  example?: string;
}

/**
 * Mentor feedback data structure
 */
export interface MentorFeedbackData {
  /** Analysis summary of player's reasoning */
  analysis: string;
  /** List of detected fallacies */
  fallacies_detected: Fallacy[];
  /** Reasoning score (0-100) */
  score: number;
  /** Quality label (excellent, good, fair, poor, failing) */
  quality: string;
  /** Critique of reasoning weaknesses */
  critique: string;
  /** Praise for reasoning strengths */
  praise: string;
  /** Adaptive hint (more specific as attempts decrease) */
  hint: string | null;
}

/**
 * Single line of dialogue in confrontation
 */
export interface DialogueLine {
  /** Speaker identifier (graves, player, suspect name) */
  speaker: string;
  /** Dialogue text */
  text: string;
  /** Emotional tone (defiant, remorseful, broken, angry, resigned) */
  tone?: string;
}

/**
 * Post-verdict confrontation dialogue data
 */
export interface ConfrontationDialogueData {
  /** Array of dialogue exchanges */
  dialogue: DialogueLine[];
  /** Aftermath text describing consequences */
  aftermath: string;
}

/**
 * Request payload for POST /api/submit-verdict
 */
export interface SubmitVerdictRequest {
  /** Case identifier */
  case_id?: string;
  /** Player identifier */
  player_id?: string;
  /** Save slot (defaults to "autosave") */
  slot?: string;
  /** Suspect ID being accused */
  accused_suspect_id: string;
  /** Player's reasoning for accusation */
  reasoning: string;
  /** Evidence IDs the player cites as support */
  evidence_cited: string[];
}

/**
 * Response from POST /api/submit-verdict
 */
export interface SubmitVerdictResponse {
  /** Whether the verdict was correct */
  correct: boolean;
  /** Number of attempts remaining */
  attempts_remaining: number;
  /** Whether the case is now solved */
  case_solved: boolean;
  /** Mentor feedback on the verdict */
  mentor_feedback: MentorFeedbackData;
  /** Confrontation dialogue (only if correct or max attempts reached) */
  confrontation: ConfrontationDialogueData | null;
  /** Reveal message showing correct answer (only if max attempts reached) */
  reveal: string | null;
  /** Pre-written response for accusing wrong suspect */
  wrong_suspect_response: string | null;
}

// ============================================
// Phase 3.5: Briefing Types
// ============================================

/**
 * Single choice option for teaching question
 */
export interface TeachingChoice {
  /** Unique identifier for the choice */
  id: string;
  /** Display text for the choice */
  text: string;
  /** Graves's response when this choice is selected */
  response: string;
}

/**
 * Teaching question with multiple choice answers
 */
export interface TeachingQuestion {
  /** Question prompt text */
  prompt: string;
  /** Array of answer choices */
  choices: TeachingChoice[];
  /** Summary of the concept after answering */
  concept_summary: string;
}

/**
 * Case dossier displayed in briefing (Phase 5.x redesign)
 */
export interface CaseDossier {
  /** Case title */
  title: string;
  /** Victim name and details */
  victim: string;
  /** Crime scene location */
  location: string;
  /** Time of incident */
  time: string;
  /** Current case status */
  status: string;
  /** Case synopsis */
  synopsis: string;
}

/**
 * Briefing content loaded from case YAML
 */
export interface BriefingContent {
  /** Case identifier */
  case_id: string;
  /** Case dossier (Phase 5.x redesign) */
  dossier: CaseDossier;
  /** Array of teaching questions (Phase 5.x - multiple questions) */
  teaching_questions: TeachingQuestion[];
  /** Transition text to display after Q&A (Phase 3.8) */
  transition?: string;
  /** Whether the briefing has been completed (backend-persisted) */
  briefing_completed: boolean;
  /** @deprecated Use dossier instead */
  case_assignment?: string;
  /** @deprecated Use teaching_questions instead */
  teaching_question?: TeachingQuestion;
  /** @deprecated Use teaching_questions instead */
  rationality_concept?: string;
  /** @deprecated Use teaching_questions instead */
  concept_description?: string;
}

/**
 * Single Q&A exchange in briefing conversation
 */
export interface BriefingConversation {
  /** Player's question */
  question: string;
  /** Graves's answer */
  answer: string;
}

/**
 * Response from POST /api/briefing/{case_id}/question
 */
export interface BriefingQuestionResponse {
  /** Graves's answer to the question */
  answer: string;
}

/**
 * Response from POST /api/briefing/{case_id}/complete
 */
export interface BriefingCompleteResponse {
  /** Whether the operation was successful */
  success: boolean;
}

// ============================================
// Phase 4: Matthew spirit companion types
// ============================================

/**
 * Matthew trigger types for categorizing companion messages
 */
export type MatthewTriggerType =
  | 'helpful'
  | 'misleading'
  | 'self_aware'
  | 'dark_humor'
  | 'emotional';

/**
 * Matthew spirit companion trigger from backend
 */
export interface MatthewTrigger {
  /** Unique trigger identifier */
  id: string;
  /** Matthew's message text */
  text: string;
  /** Whether message is helpful or misleading */
  type: MatthewTriggerType;
  /** Evidence tier (1=early, 2=mid, 3=late) */
  tier: 1 | 2 | 3;
}

/**
 * Message types for conversation display
 * Extends existing ConversationItem with inline message support
 * Added timestamp for unified message ordering (Phase 4.1)
 */
export type Message =
  | { type: 'player'; text: string; timestamp?: number }
  | { type: 'narrator'; text: string; timestamp?: number }
  | { type: 'matthew_ghost'; text: string; tone?: 'helpful' | 'misleading'; mode?: string; trust_level?: number; timestamp?: number };

// ============================================
// Phase 4.1: Matthew LLM chat types
// ============================================

/**
 * Response from Matthew LLM endpoints (auto-comment and direct chat)
 */
export interface MatthewResponse {
  /** Matthew's message text */
  text: string;
  /** Response mode: 'auto_helpful', 'auto_misleading', 'direct_chat_helpful', etc */
  mode: string;
  /** Current trust level (0-100) */
  trust_level: number;
}

// ============================================
// Phase 5.2: Location Management Types
// ============================================

/**
 * Location information from GET /api/case/{case_id}/locations
 */
export interface LocationInfo {
  /** Location identifier */
  id: string;
  /** Display name */
  name: string;
  /** Location type (micro, building, area) */
  type: string;
}

/**
 * Response from POST /api/case/{case_id}/change-location
 */
export interface ChangeLocationResponse {
  /** Whether the location change was successful */
  success: boolean;
  /** New location data */
  location: {
    /** Location ID */
    id: string;
    /** Location name */
    name: string;
    /** Location description */
    description: string;
    /** Surface elements */
    surface_elements?: string[];
    /** Witnesses present */
    witnesses_present?: string[];
  };
  /** Status message */
  message?: string;
  /** Updated player state (for B3 roundtrip reduction) */
  updated_state?: Record<string, unknown>;
}

// ============================================
// Phase 5.3: Save/Load System Types
// ============================================

/**
 * Metadata for a single save slot
 * (Returned from /api/case/{case_id}/saves/list)
 */
export interface SaveSlotMetadata {
  /** Slot identifier (slot_1, slot_2, slot_3, autosave, default) */
  slot: string;
  /** Case identifier (e.g., case_001) */
  case_id: string;
  /** ISO timestamp of when save was created */
  timestamp: string | null;
  /** Current location ID */
  location: string;
  /** Number of evidence items collected */
  evidence_count: number;
  /** Number of witnesses interrogated */
  witnesses_interrogated?: number;
  /** Progress percentage (0-100) */
  progress_percent?: number;
  /** Save file version for migration */
  version: string;
}

/**
 * Enhanced save response with slot information
 */
export interface SaveSlotResponse {
  /** Whether the save was successful */
  success: boolean;
  /** Status message */
  message: string;
  /** Slot that was saved to */
  slot?: string;
}

/**
 * Response from DELETE /api/case/{case_id}/saves/{slot}
 */
export interface DeleteSlotResponse {
  /** Whether deletion was successful */
  success: boolean;
  /** Slot that was deleted */
  slot: string;
  /** Status message */
  message: string | null;
}

// ============================================
// Phase 5.3.1: Landing Page Types
// ============================================

/**
 * Case metadata from backend API (GET /api/cases)
 * Raw format from backend CaseMetadata model
 */
export interface ApiCaseMetadata {
  /** Case identifier (e.g., "case_001") */
  id: string;
  /** Display title (e.g., "The Sealed Stacks") */
  title: string;
  /** Difficulty level from backend */
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  /** Brief case description */
  description: string;
}

/**
 * Metadata for a case in the case list
 * Used by LandingPage to display available cases
 * Frontend-transformed format from ApiCaseMetadata
 */
export interface CaseMetadata {
  /** Case identifier (e.g., "case_001") */
  id: string;
  /** Display name (e.g., "The Sealed Stacks") */
  name: string;
  /** Difficulty level (display format) */
  difficulty: 'Easy' | 'Medium' | 'Hard';
  /** Lock status (future: unlock progression) */
  status: 'locked' | 'unlocked';
  /** Brief case description */
  description: string;
}

/**
 * Response from GET /api/cases endpoint
 * Backend returns cases with metadata, count, and optional errors
 */
export interface CaseListResponse {
  /** Array of available cases (raw backend format) */
  cases: ApiCaseMetadata[];
  /** Total count of valid cases */
  count: number;
  /** Array of error messages for cases that failed to load (null or undefined if none) */
  errors?: string[] | null;
}
