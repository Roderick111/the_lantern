/**
 * SaveLoadModal Component Tests
 *
 * Captures current save/load UI behavior before the refactor wave
 * introduces a delete-slot button + reworks slot rendering.
 *
 * @module components/__tests__/SaveLoadModal.test
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '../../test/render';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SaveLoadModal } from '../SaveLoadModal';
import type { SaveSlotMetadata } from '../../types/investigation';

// ============================================
// Test Data
// ============================================

const slotOneMeta: SaveSlotMetadata = {
  slot: 'slot_1',
  case_id: 'case_001',
  timestamp: '2026-05-26T12:00:00Z',
  location: 'Blackwood Collegiate Library',
  evidence_count: 3,
  version: '1.0',
};

const autosaveMeta: SaveSlotMetadata = {
  slot: 'autosave',
  case_id: 'case_001',
  timestamp: '2026-05-26T12:30:00Z',
  location: 'Blackwood Collegiate Library',
  evidence_count: 5,
  version: '1.0',
};

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  mode: 'load' as const,
  onSave: vi.fn().mockResolvedValue(undefined),
  onLoad: vi.fn().mockResolvedValue(undefined),
  slots: [slotOneMeta, autosaveMeta],
  loading: false,
  caseId: 'case_001',
  playerId: 'test-player',
};

// ============================================
// Test Suite
// ============================================

describe('SaveLoadModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Rendering', () => {
    it('renders 3 manual slots and the autosave slot in load mode', () => {
      render(<SaveLoadModal {...defaultProps} />);

      // 3 manual slot buttons (slot_1 populated, slot_2/3 empty)
      expect(
        screen.getByRole('button', { name: /\[1\] LOAD/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /\[2\] EMPTY/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /\[3\] EMPTY/i }),
      ).toBeInTheDocument();
      // Autosave slot appears in load mode
      expect(
        screen.getByRole('button', { name: /\[4\] LOAD/i }),
      ).toBeInTheDocument();
    });

    it('does NOT render autosave slot in save mode', () => {
      render(<SaveLoadModal {...defaultProps} mode="save" />);

      // Autosave row should not be a load target in save mode
      expect(
        screen.queryByRole('button', { name: /\[4\] LOAD/i }),
      ).not.toBeInTheDocument();
    });

    // Refactor: delete button is now rendered on populated manual slots
    // (and only on populated, non-autosave slots).
    it('renders a delete button for each populated manual slot', () => {
      render(<SaveLoadModal {...defaultProps} />);

      // slot_1 is populated → one delete button exposed via aria-label.
      const deleteButtons = screen.getAllByRole('button', {
        name: /delete save in slot/i,
      });
      expect(deleteButtons).toHaveLength(1);
      expect(
        screen.getByRole('button', { name: /delete save in slot 1/i }),
      ).toBeInTheDocument();
    });

    it('does NOT render a delete button on empty slots', () => {
      render(<SaveLoadModal {...defaultProps} />);

      expect(
        screen.queryByRole('button', { name: /delete save in slot 2/i }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /delete save in slot 3/i }),
      ).not.toBeInTheDocument();
    });

    it('does NOT render a delete button on the autosave slot', () => {
      render(<SaveLoadModal {...defaultProps} />);

      // Only the manual populated slot exposes delete; autosave does not.
      expect(
        screen.getAllByRole('button', { name: /delete save in slot/i }),
      ).toHaveLength(1);
    });
  });

  describe('Load action', () => {
    it('calls onLoad with the slot id when a populated slot\'s LOAD button is clicked', async () => {
      const user = userEvent.setup();
      const onLoad = vi.fn().mockResolvedValue(undefined);

      render(<SaveLoadModal {...defaultProps} onLoad={onLoad} />);

      await user.click(screen.getByRole('button', { name: /\[1\] LOAD/i }));

      expect(onLoad).toHaveBeenCalledWith('slot_1');
    });

    it('calls onLoad with "autosave" when autosave\'s LOAD button is clicked', async () => {
      const user = userEvent.setup();
      const onLoad = vi.fn().mockResolvedValue(undefined);

      render(<SaveLoadModal {...defaultProps} onLoad={onLoad} />);

      await user.click(screen.getByRole('button', { name: /\[4\] LOAD/i }));

      expect(onLoad).toHaveBeenCalledWith('autosave');
    });
  });

  describe('Save action', () => {
    it('calls onSave with the slot id when SAVE HERE is clicked', async () => {
      const user = userEvent.setup();
      const onSave = vi.fn().mockResolvedValue(undefined);

      render(
        <SaveLoadModal
          {...defaultProps}
          mode="save"
          slots={[]}
          onSave={onSave}
        />,
      );

      await user.click(
        screen.getByRole('button', { name: /\[2\] SAVE HERE/i }),
      );

      expect(onSave).toHaveBeenCalledWith('slot_2');
    });

    it('calls onSave with the slot id when overwriting an existing slot', async () => {
      const user = userEvent.setup();
      const onSave = vi.fn().mockResolvedValue(undefined);

      render(
        <SaveLoadModal
          {...defaultProps}
          mode="save"
          slots={[slotOneMeta]}
          onSave={onSave}
        />,
      );

      await user.click(
        screen.getByRole('button', { name: /\[1\] OVERWRITE/i }),
      );

      expect(onSave).toHaveBeenCalledWith('slot_1');
    });
  });
});
