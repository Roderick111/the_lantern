"""Shared helpers for SSE end-to-end tests.

These helpers are intentionally kept out of conftest.py to avoid
mutating the existing test environment. Import them explicitly.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock


def make_chunk_stream(
    chunks: Iterable[str],
    delay_between: float = 0.0,
    raise_after: int | None = None,
    raise_exc: Exception | None = None,
):
    """Build a mock `get_response_stream` callable.

    Returns a regular function that, when called with any args/kwargs,
    returns an async generator yielding the configured chunks.

    Args:
        chunks: Strings to yield as LLM chunks.
        delay_between: Seconds to sleep before each chunk (used to trigger
            keepalive timeouts when paired with a patched _KEEPALIVE_INTERVAL).
        raise_after: If set, raise `raise_exc` after yielding N chunks.
        raise_exc: Exception to raise mid-stream.
    """
    chunks_list = list(chunks)

    def _factory(*args: Any, **kwargs: Any) -> AsyncIterator[str]:
        async def _gen() -> AsyncIterator[str]:
            for idx, chunk in enumerate(chunks_list):
                if raise_after is not None and idx == raise_after:
                    raise (raise_exc or RuntimeError("mock LLM failure"))
                if delay_between:
                    await asyncio.sleep(delay_between)
                yield chunk

        return _gen()

    return _factory


def build_mock_llm_client(
    chunks: Iterable[str],
    delay_between: float = 0.0,
    raise_after: int | None = None,
    raise_exc: Exception | None = None,
) -> MagicMock:
    """Build a mock LLM client whose `get_response_stream` yields the chunks."""
    client = MagicMock()
    client.get_response_stream = make_chunk_stream(
        chunks,
        delay_between=delay_between,
        raise_after=raise_after,
        raise_exc=raise_exc,
    )
    # Also set non-streaming response in case a route falls through.
    client.get_response = AsyncMock(return_value="".join(chunks))
    return client


@dataclass
class ParsedSSE:
    """Parsed SSE stream output."""

    data_frames: list[dict[str, Any]] = field(default_factory=list)
    keepalive_count: int = 0
    raw_lines: list[str] = field(default_factory=list)

    @property
    def first(self) -> dict[str, Any]:
        return self.data_frames[0]

    @property
    def last(self) -> dict[str, Any]:
        return self.data_frames[-1]

    @property
    def text_frames(self) -> list[dict[str, Any]]:
        return [f for f in self.data_frames if "text" in f]

    @property
    def done_frame(self) -> dict[str, Any] | None:
        for f in self.data_frames:
            if f.get("done") is True:
                return f
        return None

    @property
    def error_frame(self) -> dict[str, Any] | None:
        for f in self.data_frames:
            if "error" in f:
                return f
        return None


def parse_sse_body(body: str) -> ParsedSSE:
    """Parse a raw SSE body into structured frames.

    Recognizes:
      - `data: {json}` lines (parsed as JSON)
      - `:keepalive` comment lines
    """
    parsed = ParsedSSE()
    for raw_line in body.split("\n"):
        line = raw_line.rstrip("\r")
        parsed.raw_lines.append(line)
        if not line:
            continue
        if line.startswith(":"):
            parsed.keepalive_count += 1
            continue
        if line.startswith("data: "):
            payload = line[len("data: ") :]
            try:
                parsed.data_frames.append(json.loads(payload))
            except json.JSONDecodeError:
                # Capture as raw text frame for diagnostics
                parsed.data_frames.append({"_raw": payload})
    return parsed


async def collect_sse_stream(
    client,
    method: str,
    url: str,
    *,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    max_bytes: int = 1_000_000,
) -> ParsedSSE:
    """POST/GET an SSE endpoint and return parsed frames.

    Uses `client.stream(...)` so we read the response progressively.
    Reads to completion — for early-disconnect tests, see
    `iter_sse_stream` below.
    """
    chunks: list[str] = []
    total = 0
    async with client.stream(
        method,
        url,
        json=json_body,
        headers=headers,
    ) as response:
        async for text in response.aiter_text():
            chunks.append(text)
            total += len(text)
            if total >= max_bytes:
                break
    return parse_sse_body("".join(chunks))


async def iter_sse_frames(
    client,
    method: str,
    url: str,
    *,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield parsed SSE data frames one-by-one (skips keepalives).

    Caller can break out early to simulate disconnect.
    """
    buffer = ""
    async with client.stream(
        method,
        url,
        json=json_body,
        headers=headers,
    ) as response:
        async for text in response.aiter_text():
            buffer += text
            # SSE frames are delimited by blank lines (`\n\n`)
            while "\n\n" in buffer:
                frame, buffer = buffer.split("\n\n", 1)
                for raw_line in frame.split("\n"):
                    line = raw_line.rstrip("\r")
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        payload = line[len("data: ") :]
                        try:
                            yield json.loads(payload)
                        except json.JSONDecodeError:
                            yield {"_raw": payload}
