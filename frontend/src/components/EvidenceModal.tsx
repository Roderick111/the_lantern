/**
 * EvidenceModal Component
 *
 * Modal displaying detailed evidence information with terminal UI aesthetic.
 * Shows evidence name, location found, and full description.
 *
 * @module components/EvidenceModal
 * @since Phase 2.5
 */

import { Modal } from './ui/Modal';
import { useTheme } from '../context/useTheme';
import { renderInlineMarkdown } from '../utils/renderInlineMarkdown';
import type { EvidenceDetails } from '../types/investigation';

// ============================================
// Types
// ============================================

function formatLocationName(id: string): string {
  return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

interface EvidenceModalProps {
  /** Evidence details to display (null to hide modal) */
  evidence: EvidenceDetails | null;
  /** Callback when modal is closed */
  onClose: () => void;
  /** Callback to go back to evidence list */
  onBack?: () => void;
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string | null;
}

// ============================================
// Component
// ============================================

export function EvidenceModal({
  evidence,
  onClose,
  onBack,
  loading = false,
  error = null,
}: EvidenceModalProps) {
  const { theme } = useTheme();

  const isOpen = loading || !!error || !!evidence;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="EVIDENCE DETAILS" variant="terminal" maxWidth="max-w-lg">
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className={`animate-pulse ${theme.colors.state.success.text}`}>
            Loading evidence details...
          </div>
        </div>
      ) : error ? (
        <div className={`p-4 ${theme.colors.state.error.bg} border ${theme.colors.state.error.border} rounded-sm ${theme.colors.state.error.text} text-sm`}>
          <span className="font-bold">{theme.messages.error('')}</span> {error}
        </div>
      ) : evidence ? (
        <div className="space-y-5">
          <div className="text-center">
            <h3 className={`${theme.fonts.narrative} text-lg ${theme.colors.text.primary} font-semibold`}>
              {evidence.name}
            </h3>
            <p className={`text-xs ${theme.colors.text.muted} uppercase tracking-widest mt-1 ${theme.fonts.ui}`}>
              Found in {formatLocationName(evidence.location_found)}
            </p>
          </div>

          <div className={`border-t ${theme.colors.border.default}`} />

          <p className={`${theme.fonts.ui} text-sm ${theme.colors.text.secondary} leading-relaxed text-justify`}>
            {renderInlineMarkdown(evidence.description)}
          </p>

          {onBack && (
            <>
              <div className={`border-t ${theme.colors.border.default}`} />
              <button
                onClick={onBack}
                className={`w-full text-center text-sm ${theme.colors.text.muted} ${theme.fonts.ui} uppercase tracking-widest py-1 hover:${theme.colors.text.primary} transition-colors`}
              >
                ← Back to Evidence
              </button>
            </>
          )}
        </div>
      ) : null}
    </Modal>
  );
}
