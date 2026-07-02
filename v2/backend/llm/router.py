"""Route LLM requests to DeepSeek or Qwen."""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    LLM_AUX_MODEL,
    LLM_AUX_PROVIDER,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_MODEL,
)
from llm.openai_compat import chat_completion as openai_chat
from llm.openai_compat import chat_completion_stream as openai_chat_stream

logger = logging.getLogger("companion.llm")

Channel = Literal["main", "aux"]
SUPPORTED_PROVIDERS = ("deepseek", "qwen")


@dataclass
class LlmChoice:
    provider: str
    model: str | None = None


def _normalize_provider(provider: str) -> str:
    """Legacy ollama prefs fall back to configured main provider."""
    p = (provider or "").lower()
    if p == "ollama" or p not in SUPPORTED_PROVIDERS:
        return LLM_PROVIDER if LLM_PROVIDER in SUPPORTED_PROVIDERS else "deepseek"
    return p


def _normalize_base_url(url: str) -> str:
    url = url.rstrip("/")
    if not url.endswith("/v1"):
        url = f"{url}/v1"
    return url


def _provider_config(provider: str) -> dict[str, Any]:
    provider = _normalize_provider(provider)
    if provider == "deepseek":
        return {
            "id": "deepseek",
            "name": "DeepSeek",
            "base_url": DEEPSEEK_BASE_URL,
            "requires_key": True,
            "available": bool(DEEPSEEK_API_KEY),
            "default_model": DEEPSEEK_MODEL,
            "models": [{"id": DEEPSEEK_MODEL, "name": "DeepSeek Chat"}],
        }
    if provider == "qwen":
        return {
            "id": "qwen",
            "name": "Qwen (阿里云)",
            "base_url": _normalize_base_url(QWEN_BASE_URL),
            "requires_key": True,
            "available": bool(QWEN_API_KEY),
            "default_model": QWEN_MODEL,
            "models": [{"id": QWEN_MODEL, "name": QWEN_MODEL}],
        }
    raise ValueError(f"Unknown LLM provider: {provider}")


def list_providers() -> list[dict[str, Any]]:
    result = []
    for pid in SUPPORTED_PROVIDERS:
        cfg = _provider_config(pid)
        result.append({
            "id": cfg["id"],
            "name": cfg["name"],
            "available": cfg["available"],
            "default_model": cfg["default_model"],
            "models": cfg["models"],
        })
    return result


def default_choice(channel: Channel = "main") -> LlmChoice:
    if channel == "aux":
        provider = _normalize_provider(LLM_AUX_PROVIDER)
        model = LLM_AUX_MODEL
    else:
        provider = _normalize_provider(LLM_PROVIDER)
        model = LLM_MODEL
    cfg = _provider_config(provider)
    return LlmChoice(provider=provider, model=model or cfg["default_model"])


def choice_from_dict(data: dict[str, Any] | None, channel: Channel = "main") -> LlmChoice:
    if not data:
        return default_choice(channel)
    provider = _normalize_provider(data.get("provider") or "")
    if not provider:
        return default_choice(channel)
    cfg = _provider_config(provider)
    model = data.get("model") or cfg["default_model"]
    if provider == "deepseek" and model and ":" in model and "deepseek" not in model.lower():
        model = cfg["default_model"]
    return LlmChoice(provider=provider, model=model)


def is_choice_available(choice: LlmChoice) -> bool:
    try:
        cfg = _provider_config(choice.provider)
    except ValueError:
        return False
    if not cfg["available"]:
        return False
    return True


def get_status() -> dict[str, Any]:
    main = default_choice("main")
    aux = default_choice("aux")
    return {
        "main": {
            "provider": main.provider,
            "model": main.model,
            "available": is_choice_available(main),
        },
        "aux": {
            "provider": aux.provider,
            "model": aux.model,
            "available": is_choice_available(aux),
        },
        "providers": list_providers(),
    }


async def chat_completion(
    messages: list[dict[str, str]],
    *,
    choice: LlmChoice | dict[str, Any] | None = None,
    channel: Channel = "main",
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> str:
    if isinstance(choice, dict):
        resolved = choice_from_dict(choice, channel)
    elif isinstance(choice, LlmChoice):
        resolved = choice
    else:
        resolved = default_choice(channel)

    cfg = _provider_config(resolved.provider)
    model = resolved.model or cfg["default_model"]
    temp = LLM_TEMPERATURE if temperature is None else temperature
    tokens = LLM_MAX_TOKENS if max_tokens is None else max_tokens

    api_key = DEEPSEEK_API_KEY if resolved.provider == "deepseek" else QWEN_API_KEY
    if not api_key:
        raise RuntimeError(
            f"{cfg['name']} API key required. Set the key in .env."
        )

    logger.debug("%s model=%s tokens=%s", resolved.provider, model, tokens)
    return await openai_chat(
        messages,
        api_key=api_key,
        base_url=cfg["base_url"],
        model=model,
        temperature=temp,
        max_tokens=tokens,
        timeout=timeout,
        **kwargs,
    )


async def chat_completion_stream(
    messages: list[dict[str, str]],
    *,
    choice: LlmChoice | dict[str, Any] | None = None,
    channel: Channel = "main",
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> AsyncIterator[str]:
    if isinstance(choice, dict):
        resolved = choice_from_dict(choice, channel)
    elif isinstance(choice, LlmChoice):
        resolved = choice
    else:
        resolved = default_choice(channel)

    cfg = _provider_config(resolved.provider)
    model = resolved.model or cfg["default_model"]
    temp = LLM_TEMPERATURE if temperature is None else temperature
    tokens = LLM_MAX_TOKENS if max_tokens is None else max_tokens

    api_key = DEEPSEEK_API_KEY if resolved.provider == "deepseek" else QWEN_API_KEY
    if not api_key:
        raise RuntimeError(f"{cfg['name']} API key required. Set the key in .env.")

    async for delta in openai_chat_stream(
        messages,
        api_key=api_key,
        base_url=cfg["base_url"],
        model=model,
        temperature=temp,
        max_tokens=tokens,
        timeout=timeout,
        **kwargs,
    ):
        yield delta


def is_available(channel: Channel = "main") -> bool:
    return is_choice_available(default_choice(channel))
