/**
 * MentorFeedback Component
 *
 * Displays Graves's feedback after verdict submission in an immersive style.
 *
 * @module components/MentorFeedback
 * @since Phase 3
 */

import { generateAsciiBar } from '../styles/terminal-theme';
import { useTheme } from '../context/useTheme';
import { renderInlineMarkdown } from '../utils/renderInlineMarkdown';

// ============================================
// Types
// ============================================

interface Fallacy {
  name: string;
  description: string;
  example?: string;
}

export interface MentorFeedbackData {
  analysis: string;
  fallacies_detected: Fallacy[];
  score: number;
  quality: string;
  critique: string;
  praise: string;
  hint: string | null;
}

export interface MentorFeedbackProps {
  feedback?: MentorFeedbackData;
  correct: boolean;
  attemptsRemaining: number;
  wrongSuspectResponse?: string | null;
  onRetry?: () => void;
  isLoading?: boolean;
  onConfront?: () => void;
  confrontLabel?: string;
}

// ============================================
// Helpers
// ============================================

function getQualityLabel(quality: string): string {
  const labels: Record<string, string> = {
    excellent: 'Excellent',
    good: 'Good',
    fair: 'Fair',
    poor: 'Poor',
    failing: 'Weak',
  };
  return labels[quality] || quality;
}

// ============================================
// Component
// ============================================

