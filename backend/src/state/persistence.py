"""Player state persistence (SQLite storage).

Saves and loads player state to/from a local SQLite database (`lantern.db`).

Multi-slot save system:
- Supports 4 slots: slot_1, slot_2, slot_3, autosave
- Backward compatible: "default" slot maps to autosave
- JSON state stored as TEXT column
"""

import json
import logging
import os
import re
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .exceptions import StaleStateError
from .player_state import PlayerState

logger = logging.getLogger(__name__)

# Valid save slots
VALID_SLOTS = {"slot_1", "slot_2", "slot_3", "autosave", "default"}


class CorruptSaveError(ValueError):
    """Raised when a save row exists but cannot be deserialized into PlayerState."""


def _resolve_db_path() -> Path:
    """Resolve SQLite path: env override, Docker volume, or local dev fallback."""
    env_path = os.environ.get("LANTERN_DB_PATH")
    if env_path:
        return Path(env_path)

    saves_dir = Path("/app/saves")
    if saves_dir.exists():
        return saves_dir / "lantern.db"
    return Path(__file__).parent.parent.parent / "saves" / "lantern.db"


_DB_PATH = _resolve_db_path()

_conn: sqlite3.Connection | None = None
_db_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    """Get or create a reusable SQLite connection."""
    global _conn
    if _conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=5000")
    return _conn


def close_db() -> None:
    """Close the database connection."""
    global _conn
    if _conn is not None:
        _conn.close()
        logger.info("Database connection closed")
    _conn = None


def init_db() -> None:
    """Create saves table if it doesn't exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saves (
            player_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            slot TEXT NOT NULL,
            state TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            save_revision INTEGER NOT NULL DEFAULT 0,
            evidence_count INTEGER,
            current_location TEXT,
            witnesses_interrogated INTEGER,
            PRIMARY KEY (player_id, case_id, slot)
        )
    """)
    for migration in (
        "ALTER TABLE saves ADD COLUMN save_revision INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE saves ADD COLUMN evidence_count INTEGER",
        "ALTER TABLE saves ADD COLUMN current_location TEXT",
        "ALTER TABLE saves ADD COLUMN witnesses_interrogated INTEGER",
    ):
        try:
            conn.execute(migration)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    logger.info("Database initialized: %s", _DB_PATH)


def _save_metadata_from_state(state: PlayerState) -> tuple[int, str, int]:
    """Lightweight metadata for list endpoints (avoids full JSON parse)."""
    evidence_count = len(state.discovered_evidence)
    witnesses_interrogated = len(
        [ws for ws in state.witness_states.values() if ws.conversation_history]
    )
    return evidence_count, state.current_location, witnesses_interrogated


def _validate_identifier(value: str, name: str) -> None:
    """Validate case_id/player_id to prevent injection."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", value):
        raise ValueError(f"Invalid {name} format: {value}")


def _normalize_slot(slot: str) -> str:
    """Normalize slot name. 'default' maps to 'autosave'."""
    return "autosave" if slot == "default" else slot


# ============================================================================
# Core CRUD functions (same signatures as before)
# ============================================================================


def save_player_state(
    case_id: str,
    player_id: str,
    state: PlayerState,
    slot: str = "default",
    *,
    _retry: bool = True,
) -> bool:
    """Save player state to specific slot. Raises on failure."""
    if slot not in VALID_SLOTS:
        raise ValueError(f"Invalid slot: {slot}. Must be one of {VALID_SLOTS}")

    _validate_identifier(case_id, "case_id")
    _validate_identifier(player_id, "player_id")
    slot = _normalize_slot(slot)

    try:
        state.last_saved = datetime.now(UTC)
        state.updated_at = datetime.now(UTC)
        now = datetime.now(UTC).isoformat()

        with _db_lock:
            conn = _get_conn()
            row = conn.execute(
                """
                SELECT save_revision FROM saves
                WHERE player_id = ? AND case_id = ? AND slot = ?
                """,
                (player_id, case_id, slot),
            ).fetchone()

            expected_revision = state.save_revision
            if row is not None and int(row[0]) != expected_revision:
                raise StaleStateError(expected_revision, int(row[0]))

            new_revision = (int(row[0]) if row is not None else 0) + 1
            state.save_revision = new_revision
            state_json = json.dumps(state.model_dump(mode="json"), default=str)
            evidence_count, location, witnesses_interrogated = _save_metadata_from_state(state)

            if row is None:
                conn.execute(
                    """
                    INSERT INTO saves (
                        player_id, case_id, slot, state, updated_at,
                        save_revision, evidence_count, current_location, witnesses_interrogated
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        player_id,
                        case_id,
                        slot,
                        state_json,
                        now,
                        new_revision,
                        evidence_count,
                        location,
                        witnesses_interrogated,
                    ),
                )
            else:
                updated = conn.execute(
                    """
                    UPDATE saves
                    SET state = ?, updated_at = ?, save_revision = ?,
                        evidence_count = ?, current_location = ?, witnesses_interrogated = ?
                    WHERE player_id = ? AND case_id = ? AND slot = ? AND save_revision = ?
                    """,
                    (
                        state_json,
                        now,
                        new_revision,
                        evidence_count,
                        location,
                        witnesses_interrogated,
                        player_id,
                        case_id,
                        slot,
                        expected_revision,
                    ),
                )
                if (updated.rowcount or 0) == 0:
                    raise StaleStateError(expected_revision, new_revision)

            conn.commit()
        return True

    except StaleStateError:
        if _retry:
            with _db_lock:
                conn = _get_conn()
                row = conn.execute(
                    """
                    SELECT save_revision FROM saves
                    WHERE player_id = ? AND case_id = ? AND slot = ?
                    """,
                    (player_id, case_id, slot),
                ).fetchone()
            if row is not None:
                state.save_revision = int(row[0])
                return save_player_state(
                    case_id, player_id, state, slot, _retry=False
                )
        raise
    except Exception as e:
        logger.error(f"Save failed: {e}")
        raise


