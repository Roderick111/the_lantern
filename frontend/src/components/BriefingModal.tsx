/**
 * BriefingModal Component
 *
 * Case dossier briefing — player reviews case details then starts investigation.
 *
 * @module components/BriefingModal
 * @since Phase 3.6 (Redesign Phase 5.x)
 */

import { useTheme } from '../context/useTheme';
import { BriefingDossier } from "./BriefingDossier";
import type { BriefingContent } from "../types/investigation";

// ============================================
// Types
// ============================================

export interface BriefingModalProps {
  /** Briefing content from backend */
  briefing: BriefingContent;
  /** Callback when player clicks "Start Investigation" */
  onComplete: () => void;
  /** Whether an API call is in progress */
  loading: boolean;
  /** Error message from briefing API */
  error?: string | null;
  /** Optional callback to close the modal without completing */
  onClose?: () => void;
}

export function BriefingModal({
  briefing,
  onComplete,
  loading,
  error,
  onClose,
}: BriefingModalProps) {
  const { theme } = useTheme();

  return (
    <div
      className={`
      relative w-full max-h-[min(720px,calc(100vh-2rem))] overflow-y-auto flex flex-col ${theme.fonts.narrative} ${theme.colors.text.secondary}
      ${theme.colors.bg.primary} border ${theme.colors.border.default}
      ${theme.typography.body}
    `}
    >
      {/* Unified Folder Header */}
      <div className={`flex items-center justify-between px-4 md:px-6 py-3 border-b ${theme.colors.border.default}`}>
        <h2 className={`${theme.typography.header} font-bold`}>
          {`CASE DOSSIER: ${briefing.dossier.title}`}
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            className={`${theme.colors.text.muted} ${theme.colors.text.primaryHover} transition-colors ${theme.fonts.ui} text-base`}
            aria-label="Close Case Briefing"
          >
            [X]
          </button>
        )}
      </div>

      {error && (
        <div
          className={`mx-4 md:mx-8 mt-4 px-4 py-2 border ${theme.colors.border.default} ${theme.colors.text.muted} ${theme.typography.caption}`}
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-grow p-4 md:p-6">
        <BriefingDossier
          dossier={briefing.dossier}
          onContinue={onComplete}
          continueLabel={loading ? "SAVING..." : "START INVESTIGATION"}
        />
      </div>
    </div>
  );
}
