/**
 * Detect and strip spirit-companion chat prefixes from player input.
 * Accepts Russian and English companion names plus generic voice prefixes.
 */

const MATTHEW_NAME =
  "(?:matthew|матвей|матвея|матвею|матвеем|матвее|matvey|matvei|inner\\s+voice|voice)";

const MATTHEW_PREFIX = new RegExp(
  `^${MATTHEW_NAME}\\s*[,:]?\\s+`,
  "iu",
);

const MATTHEW_INTENT = new RegExp(
  `^(?:(?:hey\\s+)?(?:ask|tell|talk\\s+to)|спроси|скажи|поговори\\s+с)\\s+${MATTHEW_NAME}(?=\\s|[,:!?]|$)`,
  "iu",
);

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
        new RegExp(
          `^(?:(?:hey\\s+)?(?:ask|tell|talk\\s+to)|спроси|скажи|поговори\\s+с)\\s+${MATTHEW_NAME}\\s*[,:]?\\s*`,
          "iu",
        ),
        "",
      )
      .trim();
  }
  return trimmed;
}

/** Default prompt inserted by quick-action buttons. */
export const MATTHEW_QUICK_PROMPT = "Matthew, what do you think?";
export const MATVEY_QUICK_PROMPT = "Матвей, что думаешь?";
