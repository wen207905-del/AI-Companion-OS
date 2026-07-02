"""Generic OpenAI-compatible API client (DeepSeek, Qwen, etc.)."""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from config import LLM_TIMEOUT
from llm.stream_util import iter_stream_with_timeout

logger = logging.getLogger("companion.openai_compat")

_clients: dict[tuple[str, str], AsyncOpenAI] = {}


def get_client(api_key: str, base_url: str) -> AsyncOpenAI:
    key = (base_url.rstrip("/"), api_key)
    if key not in _clients:
        _clients[key] = AsyncOpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
    return _clients[key]


async def chat_completion(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: float | None = None,
    **kwargs: Any,
) -> str:
    client = get_client(api_key, base_url)
    _timeout = timeout if timeout is not None else LLM_TIMEOUT
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            ),
            timeout=_timeout,
        )
        return response.choices[0].message.content or ""
    except asyncio.TimeoutError:
        logger.warning(
            "OpenAI-compat timeout (%.0fs) model=%s prompt_len=%d",
            _timeout, model, sum(len(m.get("content", "")) for m in messages),
        )
        return ""


async def chat_completion_stream(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: float | None = None,
    **kwargs: Any,
) -> AsyncIterator[str]:
    client = get_client(api_key, base_url)
    _timeout = timeout if timeout is not None else LLM_TIMEOUT
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        async for delta in iter_stream_with_timeout(stream, total_timeout=_timeout):
            yield delta
    except Exception as exc:
        logger.warning("OpenAI-compat stream error model=%s: %s", model, exc)
