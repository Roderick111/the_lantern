/**
 * VerdictSubmission Component
 *
 * Immersive verdict submission form styled to match the game's narrative aesthetic.
 *
 * @module components/VerdictSubmission
 * @since Phase 3
 */

import { useState, useCallback } from 'react';
import { useTheme } from '../context/useTheme';

// ============================================
// Types
// ============================================

interface Suspect {
  id: string;
  name: string;
}

interface Evidence {
  id: string;
  name: string;
}

export interface VerdictSubmissionProps {
  suspects: Suspect[];
  discoveredEvidence: Evidence[];
  onSubmit: (accusedId: string, reasoning: string, evidenceCited: string[]) => Promise<void>;
  loading: boolean;
  disabled: boolean;
  attemptsRemaining?: number;
}

// ============================================
// Constants
// ============================================

const MIN_REASONING_LENGTH = 50;

// ============================================
// Component
// ============================================

export function VerdictSubmission({
  suspects,
  discoveredEvidence,
  onSubmit,
  loading,
  disabled,
  attemptsRemaining,
}: VerdictSubmissionProps) {
  const { theme } = useTheme();
  const [accusedSuspect, setAccusedSuspect] = useState<string>('');
  const [reasoning, setReasoning] = useState<string>('');
  const [selectedEvidence, setSelectedEvidence] = useState<string[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleEvidenceToggle = useCallback((evidenceId: string) => {
    setSelectedEvidence((prev) =>
      prev.includes(evidenceId)
        ? prev.filter((id) => id !== evidenceId)
        : [...prev, evidenceId],
    );
  }, []);

  const handleSubmit = useCallback(async () => {
    setValidationError(null);

    if (!accusedSuspect) {
      setValidationError('You must name a suspect.');
      return;
    }

    if (reasoning.length < MIN_REASONING_LENGTH) {
      setValidationError(`Your reasoning needs at least ${MIN_REASONING_LENGTH} characters.`);
      return;
    }

    try {
      await onSubmit(accusedSuspect, reasoning, selectedEvidence);
    } catch (err) {
      console.error('[VerdictSubmission] Failed to submit verdict:', err);
      setValidationError('Something went wrong. Please try again.');
    }
  }, [accusedSuspect, reasoning, selectedEvidence, onSubmit]);

  const isValid = accusedSuspect && reasoning.length >= MIN_REASONING_LENGTH;
  const reasoningMet = reasoning.length >= MIN_REASONING_LENGTH;

  return (
    <div className="space-y-6">
      {/* Graves's intro */}
      <p className={`${theme.fonts.narrative} italic ${theme.colors.text.muted} text-sm text-center`}>
        "Present your case, cadet. Choose your words carefully."
      </p>

      {/* Suspect Selector */}
      <div className="space-y-2">
        <label
          htmlFor="suspect-select"
          className={`text-xs ${theme.colors.text.muted} ${theme.fonts.ui} uppercase tracking-widest font-bold`}
        >
          Who is responsible?
        </label>
        <div className="relative">
          <select
            id="suspect-select"
            value={accusedSuspect}
            onChange={(e) => setAccusedSuspect(e.target.value)}
            disabled={disabled || loading}
            className={`w-full ${theme.colors.bg.primary} border ${theme.colors.border.default} rounded-sm px-3 py-3 ${theme.colors.text.secondary} ${theme.fonts.input} text-sm
                       focus:outline-none focus:${theme.colors.border.hover} transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed appearance-none`}
            aria-label="Select suspect"
          >
            <option value="">Choose a suspect...</option>
            {suspects.map((suspect) => (
              <option key={suspect.id} value={suspect.id}>
                {suspect.name}
              </option>
            ))}
          </select>
          <div className={`absolute right-3 top-3.5 pointer-events-none ${theme.colors.text.muted} text-xs`}>
            {theme.symbols.arrowDown}
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className={`border-t ${theme.colors.border.default}`} />

      {/* Reasoning Textarea */}
      <div className="space-y-2">
        <label
          htmlFor="reasoning-input"
          className={`text-xs ${theme.colors.text.muted} ${theme.fonts.ui} uppercase tracking-widest font-bold`}
        >
          Present your reasoning
        </label>
        <div className="relative">
          <textarea
            id="reasoning-input"
            value={reasoning}
            onChange={(e) => setReasoning(e.target.value)}
            disabled={disabled || loading}
            rows={3}
            placeholder="Describe your deduction..."
            className={`w-full ${theme.colors.bg.primary} border ${theme.colors.border.default} rounded-sm p-3 pr-16 ${theme.colors.text.secondary} ${theme.fonts.narrative} text-sm
                       focus:outline-none focus:${theme.colors.border.hover}
                       resize-none disabled:opacity-50 disabled:cursor-not-allowed transition-colors`}
            aria-label="Enter your reasoning"
          />
          <span className={`absolute bottom-2 right-3 text-xs ${theme.fonts.ui} tracking-wider ${reasoningMet ? theme.colors.state.success.text : theme.colors.text.separator}`}>
            {reasoningMet ? `${reasoning.length} chars` : `min ${MIN_REASONING_LENGTH - reasoning.length} more`}
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className={`border-t ${theme.colors.border.default}`} />

      {/* Evidence */}
      {discoveredEvidence.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <label className={`text-xs ${theme.colors.text.muted} ${theme.fonts.ui} uppercase tracking-widest font-bold`}>
              Supporting evidence
            </label>
            <span className={`text-xs ${theme.colors.text.separator} ${theme.fonts.ui} italic`}>
              optional
            </span>
          </div>
          <div className="space-y-1 max-h-48 overflow-y-auto scrollbar-thin">
            {discoveredEvidence.map((evidence) => {
              const isSelected = selectedEvidence.includes(evidence.id);
              return (
                <button
                  key={evidence.id}
                  type="button"
                  onClick={() => handleEvidenceToggle(evidence.id)}
                  disabled={disabled || loading}
                  className={`w-full flex items-center justify-between px-3 py-2 text-sm ${theme.fonts.ui} transition-colors
                             disabled:opacity-50 disabled:cursor-not-allowed
                             ${isSelected
                               ? `${theme.colors.text.primary} ${theme.colors.bg.active} border ${theme.colors.border.default}`
                               : `${theme.colors.text.secondary} border ${theme.colors.border.default} ${theme.colors.bg.hoverClass} hover:${theme.colors.text.primary} hover:${theme.colors.border.hover}`
                             }`}
                >
                  <span className="flex items-center gap-2">
                    <span className={`font-bold ${isSelected ? theme.colors.state.success.text : theme.colors.text.separator}`}>
                      {theme.symbols.bullet}
                    </span>
                    {evidence.name}
                  </span>
                  {isSelected && (
                    <span className={`text-xs ${theme.colors.state.success.text}`}>
                      ✓
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          {selectedEvidence.length > 0 && (
            <p className={`text-xs ${theme.colors.text.muted} ${theme.fonts.ui} px-1`}>
              {selectedEvidence.length} piece{selectedEvidence.length !== 1 ? 's' : ''} cited
            </p>
          )}
        </div>
      )}

      {/* Validation Error */}
      {validationError && (
        <div className={`p-3 border ${theme.colors.state.error.border} ${theme.animation.fadeIn}`}>
          <p className={`text-sm ${theme.colors.state.error.text} ${theme.fonts.narrative} italic text-center`}>
            {validationError}
          </p>
        </div>
      )}

      {/* Disabled Warning */}
      {disabled && (
        <div className={`p-3 ${theme.colors.bg.hover} border ${theme.colors.border.default}`}>
          <p className={`text-sm ${theme.colors.text.muted} ${theme.fonts.narrative} italic text-center`}>
            {attemptsRemaining === 0
              ? 'You have exhausted all attempts. The case is closed.'
              : 'Verdict submission is currently locked.'}
          </p>
        </div>
      )}

      {/* Submit + Footer */}
      <div className={`pt-4 border-t ${theme.colors.border.default} space-y-3`}>
        <button
          onClick={() => void handleSubmit()}
          disabled={disabled || loading || !isValid}
          className={`w-full py-3 px-4 border ${theme.colors.border.default} ${theme.colors.text.primary} ${theme.fonts.ui} text-sm uppercase tracking-widest
                     hover:${theme.colors.bg.hover} transition-all duration-200 group
                     disabled:opacity-30 disabled:cursor-not-allowed
                     focus:outline-none`}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin">/</span>
              Analyzing...
            </span>
          ) : (
            <span className="flex items-center justify-center">
              Submit Verdict
              <span className="ml-2 group-hover:translate-x-1 transition-transform duration-200">{theme.symbols.arrowRight}</span>
            </span>
          )}
        </button>
        {attemptsRemaining !== undefined && (
          <p className={`text-xs ${theme.colors.text.separator} ${theme.fonts.ui} text-center italic`}>
            {attemptsRemaining} attempt{attemptsRemaining !== 1 ? 's' : ''} remaining
          </p>
        )}
      </div>
    </div>
  );
}
