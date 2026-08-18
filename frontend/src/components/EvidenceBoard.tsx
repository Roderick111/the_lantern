/**
 * EvidenceBoard Component
 *
 * Displays discovered evidence in a minimal B&W terminal aesthetic sidebar.
 * Auto-updates when new evidence is discovered during investigation.
 * Uses centralized design system for consistent styling.
 *
 * @module components/EvidenceBoard
 * @since Phase 1
 * @updated Phase 5.3.1 (Design System)
 */

import { useMemo } from "react";
import { TerminalPanel } from "./ui/TerminalPanel";
import { useTheme } from '../context/useTheme';

// ============================================
// Types
// ============================================

interface EvidenceBoardProps {
  /** Array of discovered evidence IDs */
  evidence: string[];
  /** Localized display names keyed by stable evidence IDs */
  evidenceNames?: Record<string, string>;
  /** Current case ID */
  caseId: string;
  /** Optional: Compact mode for smaller displays */
  compact?: boolean;
  /** Callback when evidence is clicked for details */
  onEvidenceClick?: (evidenceId: string) => void;
  /** Whether panel can be collapsed */
  collapsible?: boolean;
  /** Initial collapsed state */
  defaultCollapsed?: boolean;
  /** Optional key to persist collapsed state */
  persistenceKey?: string;
  /** Bare mode: render content without TerminalPanel wrapper (for use inside modals) */
  bare?: boolean;
}

// ============================================
// Component
// ============================================

export function EvidenceBoard({
  evidence,
  evidenceNames,
  caseId: _caseId,
  compact: _compact = false,
  onEvidenceClick,
  collapsible = false,
  defaultCollapsed = false,
  persistenceKey,
  bare = false,
}: EvidenceBoardProps) {
  const { theme } = useTheme();

  // Memoize the formatted evidence list to prevent re-computation on every render.
  const formattedEvidence = useMemo(
    () =>
      evidence.map((evidenceId, index) => ({
        id: evidenceId,
        formattedId: evidenceNames?.[evidenceId] ?? formatEvidenceId(evidenceId),
        displayIndex: String(index + 1).padStart(2, "0"),
      })),
    [evidence, evidenceNames],
  );

  // Empty state
  if (evidence.length === 0) {
    const emptyContent = (
      <div className="py-6 text-center">
        <p className={`${theme.colors.text.muted} text-sm`}>No evidence discovered yet</p>
        <p className={`${theme.colors.text.separator} text-xs mt-2`}>
          Investigate the location to find clues
        </p>
      </div>
    );
    if (bare) return emptyContent;
    return (
      <TerminalPanel title="EVIDENCE BOARD" collapsible={collapsible} defaultCollapsed={defaultCollapsed} persistenceKey={persistenceKey}>
        {emptyContent}
      </TerminalPanel>
    );
  }

  const listContent = (
    <ul className="space-y-3">
      {formattedEvidence.map((item) => (
        <li key={item.id}>
          <button
            onClick={() => onEvidenceClick?.(item.id)}
            className={`w-full text-left p-4 border group transition-all duration-200
              ${theme.colors.border.default} ${theme.colors.bg.primary} ${theme.colors.interactive.borderHover} ${theme.colors.bg.hoverClass}
              cursor-pointer shadow-sm hover:shadow-md
              focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:outline-none`}
            type="button"
            aria-label={`View details for ${item.formattedId}`}
          >
            <div className="flex items-start justify-between">
              <h3 className={`${theme.fonts.ui} font-bold uppercase tracking-wider text-sm flex items-center gap-2 ${theme.colors.text.primary}`}>
                <span className={`${theme.colors.text.muted} group-hover:text-amber-400 transition-colors`}>
                  {theme.symbols.bullet}
                </span>
                {item.formattedId}
              </h3>
              <span className={`${theme.colors.text.separator} text-xs ${theme.fonts.ui}`}>
                #{item.displayIndex}
              </span>
            </div>
          </button>
        </li>
      ))}
    </ul>
  );

  if (bare) return listContent;

  return (
    <TerminalPanel
      title="EVIDENCE BOARD"
      subtitle={`${evidence.length} ITEM${evidence.length === 1 ? "" : "S"}`}
      footer="Click on evidence to view details"
      collapsible={collapsible}
      defaultCollapsed={defaultCollapsed}
      persistenceKey={persistenceKey}
    >
      {listContent}
    </TerminalPanel>
  );
}

// ============================================
// Helpers
// ============================================

/**
 * Format evidence ID for display
 * Converts snake_case to Title Case with spaces
 *
 * @example
 * formatEvidenceId("hidden_note") // "Hidden Note"
 * formatEvidenceId("focus_signature") // "Focus Signature"
 */
function formatEvidenceId(id: string): string {
  return id
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}
