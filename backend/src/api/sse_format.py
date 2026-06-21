"""SSE event formatting — avoid per-chunk dict allocation where possible."""

from __future__ import annotations

import json
from typing import Any


def sse_text_event(text: str) -> str:
    """Format a single SSE text chunk event."""
    return f"data: {{\"text\": {json.dumps(text)}}}\n\n"


def sse_json_event(payload: dict[str, Any]) -> str:
    """Format an SSE event from a JSON-serializable payload."""
    return f"data: {json.dumps(payload)}\n\n"
