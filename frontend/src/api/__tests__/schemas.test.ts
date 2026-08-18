/**
 * Zod Schema Baseline Tests
 *
 * Captures the current runtime contract of the most-used schemas
 * so the upcoming refactor cannot silently widen/narrow them.
 *
 * Some assertions are marked REGRESSION — they capture
 * known bugs that the refactor is expected to fix.
 *
 * @module api/__tests__/schemas.test
 */

import { describe, it, expect } from 'vitest';
import {
  InvestigateResponseSchema,
  BriefingCompleteResponseSchema,
  SaveResponseSchema,
  LoadResponseSchema,
} from '../schemas';

describe('Zod schemas — runtime contracts', () => {
  describe('InvestigateResponseSchema', () => {
    it('parses a valid minimal payload', () => {
      const result = InvestigateResponseSchema.safeParse({
        narrator_response: 'You search the desk.',
        new_evidence: [],
        already_discovered: false,
      });

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.narrator_response).toBe('You search the desk.');
      }
    });

    it('parses a valid full payload with optional fields', () => {
      const result = InvestigateResponseSchema.safeParse({
        narrator_response: 'You find a note.',
        new_evidence: ['hidden_note'],
        evidence_names: { hidden_note: 'Hidden Note' },
        already_discovered: false,
        location_changed: 'library',
        updated_state: {
          case_id: 'case_001',
          current_location: 'library',
          discovered_evidence: ['hidden_note'],
          visited_locations: ['library'],
          save_revision: 1,
        },
      });

      expect(result.success).toBe(true);
    });

    it('rejects unknown top-level keys (.strict() enforced)', () => {
      const result = InvestigateResponseSchema.safeParse({
        narrator_response: 'text',
        new_evidence: [],
        already_discovered: false,
        unexpected_field: 'should not be allowed',
      });

      expect(result.success).toBe(false);
    });

    it('rejects payload missing required fields', () => {
      const result = InvestigateResponseSchema.safeParse({
        narrator_response: 'text',
        // missing new_evidence, already_discovered
      });

      expect(result.success).toBe(false);
    });
  });

  describe('BriefingCompleteResponseSchema', () => {
    it('parses {success: true} (minimal contract)', () => {
      const result = BriefingCompleteResponseSchema.safeParse({
        success: true,
      });

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.success).toBe(true);
      }
    });

    it('parses {success: false}', () => {
      const result = BriefingCompleteResponseSchema.safeParse({
        success: false,
      });

      expect(result.success).toBe(true);
    });

    // Bug #5 fix: schema now accepts the real backend payload
    // {success: true, updated_state: {...}}. Previously .strict() rejected the
    // unknown key, causing Start Investigation to crash.
    it('accepts {success: true, updated_state: {...}} from real backend', () => {
      const result = BriefingCompleteResponseSchema.safeParse({
        success: true,
        updated_state: { anything: 1 },
      });

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.updated_state).toEqual({ anything: 1 });
      }
    });

    it('rejects payload missing success field', () => {
      const result = BriefingCompleteResponseSchema.safeParse({});
      expect(result.success).toBe(false);
    });
  });

  describe('SaveResponseSchema', () => {
    it('parses valid save response', () => {
      const result = SaveResponseSchema.safeParse({
        success: true,
        message: 'Saved successfully',
      });

      expect(result.success).toBe(true);
    });

    it('accepts response without optional message', () => {
      const result = SaveResponseSchema.safeParse({ success: true });
      expect(result.success).toBe(true);
    });
  });

  describe('LoadResponseSchema', () => {
    it('parses a valid load response with conversation history', () => {
      const result = LoadResponseSchema.safeParse({
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: ['note'],
        visited_locations: ['library'],
        conversation_history: [
          { type: 'player', text: 'search desk', timestamp: 1000 },
          { type: 'narrator', text: 'found a note', timestamp: 1001 },
        ],
      });

      expect(result.success).toBe(true);
    });

    it('accepts null conversation_history (nullish)', () => {
      const result = LoadResponseSchema.safeParse({
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
        conversation_history: null,
      });

      expect(result.success).toBe(true);
    });

    it('rejects invalid message type in conversation_history', () => {
      const result = LoadResponseSchema.safeParse({
        case_id: 'case_001',
        current_location: 'library',
        discovered_evidence: [],
        visited_locations: ['library'],
        conversation_history: [
          { type: 'unknown_type', text: 'x', timestamp: 1 },
        ],
      });

      expect(result.success).toBe(false);
    });
  });
});
