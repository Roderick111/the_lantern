"""Game language configuration.

Provides language instruction blocks for LLM prompts.
Generated narration/dialogue follows this instruction; authored case text comes
from the locale overlay while IDs and structured tags stay stable.
"""

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "ru": "Russian",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "pt": "Portuguese",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "it": "Italian",
}


def get_language_instruction(language: str) -> str:
    """Return language instruction block for LLM prompts.

    Returns empty string for English (default, no extra prompt noise).
    For other languages, returns an all-caps instruction block.

    Args:
        language: ISO 639-1 code (e.g. "en", "ru", "fr")

    Returns:
        Language instruction string to append to system prompts
    """
    if language == "en" or language not in SUPPORTED_LANGUAGES:
        return ""

    lang_name = SUPPORTED_LANGUAGES[language]

    return f"""

LANGUAGE RULE: YOU MUST RESPOND IN {lang_name.upper()}.
Translate ONLY narration and dialogue text. DO NOT translate any of the following: \
they must remain exactly as defined in English:
- Evidence tags: [EVIDENCE_ID]
- Trust tags: [TRUST_DELTA: N]
- Evidence IDs, secret IDs, witness IDs
- Spell names and incantations
- Any bracketed metadata or structured output
- JSON output format (keys and structure)"""
