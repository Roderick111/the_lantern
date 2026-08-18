"""Shared SSE stream lifecycle for narrator and witness responses."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.responses import StreamingResponse

from src.api import helpers
from src.api.errors import llm_stream_error_payload, redact_secrets
from src.api.helpers import SSE_HEADERS, SSE_KEEPALIVE
from src.api.llm_client import EmptyLLMResponseError
from src.api.sse_format import sse_json_event, sse_text_event
from src.telemetry.logger import log_event

logger = logging.getLogger(__name__)

NO_TEXT_DEADLINE_SECONDS = 90
VISIBLE_TEXT_DEADLINE_SECONDS = 120

RenderChunk = Callable[[str], str | None]
Finalize = Callable[[str], Awaitable[dict[str, Any]]]
PersistCompletion = Callable[[str, dict[str, Any]], Awaitable[None]]
FailureHook = Callable[[Exception, bool], Awaitable[None] | None]


class StreamDeadlineError(TimeoutError):
    """Raised when provider stream exceeds its request deadline."""


class StreamFinalizationError(RuntimeError):
    """Raised when deterministic post-processing or persistence fails."""


def _as_awaitable(value: Any) -> Awaitable[Any]:
    if inspect.isawaitable(value):
        return value

    async def resolved() -> Any:
        return value

    return resolved()


async def reliable_sse_stream(
    source: AsyncIterator[str],
    *,
    request: Request | None,
    endpoint: str,
    request_id: str | None,
    finalize: Finalize,
    render_chunk: RenderChunk | None = None,
    flush_render: Callable[[], str | None] | None = None,
    persist_completion: PersistCompletion | None = None,
    on_failure: FailureHook | None = None,
) -> AsyncIterator[str]:
    """Consume one provider stream and emit exactly one terminal SSE frame.

    Pending ``__anext__`` tasks survive heartbeat timeouts. They are cancelled
    only on hard deadline, client disconnect, or generator cleanup.
    """

    iterator = source.__aiter__()
    pending: asyncio.Task[str] | None = None
    full_response = ""
    visible_text = False
    terminal_sent = False
    chunk_count = 0
    started = time.monotonic()

    async def disconnected() -> bool:
        if request is None:
            return False
        try:
            return await request.is_disconnected()
        except Exception:
            return False

    async def next_chunk() -> str:
        return await iterator.__anext__()

    def emit_text(raw: str) -> str | None:
        rendered = render_chunk(raw) if render_chunk else raw
        return sse_text_event(rendered) if rendered else None

    try:
        while True:
            if await disconnected():
                return
            if pending is None:
                pending = asyncio.create_task(next_chunk())

            elapsed = time.monotonic() - started
            deadline = VISIBLE_TEXT_DEADLINE_SECONDS if visible_text else NO_TEXT_DEADLINE_SECONDS
            remaining = max(0.01, deadline - elapsed)
            wait_for = min(helpers._KEEPALIVE_INTERVAL, remaining)
            done, _ = await asyncio.wait({pending}, timeout=wait_for)
            if not done:
                if remaining <= helpers._KEEPALIVE_INTERVAL:
                    raise StreamDeadlineError(
                        f"stream exceeded {deadline}s deadline for {endpoint}"
                    )
                yield SSE_KEEPALIVE
                continue

            try:
                chunk = pending.result()
            except StopAsyncIteration:
                pending = None
                break
            finally:
                if pending is not None and pending.done():
                    pending = None

            if chunk.startswith(":"):
                yield chunk
                continue

            full_response += chunk
            chunk_count += 1
            if chunk.strip():
                visible_text = True
            event = emit_text(chunk)
            if event:
                yield event

        if not full_response.strip():
            raise EmptyLLMResponseError(f"Empty response from {endpoint}")

        if flush_render is not None:
            tail = flush_render()
            if tail:
                yield sse_text_event(tail)

        try:
            done_payload = await _as_awaitable(finalize(full_response))
        except Exception as exc:
            raise StreamFinalizationError(str(exc)) from exc
        done_payload = {**done_payload, "done": True}
        if request_id is not None:
            done_payload["request_id"] = request_id
        if persist_completion is not None:
            try:
                await persist_completion(full_response, done_payload)
            except Exception as exc:
                raise StreamFinalizationError(str(exc)) from exc
        try:
            await log_event(
                "llm_stream_terminal",
                "system",
                "system",
                {
                    "endpoint": endpoint,
                    "request_id": request_id,
                    "outcome": "done",
                    "content_chars": len(full_response),
                    "chunk_count": chunk_count,
                },
            )
        except Exception:
            logger.debug("stream success telemetry failed", exc_info=True)
        yield sse_json_event(done_payload)
        terminal_sent = True
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        partial = bool(full_response.strip())
        payload = llm_stream_error_payload(
            exc,
            request_id=request_id,
            partial=partial,
        )
        if isinstance(exc, StreamFinalizationError):
            payload.update(
                code="persist_failed",
                error="Progress may not be saved. Try again.",
                retryable=True,
            )
        if partial and not isinstance(exc, StreamFinalizationError):
            payload["code"] = "partial_stream"
            payload["retryable"] = True
        logger.error(
            "SSE stream failed endpoint=%s request_id=%s partial=%s error=%s",
            endpoint,
            request_id,
            partial,
            redact_secrets(str(exc)),
        )
        try:
            await log_event(
                "llm_stream_terminal",
                "system",
                "system",
                {
                    "endpoint": endpoint,
                    "request_id": request_id,
                    "outcome": "error",
                    "code": payload.get("code"),
                    "partial": partial,
                    "content_chars": len(full_response),
                    "chunk_count": chunk_count,
                },
            )
        except Exception:
            logger.debug("stream failure telemetry failed", exc_info=True)
        if on_failure is not None:
            try:
                result = on_failure(exc, partial)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.error("stream failure hook failed endpoint=%s", endpoint, exc_info=True)
        yield sse_json_event(payload)
        terminal_sent = True
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        close = getattr(iterator, "aclose", None)
        if close is not None:
            try:
                await close()
            except Exception:
                logger.debug("provider stream cleanup failed", exc_info=True)
        if not terminal_sent and full_response.strip() and not await disconnected():
            logger.warning("SSE generator closed before terminal endpoint=%s", endpoint)


def streaming_response(generator: AsyncIterator[str]) -> StreamingResponse:
    """Create compatible StreamingResponse with standard no-buffer headers."""
    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


def replay_cached_stream(cached: dict[str, Any]) -> StreamingResponse:
    """Replay completed stream without rerunning LLM or mutating state."""

    async def generator() -> AsyncIterator[str]:
        text = cached.get("text", "")
        if text:
            yield sse_text_event(text)
        done_payload = cached.get("done_payload")
        if isinstance(done_payload, dict):
            yield sse_json_event(done_payload)

    return streaming_response(generator())
