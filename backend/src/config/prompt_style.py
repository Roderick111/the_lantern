"""Shared prose constraints for generated game text."""

ANTI_AI_STYLE_FILTER = """STYLE FILTER:
- Maximum one em dash per response, with spaces.
- Never use exactly three items in a list or sequence.
- Avoid contrast framing such as \"not X, but Y\" or \"Not X. Y.\"
- Avoid three short sentences stacked for dramatic effect.
- Avoid rhetorical or formal transitions.
- Avoid self-narration, empty setup, and weightless summary sentences.
- Replace vague scale claims with concrete details.
- Avoid generic sentence-final -ing clauses.
- Avoid significance inflation and all-caps emphasis."""
