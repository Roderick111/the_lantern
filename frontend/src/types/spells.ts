/**
 * Types for the Rite System (Phase 4.5)
 *
 * Spell definitions matching backend/src/spells/definitions.py
 *
 * @module types/spells
 * @since Phase 4.5
 */

// ============================================
// Spell Types
// ============================================

/**
 * Spell safety levels
 * - safe: Can be used freely without consequences
 * - restricted: Requires authorization, illegal use has consequences
 */
export type SafetyLevel = "safe" | "restricted";

/**
 * Spell categories for organization
 */
export type SpellCategory = "detection" | "analysis" | "restoration" | "mental";

/**
 * Spell definition matching backend SPELL_DEFINITIONS structure
 */
export interface SpellDefinition {
  /** Spell ID (lowercase, e.g., "unveil") */
  id: string;
  /** Display name (e.g., "Unveil") */
  name: string;
  /** Spell description/effect */
  description: string;
  /** Safety level (safe or restricted) */
  safetyLevel: SafetyLevel;
  /** Spell category */
  category: SpellCategory;
}