export function MentorFeedback({
  feedback,
  correct,
  attemptsRemaining,
  wrongSuspectResponse,
  onRetry,
  isLoading = false,
  onConfront,
  confrontLabel = 'Proceed',
}: MentorFeedbackProps) {
  const { theme } = useTheme();

  const getScoreColor = (score: number): string => {
    if (score >= 75) return theme.colors.state.success.text;
    if (score >= 50) return theme.colors.state.warning.text;
    return theme.colors.state.error.text;
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4" role="status" aria-live="polite" aria-busy="true">
        <div
          className={`animate-spin h-6 w-6 border-2 ${theme.colors.border.default} border-t-transparent rounded-full`}
          aria-hidden="true"
        />
        <p className={`${theme.fonts.narrative} italic ${theme.colors.text.muted} text-sm`}>
          Graves is reviewing your case...
        </p>
      </div>
    );
  }

  if (!feedback) return null;

  return (
    <div className="space-y-6">
      {/* Verdict Result — centered, prominent */}
      <div className="text-center space-y-1">
        <p className={`text-xs ${theme.colors.text.separator} ${theme.fonts.ui} uppercase tracking-widest`}>
          Verdict
        </p>
        <p className={`text-lg font-bold ${theme.fonts.ui} uppercase tracking-wider ${
          correct ? theme.colors.state.success.text : theme.colors.state.error.text
        }`}>
          {correct ? 'Correct' : 'Incorrect'}
        </p>
      </div>

      {/* Divider */}
      <div className={`border-t ${theme.colors.border.default}`} />

      {/* Graves's Response */}
      {feedback.analysis && (
        <div className="space-y-2">
          <p className={`text-xs ${theme.colors.text.muted} ${theme.fonts.ui} uppercase tracking-widest font-bold`}>
            Graves's response
          </p>
          <div className={`${theme.fonts.narrative} text-sm ${theme.colors.text.secondary} whitespace-pre-wrap leading-relaxed text-justify space-y-3`}>
            {feedback.analysis.split('\n').filter(Boolean).map((para, i) => (
              <p key={i}>{renderInlineMarkdown(para)}</p>
            ))}
          </div>
        </div>
      )}

      {/* Pre-written wrong suspect response */}
      {!correct && wrongSuspectResponse && (
        <>
          <div className={`border-t ${theme.colors.border.default}`} />
          <div className="space-y-2">
            <p className={`text-xs ${theme.colors.state.error.text} ${theme.fonts.ui} uppercase tracking-widest font-bold`}>
              Case notes
            </p>
            <p className={`${theme.fonts.narrative} text-sm ${theme.colors.text.secondary} whitespace-pre-wrap leading-relaxed text-justify`}>
              {renderInlineMarkdown(wrongSuspectResponse || '')}
            </p>
          </div>
        </>
      )}

      {/* Divider */}
      <div className={`border-t ${theme.colors.border.default}`} />

      {/* Score — compact row */}
      <div className="space-y-2">
        <div className="flex items-baseline justify-between">
          <p className={`text-xs ${theme.colors.text.muted} ${theme.fonts.ui} uppercase tracking-widest font-bold`}>
            Reasoning quality
          </p>
          <span className={`text-xs ${theme.fonts.ui} italic ${theme.colors.text.separator}`}>
            {getQualityLabel(feedback.quality)}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div
            className="flex-1"
            role="progressbar"
            aria-valuenow={feedback.score}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Reasoning score: ${feedback.score} out of 100`}
          >
            <span className={`font-mono text-sm tracking-widest ${getScoreColor(feedback.score)}`}>
              {generateAsciiBar(feedback.score, 20)}
            </span>
          </div>
          <span className={`text-sm font-bold ${theme.fonts.ui} ${getScoreColor(feedback.score)}`}>
            {feedback.score}
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className={`border-t ${theme.colors.border.default}`} />

      {/* Action Buttons */}
      {(() => {
        const showRetry = attemptsRemaining > 0 && onRetry && (feedback.score < 70 || !correct);
        const bothVisible = showRetry && onConfront;

        return (
          <div className={bothVisible ? 'flex gap-3' : 'space-y-3'}>
            {/* Retry — blue accent when score < 70 */}
            {showRetry && (
              <button
                onClick={onRetry}
                className={`py-3 px-4 ${theme.fonts.ui} text-sm uppercase tracking-widest transition-all duration-200 group focus:outline-none
                           ${bothVisible ? 'flex-1' : 'w-full'}
                           ${feedback.score < 70
                             ? 'border border-blue-500 bg-blue-500/10 text-blue-400 font-bold hover:bg-blue-500/20'
                             : `border ${theme.colors.border.default} ${theme.colors.text.primary} hover:${theme.colors.bg.hover}`
                           }`}
              >
                <span className="flex items-center justify-center">
                  <span className="mr-2 group-hover:-translate-x-1 transition-transform duration-200">↩</span>
                  {feedback.score < 70 && correct ? 'Prove It Wasn\'t Luck' : 'Try Again'}
                </span>
              </button>
            )}

            {/* Confrontation/Proceed Button */}
            {onConfront && (
              <button
                onClick={onConfront}
                className={`py-3 px-4 border ${theme.colors.border.default} ${theme.fonts.ui} text-sm uppercase tracking-widest
                           hover:${theme.colors.bg.hover} transition-all duration-200 group focus:outline-none
                           ${bothVisible ? 'flex-1' : 'w-full'}
                           ${feedback.score < 70 && showRetry ? theme.colors.text.muted : theme.colors.text.primary}`}
              >
                <span className="flex items-center justify-center">
                  {confrontLabel}
                  <span className="ml-2 group-hover:translate-x-1 transition-transform duration-200">{theme.symbols.arrowRight}</span>
                </span>
              </button>
            )}
          </div>
        );
      })()}

      {/* Attempts remaining — quiet footer */}
      {!correct && (
        <p className={`text-xs ${theme.colors.text.separator} ${theme.fonts.ui} text-center italic`}>
          {attemptsRemaining} attempt{attemptsRemaining !== 1 ? 's' : ''} remaining
        </p>
      )}

      {/* Out of attempts */}
      {!correct && attemptsRemaining === 0 && (
        <p className={`${theme.fonts.narrative} italic text-sm ${theme.colors.state.error.text} text-center`}>
          You have exhausted all attempts. The truth will now be revealed.
        </p>
      )}
    </div>
  );
}
