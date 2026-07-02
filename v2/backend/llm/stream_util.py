"""Shared helpers for LLM streaming with timeout."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger("companion.llm")


async def iter_stream_with_timeout(
    stream: Any,
    *,
    total_timeout: float,
    idle_timeout: float = 60.0,
) -> AsyncIterator[str]:
    """Yield text deltas from an OpenAI-style stream; stop on total or idle timeout."""
    started = asyncio.get_running_loop().time()
    iterator = stream.__aiter__()

    while True:
        elapsed = asyncio.get_running_loop().time() - started
        if elapsed >= total_timeout:
            logger.warning("LLM stream total timeout (%.0fs)", total_timeout)
            break
        remaining = min(idle_timeout, total_timeout - elapsed)
        try:
            chunk = await asyncio.wait_for(iterator.__anext__(), timeout=remaining)
        except StopAsyncIteration:
            break
        except asyncio.TimeoutError:
            logger.warning("LLM stream idle timeout (%.0fs)", idle_timeout)
            break

        if not getattr(chunk, "choices", None):
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
