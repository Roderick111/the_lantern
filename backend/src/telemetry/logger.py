"""Telemetry event logger — fire-and-forget JSONL appender."""

import asyncio
import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Write to /app/saves/telemetry in production (Docker volume-mounted),
# falls back to local telemetry/ dir for dev
_SAVES_DIR = Path("/app/saves")
TELEMETRY_DIR = (
    _SAVES_DIR / "telemetry"
    if _SAVES_DIR.exists()
    else Path(__file__).parent.parent.parent / "telemetry"
)


def _validate_identifier(value: str, name: str) -> None:
    """Validate identifier to prevent path traversal."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", value):
        raise ValueError(f"Invalid {name} format: {value}")


def _write_event_sync(
    event_type: str,
    player_id: str,
    case_id: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Sync helper that does the actual file append. Called via to_thread."""
    _validate_identifier(player_id, "player_id")
    _validate_identifier(case_id, "case_id")

    # Restricted perms (best-effort; creation only). Prevents world-readable logs.
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        TELEMETRY_DIR.chmod(0o700)
    except (OSError, PermissionError):
        pass

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    filepath = TELEMETRY_DIR / f"{today}.jsonl"

    event = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event_type,
        "player_id": player_id,
        "case_id": case_id,
        "data": data or {},
    }

    # Use restricted file perms on create (umask may still affect)
    fd = os.open(str(filepath), os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    try:
        os.chmod(filepath, 0o600)
    except (OSError, PermissionError):
        pass


async def log_event(
    event_type: str,
    player_id: str,
    case_id: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Append one event to today's JSONL file via thread offload. Never raises."""
    try:
        await asyncio.to_thread(_write_event_sync, event_type, player_id, case_id, data)
    except Exception as e:
        logger.warning(f"Telemetry write failed: {e}")
