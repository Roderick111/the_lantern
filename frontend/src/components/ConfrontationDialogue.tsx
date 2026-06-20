/**
 * ConfrontationDialogue Component
 *
 * Post-verdict confrontation scene with immersive narrative design.
 *
 * @module components/ConfrontationDialogue
 * @since Phase 3
 */

import { useTheme } from '../context/useTheme';
import { renderInlineMarkdown } from '../utils/renderInlineMarkdown';
import type { TerminalTheme } from '../styles/terminal-theme';

// ============================================
// Types
// ============================================

export interface DialogueLine {
  speaker: string;
  text: string;
  tone?: string;
}

export interface ConfrontationDialogueData {
  dialogue: DialogueLine[];
  aftermath: string;
}

export interface ConfrontationDialogueProps {
  dialogue: DialogueLine[];
  aftermath: string;
  onClose: () => void;
  caseSolvedCorrectly?: boolean;
}

// ============================================
// Helper Functions
// ============================================

function getSpeakerColor(speaker: string, theme: TerminalTheme): string {
  const speakerLower = speaker.toLowerCase();
  const charTheme = theme.colors.character;
  if (speakerLower === "graves") return charTheme.detective.text;
  if (speakerLower === "player" || speakerLower === "you")
    return charTheme.detective.text;
  return charTheme.witness.text;
}

function formatSpeakerName(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1).toLowerCase();
}

// ============================================
// Sub-components
// ============================================

function DialogueBubble({ line, theme }: { line: DialogueLine; theme: TerminalTheme }) {
  const paragraphs = line.text.split('\n').filter(Boolean);

  return (
    <div className="space-y-1">
      {/* Speaker + tone */}
      <div className="flex items-baseline gap-2">
        <span className={`text-sm font-bold uppercase tracking-widest ${getSpeakerColor(line.speaker, theme)}`}>
          {formatSpeakerName(line.speaker)}
        </span>
        {line.tone && (
          <span className={`text-xs ${theme.colors.text.separator} italic`}>
            {line.tone}
          </span>
        )}
      </div>

      {/* Text as paragraphs */}
      <div className={`${theme.fonts.narrative} text-base ${theme.colors.text.secondary} leading-[28px] tracking-[0.1px] text-justify space-y-3`}>
        {paragraphs.map((para, i) => (
          <p key={i}>{renderInlineMarkdown(para)}</p>
        ))}
      </div>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function ConfrontationDialogue({
  dialogue,
  aftermath,
  onClose,
  caseSolvedCorrectly = true,
}: ConfrontationDialogueProps) {
  const { theme } = useTheme();

  return (
    <div className="space-y-6">
      {/* Case Solved — minimal centered banner */}
      <div className="text-center space-y-1">
        <p className={`text-xs ${theme.colors.text.separator} ${theme.fonts.ui} uppercase tracking-widest`}>
          {caseSolvedCorrectly ? 'Case Solved' : 'Case Resolved'}
        </p>
        <p className={`text-lg font-bold ${theme.fonts.ui} uppercase tracking-wider ${
          caseSolvedCorrectly ? theme.colors.state.success.text : theme.colors.text.secondary
        }`}>
          {caseSolvedCorrectly ? 'Justice Has Been Served' : 'The Truth Is Revealed'}
        </p>
      </div>

      {/* Divider */}
      <div className={`border-t ${theme.colors.border.default}`} />

      {/* Dialogue */}
      <div className="space-y-6">
        {dialogue.map((line, idx) => (
          <DialogueBubble key={idx} line={line} theme={theme} />
        ))}
      </div>

      {/* Aftermath */}
      {aftermath && (
        <>
          <div className={`border-t ${theme.colors.border.default}`} />

          <div className="space-y-2">
            <p className={`text-sm ${theme.colors.text.muted} ${theme.fonts.ui} uppercase tracking-widest font-bold text-center`}>
              Aftermath
            </p>
            <div className={`${theme.fonts.narrative} text-base ${theme.colors.text.muted} italic leading-[28px] tracking-[0.1px] text-justify space-y-3`}>
              {aftermath.split('\n').filter(Boolean).map((para, i) => (
                <p key={i}>{renderInlineMarkdown(para)}</p>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Divider */}
      <div className={`border-t ${theme.colors.border.default}`} />

      {/* Close Button — consistent with other modals */}
      <button
        onClick={onClose}
        className={`w-full py-3 px-4 border ${theme.colors.border.default} ${theme.colors.text.primary} ${theme.fonts.ui} text-sm uppercase tracking-widest
                   hover:${theme.colors.bg.hover} transition-all duration-200 group focus:outline-none`}
      >
        <span className="flex items-center justify-center">
          Close Case File
          <span className="ml-2 group-hover:translate-x-1 transition-transform duration-200">{theme.symbols.arrowRight}</span>
        </span>
      </button>
    </div>
  );
}
