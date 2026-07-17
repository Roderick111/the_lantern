"""Idempotency records for durable Telegram (and other) mutation retries.

Keyed by (player_id, operation, request_id). Same DB as player saves.
Statuses:
  - in_progress: duplicate returns 409 request_in_progress
  - completed: duplicate returns stored status/body (no re-run)
  - failed_before_mutation: request may retry (re-claim)

Records kept 7 days; cleanup is opportunistic and bounded (no scheduler).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from src.state.persistence import _db_lock, _get_conn

logger = logging.getLogger(__name__)

STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED_BEFORE_MUTATION = "failed_before_mutation"

RETENTION_DAYS = 7
CLEANUP_BATCH_LIMIT = 100

IDEMPOTENCY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS idempotency_records (
    player_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    request_id TEXT NOT NULL,
    status TEXT NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (player_id, operation, request_id)
)
"""


def ensure_idempotency_table() -> None:
    """Create idempotency table if missing (dev/test + init_db path)."""
    with _db_lock:
        conn = _get_conn()
        conn.execute(IDEMPOTENCY_TABLE_SQL)
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_idempotency_updated_at
            ON idempotency_records(updated_at)
            """
        )
        conn.commit()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _cleanup_expired_unlocked(conn: Any) -> int:
    """Delete expired rows, bounded. Caller holds _db_lock."""
    cutoff = (datetime.now(UTC) - timedelta(days=RETENTION_DAYS)).isoformat()
    cur = conn.execute(
        """
        DELETE FROM idempotency_records
        WHERE rowid IN (
            SELECT rowid FROM idempotency_records
            WHERE updated_at < ?
            LIMIT ?
        )
        """,
        (cutoff, CLEANUP_BATCH_LIMIT),
    )
    return cur.rowcount or 0


def claim_or_get(
    player_id: str,
    operation: str,
    request_id: str,
) -> dict[str, Any] | None:
    """Claim in_progress or return completed body.

    Returns:
        Cached response body dict when status is completed.
        None when claim succeeds (caller must run handler).

    Raises:
        HTTPException 409 with code request_in_progress when in_progress.
    """
    now = _now_iso()
    with _db_lock:
        conn = _get_conn()
        _cleanup_expired_unlocked(conn)

        row = conn.execute(
            """
            SELECT status, response_status, response_body
            FROM idempotency_records
            WHERE player_id = ? AND operation = ? AND request_id = ?
            """,
            (player_id, operation, request_id),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO idempotency_records (
                    player_id, operation, request_id, status,
                    response_status, response_body, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, NULL, NULL, ?, ?)
                """,
                (player_id, operation, request_id, STATUS_IN_PROGRESS, now, now),
            )
            conn.commit()
            return None

        status, _response_status, response_body = row[0], row[1], row[2]

        if status == STATUS_COMPLETED and response_body is not None:
            cached: dict[str, Any] = json.loads(response_body)
            return cached

        if status == STATUS_IN_PROGRESS:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "request_in_progress",
                    "message": "Identical request already in progress",
                },
            )

        if status == STATUS_FAILED_BEFORE_MUTATION:
            conn.execute(
                """
                UPDATE idempotency_records
                SET status = ?, response_status = NULL, response_body = NULL,
                    updated_at = ?
                WHERE player_id = ? AND operation = ? AND request_id = ?
                """,
                (STATUS_IN_PROGRESS, now, player_id, operation, request_id),
            )
            conn.commit()
            return None

        # Unknown/corrupt row — treat as retriable re-claim
        logger.warning(
            "Unexpected idempotency status=%s player=%s op=%s; re-claiming",
            status,
            player_id,
            operation,
        )
        conn.execute(
            """
            UPDATE idempotency_records
            SET status = ?, response_status = NULL, response_body = NULL,
                updated_at = ?
            WHERE player_id = ? AND operation = ? AND request_id = ?
            """,
            (STATUS_IN_PROGRESS, now, player_id, operation, request_id),
        )
        conn.commit()
        return None


def complete(
    player_id: str,
    operation: str,
    request_id: str,
    response: BaseModel | dict[str, Any],
    status_code: int = 200,
) -> None:
    """Mark request completed and store response body for replay."""
    if isinstance(response, BaseModel):
        body = response.model_dump(mode="json")
    else:
        body = response
    body_json = json.dumps(body, default=str)
    now = _now_iso()
    with _db_lock:
        conn = _get_conn()
        conn.execute(
            """
            UPDATE idempotency_records
            SET status = ?, response_status = ?, response_body = ?, updated_at = ?
            WHERE player_id = ? AND operation = ? AND request_id = ?
            """,
            (
                STATUS_COMPLETED,
                status_code,
                body_json,
                now,
                player_id,
                operation,
                request_id,
            ),
        )
        conn.commit()


def mark_failed_before_mutation(
    player_id: str,
    operation: str,
    request_id: str,
) -> None:
    """Allow retry after known failure that did not mutate game state."""
    now = _now_iso()
    with _db_lock:
        conn = _get_conn()
        conn.execute(
            """
            UPDATE idempotency_records
            SET status = ?, response_status = NULL, response_body = NULL,
                updated_at = ?
            WHERE player_id = ? AND operation = ? AND request_id = ?
              AND status = ?
            """,
            (
                STATUS_FAILED_BEFORE_MUTATION,
                now,
                player_id,
                operation,
                request_id,
                STATUS_IN_PROGRESS,
            ),
        )
        conn.commit()


class IdempotencyGuard:
    """Small helper for route handlers.

    Usage:
        guard = IdempotencyGuard(player_id, "investigate", body.request_id)
        early = guard.begin()
        if early is not None:
            return ResponseModel.model_validate(early)
        try:
            result = ...
            guard.complete(result)
            return result
        except SomePreMutationError:
            guard.fail_before_mutation()
            raise
    """

    def __init__(
        self,
        player_id: str,
        operation: str,
        request_id: str | None,
    ) -> None:
        self.player_id = player_id
        self.operation = operation
        self.request_id = request_id
        self.active = bool(request_id)

    def begin(self) -> dict[str, Any] | None:
        """Claim or return cached completed body. None means proceed."""
        if not self.active or self.request_id is None:
            return None
        return claim_or_get(self.player_id, self.operation, self.request_id)

    def complete(
        self,
        response: BaseModel | dict[str, Any],
        status_code: int = 200,
    ) -> None:
        if not self.active or self.request_id is None:
            return
        complete(
            self.player_id,
            self.operation,
            self.request_id,
            response,
            status_code,
        )

    def fail_before_mutation(self) -> None:
        if not self.active or self.request_id is None:
            return
        mark_failed_before_mutation(
            self.player_id,
            self.operation,
            self.request_id,
        )
