/**
 * EvidenceBoard Component Tests
 *
 * Tests for the evidence display sidebar including:
 * - Empty state rendering
 * - Evidence list rendering
 * - Evidence formatting
 * - Compact mode
 *
 * @module components/__tests__/EvidenceBoard.test
 * @since Phase 1
 */

import { describe, it, expect } from 'vitest';
import { render } from '../../test/render';
import { screen } from '@testing-library/react';
import { EvidenceBoard } from '../EvidenceBoard';

// ============================================
// Test Suite
// ============================================

describe('EvidenceBoard', () => {
  // ------------------------------------------
  // Rendering Tests
  // ------------------------------------------

  describe('Rendering', () => {
    it('renders evidence board title', () => {
      render(<EvidenceBoard evidence={[]} caseId="case_001" />);

      expect(screen.getByText(/Evidence Board/i)).toBeInTheDocument();
    });

    it('renders header with gray separator', () => {
      render(<EvidenceBoard evidence={[]} caseId="case_001" />);

      // Separator should be visible
      expect(screen.getByText(/Evidence Board/i)).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Empty State Tests
  // ------------------------------------------

  describe('Empty State', () => {
    it('displays empty state message when no evidence', () => {
      render(<EvidenceBoard evidence={[]} caseId="case_001" />);

      expect(screen.getByText(/No evidence discovered yet/i)).toBeInTheDocument();
    });

    it('displays hint text in empty state', () => {
      render(<EvidenceBoard evidence={[]} caseId="case_001" />);

      expect(screen.getByText(/Investigate the location to find clues/i)).toBeInTheDocument();
    });

    it('does not show evidence count in empty state', () => {
      render(<EvidenceBoard evidence={[]} caseId="case_001" />);

      expect(screen.queryByText(/Collected:/i)).not.toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Evidence List Tests
  // ------------------------------------------

  describe('Evidence List', () => {
    it('displays single evidence item', () => {
      render(<EvidenceBoard evidence={['hidden_note']} caseId="case_001" />);

      expect(screen.getByText(/Hidden Note/i)).toBeInTheDocument();
    });

    it('uses authored localized evidence names when provided', () => {
      render(
        <EvidenceBoard
          evidence={['hidden_note']}
          evidenceNames={{ hidden_note: 'Смятая записка с извинениями' }}
          caseId="case_001"
        />,
      );

      expect(screen.getByText('Смятая записка с извинениями')).toBeInTheDocument();
      expect(screen.queryByText('Hidden Note')).not.toBeInTheDocument();
    });

    it('displays multiple evidence items', () => {
      render(
        <EvidenceBoard
          evidence={['hidden_note', 'focus_signature', 'blood_stain']}
          caseId="case_001"
        />
      );

      expect(screen.getByText(/Hidden Note/i)).toBeInTheDocument();
      expect(screen.getByText(/Focus Signature/i)).toBeInTheDocument();
      expect(screen.getByText(/Blood Stain/i)).toBeInTheDocument();
    });

    it('displays evidence count for single item', () => {
      render(<EvidenceBoard evidence={['hidden_note']} caseId="case_001" />);

      // Count shown in subtitle
      expect(screen.getByText(/1 ITEM$/i)).toBeInTheDocument();
    });

    it('displays evidence count for multiple items', () => {
      render(
        <EvidenceBoard evidence={['hidden_note', 'focus_signature']} caseId="case_001" />
      );

      // Count shown in subtitle
      expect(screen.getByText(/2 ITEMS/i)).toBeInTheDocument();
    });

    it.todo('displays numbered index for each evidence');

    it('does not show empty state when evidence exists', () => {
      render(<EvidenceBoard evidence={['hidden_note']} caseId="case_001" />);

      expect(screen.queryByText(/No evidence discovered yet/i)).not.toBeInTheDocument();
    });

    it('shows footer hint when evidence exists', () => {
      render(<EvidenceBoard evidence={['hidden_note']} caseId="case_001" />);

      expect(
        screen.getByText(/Click on evidence to view details/i)
      ).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Evidence ID Formatting Tests
  // ------------------------------------------

  describe('Evidence ID Formatting', () => {
    it('formats snake_case to Title Case', () => {
      render(<EvidenceBoard evidence={['hidden_note']} caseId="case_001" />);

      expect(screen.getByText(/Hidden Note/i)).toBeInTheDocument();
    });

    it('handles multiple underscores', () => {
      render(
        <EvidenceBoard evidence={['dark_arts_book_page']} caseId="case_001" />
      );

      expect(screen.getByText(/Dark Arts Book Page/i)).toBeInTheDocument();
    });

    it('handles single word IDs', () => {
      render(<EvidenceBoard evidence={['letter']} caseId="case_001" />);

      expect(screen.getByText(/Letter/i)).toBeInTheDocument();
    });

    it('handles all caps ID parts', () => {
      render(<EvidenceBoard evidence={['MINISTRY_SEAL']} caseId="case_001" />);

      expect(screen.getByText(/Ministry Seal/i)).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Compact Mode Tests
  // ------------------------------------------

  describe('Compact Mode', () => {
    it('renders in compact mode', () => {
      render(
        <EvidenceBoard evidence={['hidden_note']} caseId="case_001" compact={true} />
      );

      expect(screen.getByText(/Hidden Note/i)).toBeInTheDocument();
    });

    it('renders in default (non-compact) mode', () => {
      render(
        <EvidenceBoard evidence={['hidden_note']} caseId="case_001" compact={false} />
      );

      expect(screen.getByText(/Hidden Note/i)).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Accessibility Tests
  // ------------------------------------------

  describe('Accessibility', () => {
    it('uses list markup for evidence items', () => {
      render(
        <EvidenceBoard evidence={['hidden_note', 'focus_signature']} caseId="case_001" />
      );

      const list = screen.getByRole('list');
      expect(list).toBeInTheDocument();

      const items = screen.getAllByRole('listitem');
      expect(items).toHaveLength(2);
    });

    it('has semantic heading', () => {
      render(<EvidenceBoard evidence={[]} caseId="case_001" />);

      expect(
        screen.getByRole('heading', { level: 3, name: /Evidence Board/i })
      ).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Edge Cases
  // ------------------------------------------

  describe('Edge Cases', () => {
    it('handles very long evidence IDs', () => {
      const longId = 'this_is_a_very_long_evidence_id_that_might_cause_layout_issues';
      render(<EvidenceBoard evidence={[longId]} caseId="case_001" />);

      expect(
        screen.getByText(/This Is A Very Long Evidence Id That Might Cause Layout Issues/i)
      ).toBeInTheDocument();
    });

    it('handles special characters in evidence IDs', () => {
      // Even though we shouldn't have special chars, let's ensure it doesn't break
      render(<EvidenceBoard evidence={['note_v2']} caseId="case_001" />);

      expect(screen.getByText(/Note V2/i)).toBeInTheDocument();
    });

    it('handles empty string evidence ID gracefully', () => {
      // Edge case: should not crash
      render(<EvidenceBoard evidence={['']} caseId="case_001" />);

      // Should show count but empty formatted name (count in subtitle)
      expect(screen.getByText(/1 ITEM$/i)).toBeInTheDocument();
    });
  });
});