def load_player_state(
    case_id: str,
    player_id: str,
    slot: str = "default",
) -> PlayerState | None:
    """Load player state from specific slot."""
    if slot not in VALID_SLOTS:
        raise ValueError(f"Invalid slot: {slot}. Must be one of {VALID_SLOTS}")

    _validate_identifier(case_id, "case_id")
    _validate_identifier(player_id, "player_id")
    slot = _normalize_slot(slot)

    try:
        with _db_lock:
            conn = _get_conn()
            row = conn.execute(
                """
                SELECT state, save_revision FROM saves
                WHERE player_id = ? AND case_id = ? AND slot = ?
                """,
                (player_id, case_id, slot),
            ).fetchone()

        if row is None:
            return None

        state_json = row[0]
        if not state_json:
            raise CorruptSaveError(f"Corrupted save in slot {slot}: state column is empty")

        data: dict[str, Any] = json.loads(state_json)
        if row[1] is not None:
            data["save_revision"] = int(row[1])

        if not data.get("state_id") or not data.get("case_id"):
            raise CorruptSaveError(f"Corrupted save in slot {slot}: missing required fields")

        return PlayerState(**data)

    except json.JSONDecodeError as e:
        logger.error(f"Corrupt JSON in slot {slot}: {e}")
        raise CorruptSaveError(f"Corrupted save in slot {slot}: invalid JSON") from e
    except ValidationError as e:
        logger.error(f"Invalid state in slot {slot}: {e}")
        raise CorruptSaveError(f"Corrupted save in slot {slot}: invalid state data") from e
    except (CorruptSaveError, ValueError):
        raise
    except sqlite3.Error as e:
        logger.error(f"Load failed (database): {e}")
        return None


def delete_player_save(
    case_id: str,
    player_id: str,
    slot: str,
) -> bool:
    """Delete specific save slot."""
    if slot not in VALID_SLOTS:
        return False

    slot = _normalize_slot(slot)

    try:
        conn = _get_conn()
        cursor = conn.execute(
            "DELETE FROM saves WHERE player_id = ? AND case_id = ? AND slot = ?",
            (player_id, case_id, slot),
        )
        conn.commit()
        return (cursor.rowcount or 0) > 0
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return False


def get_save_metadata(
    case_id: str,
    player_id: str,
    slot: str,
) -> dict[str, Any] | None:
    """Get metadata for a save slot."""
    slot_normalized = _normalize_slot(slot)

    try:
        conn = _get_conn()
        row = conn.execute(
            """
            SELECT state, updated_at, evidence_count, current_location, witnesses_interrogated
            FROM saves WHERE player_id = ? AND case_id = ? AND slot = ?
            """,
            (player_id, case_id, slot_normalized),
        ).fetchone()

        if row is None:
            return None

        state_json, updated_at, ev_col, loc_col, wit_col = row
        if ev_col is not None and loc_col is not None:
            evidence_count = int(ev_col)
            location = str(loc_col)
            witnesses_interrogated = int(wit_col or 0)
            data: dict[str, Any] = {"case_id": case_id, "version": "1.0.0"}
        else:
            data = json.loads(state_json)
            evidence_count = len(data.get("discovered_evidence", []))
            location = data.get("current_location", "unknown")
            witness_states = data.get("witness_states", {})
            witnesses_interrogated = len(
                [ws for ws in witness_states.values() if ws.get("conversation_history")]
            )

        total_evidence = 15
        progress_percent = min(100, int((evidence_count / total_evidence) * 100))

        return {
            "slot": slot,
            "case_id": data.get("case_id", case_id),
            "timestamp": data.get("last_saved") or updated_at,
            "location": location,
            "evidence_count": evidence_count,
            "witnesses_interrogated": witnesses_interrogated,
            "progress_percent": progress_percent,
            "version": data.get("version", "1.0.0"),
        }

    except Exception as e:
        logger.warning(f"Failed to read metadata for slot {slot}: {e}")
        return None


def list_player_saves(
    case_id: str,
    player_id: str,
) -> list[dict[str, Any]]:
    """List all save slots with metadata for a player."""
    saves: list[dict[str, Any]] = []
    for slot in ["slot_1", "slot_2", "slot_3", "autosave"]:
        metadata = get_save_metadata(case_id, player_id, slot)
        if metadata:
            saves.append(metadata)
    return saves


# ============================================================================
# Legacy functions (kept for backward compat)
# ============================================================================


def save_state(state: PlayerState, player_id: str) -> bool:
    """Legacy save — delegates to save_player_state with autosave slot. Raises on failure."""
    return save_player_state(state.case_id, player_id, state, "autosave")


def load_state(case_id: str, player_id: str) -> PlayerState | None:
    """Legacy load — delegates to load_player_state with autosave slot."""
    return load_player_state(case_id, player_id, "autosave")


def delete_state(case_id: str, player_id: str) -> bool:
    """Legacy delete — delegates to delete_player_save with autosave slot."""
    return delete_player_save(case_id, player_id, "autosave")


def list_saves(player_id: str | None = None) -> list[str]:
    """Legacy list — returns empty (not used in new system)."""
    return []


def migrate_old_save(
    case_id: str,
    player_id: str,
) -> bool:
    """No-op migration."""
    return False
