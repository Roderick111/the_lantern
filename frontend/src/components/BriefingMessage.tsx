/**
 * BriefingMessage Component
 *
 * Simple message bubble for dialogue-based briefing UI.
 * Displays speaker name (GRAVES or YOU) and text content.
 *
 * @module components/BriefingMessage
 * @since Phase 3.6
 */

import { useTheme } from '../context/useTheme';
import { renderInlineMarkdown } from '../utils/renderInlineMarkdown';

export interface BriefingMessageProps {
  /** Speaker of the message */
  speaker: 'graves' | 'player';
  /** Message text content */
  text: string;
}

export function BriefingMessage({ speaker, text }: BriefingMessageProps) {
  const { theme } = useTheme();
  const isGraves = speaker === 'graves';

  // Use narrator style for Graves (mentor), player style for player
  const wrapperClass = isGraves
    ? theme.components.message.narrator.wrapper
    : theme.components.message.player.wrapper;

  const textClass = isGraves
    ? theme.components.message.narrator.text
    : theme.components.message.player.text;

  return (
    <div className={wrapperClass}>
      <p className={textClass}>
        {!isGraves && <span className={theme.components.message.player.prefix}>{theme.symbols.inputPrefix}</span>}
        {renderInlineMarkdown(text)}
      </p>
    </div>
  );
}
