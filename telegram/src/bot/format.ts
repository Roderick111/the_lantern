import { TELEGRAM_MAX_MESSAGE } from "../domain/types";

/** Escape for Telegram HTML parse mode. */
export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * Split long reply at paragraph boundaries under maxLen.
 * Order preserved. Last chunk gets buttons in delivery layer.
 */
export function splitMessage(text: string, maxLen = TELEGRAM_MAX_MESSAGE): string[] {
  if (text.length <= maxLen) return [text];

  const paragraphs = text.split(/\n\n+/);
  const chunks: string[] = [];
  let current = "";

  const push = (s: string) => {
    if (s) chunks.push(s);
  };

  for (const p of paragraphs) {
    const piece = p;
    if (piece.length > maxLen) {
      push(current);
      current = "";
      // hard-split oversized paragraph
      for (let i = 0; i < piece.length; i += maxLen) {
        chunks.push(piece.slice(i, i + maxLen));
      }
      continue;
    }
    const next = current ? `${current}\n\n${piece}` : piece;
    if (next.length > maxLen) {
      push(current);
      current = piece;
    } else {
      current = next;
    }
  }
  push(current);
  return chunks.length > 0 ? chunks : [text.slice(0, maxLen)];
}
