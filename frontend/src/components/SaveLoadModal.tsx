/**
 * SaveLoadModal Component
 *
 * Modal for selecting save slots (save or load mode).
 * Shows 3 manual slots + 1 autosave slot (load mode only).
 * Displays metadata: timestamp, location, evidence count.
 *
 * @module components/SaveLoadModal
 * @since Phase 5.3
 */

import * as Dialog from '@radix-ui/react-dialog';
import { useEffect, useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { backdropVariants, dialogContentVariants, reducedMotionVariants } from '../utils/modalAnimations';
import { useTheme } from '../context/useTheme';
import { loadGameState, saveGameState, deleteSaveSlot } from '../api/client';
import { ConfirmDialog } from './ConfirmDialog';
import type { SaveSlotMetadata } from '../types/investigation';

// ============================================
// Types
// ============================================

export interface SaveLoadModalProps {
  /** Whether modal is open */
  isOpen: boolean;
  /** Callback to close modal */
  onClose: () => void;
  /** Mode: save or load */
  mode: 'save' | 'load';
  /** Callback when save button clicked */
  onSave: (slot: string) => Promise<void>;
  /** Callback when load button clicked */
  onLoad: (slot: string) => Promise<void>;
  /** Array of save slot metadata */
  slots: SaveSlotMetadata[];
  /** Loading state */
  loading: boolean;
  /** Case ID for export/import operations */
  caseId: string;
  /** Player ID for server API calls */
  playerId: string;
  /** Callback after import succeeds (to refresh slots) */
  onImportSuccess?: () => void;
}

// ============================================
// Component
// ============================================

export function SaveLoadModal({
  isOpen,
  onClose,
  mode,
  onSave,
  onLoad,
  slots,
  loading,
  caseId,
  playerId,
  onImportSuccess,
}: SaveLoadModalProps) {
  const { theme } = useTheme();
  const prefersReducedMotion = useReducedMotion();
  const importInputRef = useRef<HTMLInputElement>(null);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [pendingDeleteSlot, setPendingDeleteSlot] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const manualSlots = useMemo(() => ['slot_1', 'slot_2', 'slot_3'], []);
  const autosaveSlot = useMemo(() => slots.find((s) => s.slot === 'autosave'), [slots]);

  // All available slots (manual + autosave if exists)
  const allSlots = useMemo(() =>
    mode === 'load' && autosaveSlot
      ? [...manualSlots, 'autosave']
      : manualSlots,
    [mode, autosaveSlot, manualSlots]
  );

  // Selected slot index for keyboard navigation
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Keyboard shortcuts (1-4, arrows, Enter)
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      // Number keys 1-4: Select slot directly
      if (e.key >= '1' && e.key <= '4') {
        e.preventDefault();
        e.stopPropagation();
        const index = parseInt(e.key) - 1;
        if (index < allSlots.length) {
          setSelectedIndex(index);
        }
      }
      // Arrow Up / W: Previous non-empty slot
      else if (e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') {
        e.preventDefault();
        e.stopPropagation();

        let nextIndex = selectedIndex;
        let attempts = 0;

        // Find previous non-empty slot
        do {
          nextIndex = nextIndex > 0 ? nextIndex - 1 : allSlots.length - 1;
          attempts++;

          const slotId = allSlots[nextIndex];
          const slotData = slots.find((s) => s.slot === slotId);

          // Accept if slot has data or is autosave
          if (slotData || slotId === 'autosave') {
            setSelectedIndex(nextIndex);
            break;
          }
        } while (attempts < allSlots.length);
      }
      // Arrow Down / S: Next non-empty slot
      else if (e.key === 'ArrowDown' || e.key === 's' || e.key === 'S') {
        e.preventDefault();
        e.stopPropagation();

        let nextIndex = selectedIndex;
        let attempts = 0;

        // Find next non-empty slot
        do {
          nextIndex = nextIndex < allSlots.length - 1 ? nextIndex + 1 : 0;
          attempts++;

          const slotId = allSlots[nextIndex];
          const slotData = slots.find((s) => s.slot === slotId);

          // Accept if slot has data or is autosave
          if (slotData || slotId === 'autosave') {
            setSelectedIndex(nextIndex);
            break;
          }
        } while (attempts < allSlots.length);
      }
      // Enter: Confirm action on selected slot
      else if (e.key === 'Enter') {
        e.preventDefault();
        e.stopPropagation();
        const slotId = allSlots[selectedIndex];
        const slotData = slots.find((s) => s.slot === slotId);

        // Don't allow loading empty slots
        if (mode === 'load' && !slotData && slotId !== 'autosave') {
          return;
        }

        if (mode === 'save') {
          void onSave(slotId).then(() => onClose());
        } else {
          void onLoad(slotId).then(() => onClose());
        }
      }
    };

    // Capture phase to block events before they reach landing page
    document.addEventListener('keydown', handleKeyDown, true);
    return () => document.removeEventListener('keydown', handleKeyDown, true);
  }, [isOpen, allSlots, selectedIndex, mode, onSave, onLoad, onClose, slots]);

  /**
   * Get metadata for a specific slot
   */
  const getSlotData = (slotId: string) => slots.find((s) => s.slot === slotId);

  /**
   * Get case name from case_id
   * TODO: Replace with API call when /api/cases endpoint is implemented
   */
  const getCaseName = (caseId: string): string => {
    const caseNames: Record<string, string> = {
      case_001: 'The Sealed Stacks',
      case_002: 'The Poisoned Potion',
      case_003: 'The Missing Focus',
      case_004: 'The Forbidden Forest',
      case_005: 'The Dark Artifact',
      case_006: 'The Memory Charm',
    };
    return caseNames[caseId] || caseId;
  };

  /**
   * Format slot timestamp for display
   */
  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return 'Unknown';
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch {
      return 'Unknown';
    }
  };

  /**
   * Handle save button click
   */
  const handleSaveClick = (slotId: string) => {
    void onSave(slotId).then(() => onClose());
  };

  /**
   * Handle load button click
   */
  const handleLoadClick = (slotId: string) => {
    void onLoad(slotId).then(() => onClose());
  };

  /**
   * Handle export button click - download save from server as JSON
   */
  const handleExport = async (slotId: string) => {
    try {
      const state = await loadGameState(caseId, slotId);
      const data = JSON.stringify(state, null, 2);
      const blob = new Blob([data], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `lantern_save_${caseId}_${slotId}_${Date.now()}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Failed to export save:', e);
    }
  };

  /**
   * Confirm and execute slot deletion (manual slots only — autosave is protected).
   * Surfaces success/failure via the same status banner used by import.
   */
  const handleConfirmDelete = async () => {
    if (!pendingDeleteSlot) return;
    const slotId = pendingDeleteSlot;
    setDeleting(true);
    setImportStatus(null);
    try {
      await deleteSaveSlot(caseId, slotId);
      setImportStatus(`Deleted ${slotId.replace('_', ' ')}`);
      onImportSuccess?.();
    } catch {
      setImportStatus(`Failed to delete ${slotId.replace('_', ' ')}`);
    } finally {
      setDeleting(false);
      setPendingDeleteSlot(null);
    }
  };

  /**
   * Handle import file selection - upload JSON to server
   */
  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImportStatus(null);
    // Import to first empty slot, or slot_1 as fallback
    const emptySlot = manualSlots.find((s) => !slots.find((meta) => meta.slot === s)) ?? 'slot_1';

    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as Record<string, unknown>;

      // Basic validation
      if (
        typeof parsed.case_id !== 'string' ||
        typeof parsed.current_location !== 'string' ||
        !Array.isArray(parsed.discovered_evidence) ||
        !Array.isArray(parsed.visited_locations)
      ) {
        setImportStatus('Import failed: invalid save file');
        return;
      }

      const state = parsed as unknown as import('../types/investigation').InvestigationState;
      await saveGameState(caseId, state, emptySlot, playerId);
      setImportStatus(`Imported to ${emptySlot.replace('_', ' ')}`);
      onImportSuccess?.();
    } catch {
      setImportStatus('Import failed: invalid save file');
    }

    // Reset input so same file can be re-selected
    if (importInputRef.current) {
      importInputRef.current.value = '';
    }
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <AnimatePresence>
        {isOpen && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div className={theme.components.modal.overlay}
                variants={prefersReducedMotion ? reducedMotionVariants : backdropVariants}
                initial="initial" animate="animate" exit="exit" />
            </Dialog.Overlay>

            <Dialog.Content asChild forceMount onEscapeKeyDown={onClose}>
              <motion.div
                className={`fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50
                           ${theme.colors.bg.primary} border ${theme.colors.border.default} border-t-amber-900/50
                           w-[calc(100%-2rem)] max-w-lg shadow-xl max-h-[calc(100dvh-2rem)] overflow-y-auto
                           focus:outline-none`}
                variants={prefersReducedMotion ? reducedMotionVariants : dialogContentVariants}
                initial="initial" animate="animate" exit="exit"
              >
          {/* Title */}
          <div className={`border-b ${theme.colors.border.default} px-6 py-4`}>
            <Dialog.Title className={`text-sm font-bold ${theme.colors.text.primary} ${theme.fonts.ui} uppercase tracking-wider`}>
              {theme.symbols.block} {mode === 'save' ? 'SAVE GAME' : 'LOAD GAME'}
            </Dialog.Title>
            <Dialog.Description className={`text-xs ${theme.colors.text.muted} mt-1`}>
              {mode === 'save'
                ? 'Manual slots store your latest autosave snapshot (not unsaved in-session changes until autosave runs).'
                : 'Load a saved game from a slot'}
            </Dialog.Description>
          </div>

          {/* Slots */}
          <div className="p-6 space-y-3">
            {/* Manual save slots */}
            {manualSlots.map((slotId, index) => {
              const slotData = getSlotData(slotId);
              const isEmpty = !slotData;
              const isSelected = selectedIndex === index;

              return (
                <div
                  key={slotId}
                  className={`border p-4 ${
                    isEmpty
                      ? mode === 'save'
                        ? `${theme.colors.border.default} ${theme.colors.bg.semiTransparent}`
                        : `border-gray-800 ${theme.colors.bg.semiTransparent} opacity-50`
                      : isSelected
                      ? `border-amber-500/50 ${theme.colors.bg.hover}`
                      : `${theme.colors.border.default} ${theme.colors.bg.semiTransparent}`
                  }`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex-1">
                      <div className={`font-bold mb-2 ${theme.fonts.ui} text-sm ${
                        isEmpty && mode === 'load' ? theme.colors.text.separator : theme.colors.text.primary
                      }`}>
                        {theme.symbols.prefix} {slotData ? getCaseName(slotData.case_id) : `Slot ${index + 1}`}
                      </div>
                      {slotData ? (
                        <>
                          <div className={`text-sm ${theme.colors.text.tertiary} ${theme.fonts.ui}`}>
                            {theme.symbols.bullet} {formatTimestamp(slotData.timestamp)}
                          </div>
                          <div className={`text-sm ${theme.colors.text.muted} ${theme.fonts.ui}`}>
                            {theme.symbols.bullet} Location: {slotData.location}
                          </div>
                          <div className={`text-sm ${theme.colors.text.muted} ${theme.fonts.ui}`}>
                            {theme.symbols.bullet} Evidence: {slotData.evidence_count}
                          </div>
                        </>
                      ) : (
                        <div className={`text-sm ${theme.colors.text.separator} ${theme.fonts.ui} italic`}>
                          Empty slot
                        </div>
                      )}
                    </div>
                  </div>
                  <div className={`border-t ${theme.colors.border.default} pt-3 flex items-center justify-between gap-2`}>
                    <button
                      onClick={() =>
                        mode === 'save'
                          ? handleSaveClick(slotId)
                          : handleLoadClick(slotId)
                      }
                      disabled={
                        loading || (mode === 'load' && !slotData)
                      }
                      className={`flex-1 text-left ${theme.fonts.ui} text-sm font-bold transition-colors uppercase tracking-wider ${
                        isEmpty && mode === 'load'
                          ? `${theme.colors.text.separator} disabled:${theme.colors.text.separator}`
                          : isEmpty && mode === 'save'
                          ? `${theme.colors.text.primary} ${theme.colors.interactive.hover}`
                          : isSelected && !isEmpty
                          ? `${theme.colors.interactive.text} underline`
                          : `${theme.colors.text.primary} ${theme.colors.interactive.hover} disabled:${theme.colors.text.separator}`
                      } disabled:no-underline`}
                    >
                      {mode === 'save'
                        ? slotData
                          ? `${theme.symbols.doubleArrowRight} [${index + 1}] OVERWRITE`
                          : `${theme.symbols.doubleArrowRight} [${index + 1}] SAVE HERE`
                        : slotData
                        ? `${theme.symbols.doubleArrowRight} [${index + 1}] LOAD`
                        : `${theme.symbols.doubleArrowRight} [${index + 1}] EMPTY`}
                    </button>
                    {slotData && (
                      <>
                        <button
                          onClick={() => void handleExport(slotId)}
                          className={`${theme.fonts.ui} text-xs ${theme.colors.text.muted} ${theme.colors.interactive.hover} transition-colors uppercase tracking-wider`}
                          title="Export save file"
                        >
                          EXPORT
                        </button>
                        <button
                          onClick={() => setPendingDeleteSlot(slotId)}
                          disabled={loading || deleting}
                          className={`${theme.fonts.ui} text-xs text-red-400 hover:text-red-300 transition-colors uppercase tracking-wider disabled:opacity-50`}
                          title="Delete save"
                          aria-label={`Delete save in slot ${index + 1}`}
                        >
                          DELETE
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Autosave slot (load mode only) */}
            {mode === 'load' && autosaveSlot && (
              <div className={`border p-4 ${
                selectedIndex === 3
                  ? `border-amber-500/50 ${theme.colors.bg.hover}`
                  : `${theme.colors.border.default} ${theme.colors.bg.semiTransparent}`
              }`}>
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <div className={`font-bold ${theme.colors.text.primary} mb-2 ${theme.fonts.ui} text-sm`}>
                      {theme.symbols.prefix} {getCaseName(autosaveSlot.case_id)}
                    </div>
                    <div className={`text-xs ${theme.colors.text.muted} ${theme.fonts.ui} mb-1`}>
                      [Autosave]
                    </div>
                    <div className={`text-sm ${theme.colors.text.tertiary} ${theme.fonts.ui}`}>
                      {theme.symbols.bullet} {formatTimestamp(autosaveSlot.timestamp)}
                    </div>
                    <div className={`text-sm ${theme.colors.text.muted} ${theme.fonts.ui}`}>
                      {theme.symbols.bullet} Location: {autosaveSlot.location}
                    </div>
                    <div className={`text-sm ${theme.colors.text.muted} ${theme.fonts.ui}`}>
                      {theme.symbols.bullet} Evidence: {autosaveSlot.evidence_count}
                    </div>
                  </div>
                </div>
                <div className={`border-t ${theme.colors.border.default} pt-3 flex items-center justify-between gap-2`}>
                  <button
                    onClick={() => handleLoadClick('autosave')}
                    disabled={loading}
                    className={`flex-1 text-left ${theme.fonts.ui} text-sm font-bold transition-colors uppercase tracking-wider ${
                      selectedIndex === 3
                        ? `${theme.colors.interactive.text} underline`
                        : `${theme.colors.text.primary} ${theme.colors.interactive.hover}`
                    } disabled:${theme.colors.text.separator} disabled:no-underline`}
                  >
                    {theme.symbols.doubleArrowRight} [4] LOAD
                  </button>
                  <button
                    onClick={() => void handleExport('autosave')}
                    className={`${theme.fonts.ui} text-xs ${theme.colors.text.muted} ${theme.colors.interactive.hover} transition-colors uppercase tracking-wider`}
                    title="Export save file"
                  >
                    EXPORT
                  </button>
                </div>
              </div>
            )}

            {/* Import section */}
            <div className={`border-t ${theme.colors.border.default} pt-4 mt-4`}>
              <input
                ref={importInputRef}
                type="file"
                accept=".json"
                onChange={(e) => void handleImportFile(e)}
                className="hidden"
                id="import-save-file"
              />
              <label
                htmlFor="import-save-file"
                className={`block w-full text-center ${theme.fonts.ui} text-sm font-bold cursor-pointer transition-colors uppercase tracking-wider
                  ${theme.colors.text.muted} ${theme.colors.interactive.hover} border ${theme.colors.border.default} p-3`}
              >
                {theme.symbols.prefix} IMPORT SAVE FILE
              </label>
              {importStatus && (
                <div className={`text-center text-xs ${theme.fonts.ui} mt-2 ${
                  importStatus.startsWith('Import failed') || importStatus.startsWith('Failed') ? 'text-red-400' : theme.colors.text.tertiary
                }`}>
                  {importStatus}
                </div>
              )}
            </div>

            {/* Loading indicator */}
            {loading && (
              <div className={`text-center text-sm ${theme.colors.text.muted} ${theme.fonts.ui} mt-4`}>
                {theme.symbols.block} {mode === 'save' ? 'Saving...' : 'Loading...'}
              </div>
            )}
          </div>

          {/* Close button [X] */}
          <Dialog.Close asChild>
            <button
              className={`absolute top-4 right-4 ${theme.colors.text.tertiary} ${theme.colors.interactive.hover}
                         focus-visible:ring-2 focus-visible:ring-white focus-visible:outline-none
                         px-1 transition-colors ${theme.fonts.ui} text-sm`}
              aria-label="Close"
            >
              {theme.symbols.closeButton}
            </button>
          </Dialog.Close>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>

      <ConfirmDialog
        open={pendingDeleteSlot !== null}
        title="Delete Save"
        message={
          pendingDeleteSlot
            ? `Permanently delete the save in ${pendingDeleteSlot.replace('_', ' ')}? This cannot be undone.`
            : ''
        }
        confirmText={deleting ? 'Deleting...' : 'Delete'}
        cancelText="Cancel"
        destructive
        onConfirm={() => void handleConfirmDelete()}
        onCancel={() => setPendingDeleteSlot(null)}
      />
    </Dialog.Root>
  );
}