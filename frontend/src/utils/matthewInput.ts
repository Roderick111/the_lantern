/**
 * Detect and strip spirit-companion chat prefixes from player input.
 * Accepts "Matthew,", "Voice,", and "Inner voice," prefixes.
 */

const MATTHEW_PREFIX =
  /^(?:matthew|inner\s+voice|voice)\s*[,:]?\s+/i;

const MATTHEW_INTENT =
  /^(?:hey\s+)?(?:ask|tell|talk\s+to)\s+(?:matthew|inner\s+voice|voice)\b/i;

/** True when the player is addressing Matthew (spirit companion). */
export function isMatthewMessage(input: string): boolean {
  const trimmed = input.trim();
  return MATTHEW_PREFIX.test(trimmed) || MATTHEW_INTENT.test(trimmed);
}

/** Remove Matthew addressing prefix before sending to the API. */
export function stripMatthewPrefix(input: string): string {
  const trimmed = input.trim();
  if (MATTHEW_PREFIX.test(trimmed)) {
    return trimmed.replace(MATTHEW_PREFIX, "").trim();
  }
  if (MATTHEW_INTENT.test(trimmed)) {
    return trimmed
      .replace(
        /^(?:hey\s+)?(?:ask|tell|talk\s+to)\s+(?:matthew|inner\s+voice|voice)\s*[,:]?\s*/i,
        "",
      )
      .trim();
  }
  return trimmed;
}

/** Default prompt inserted by quick-action buttons. */
export const MATTHEW_QUICK_PROMPT = "Matthew, what do you think?";