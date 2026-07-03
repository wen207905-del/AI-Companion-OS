"""SiliconFlow image generation client — model-specific payloads."""

from __future__ import annotations

import base64
import logging
from math import gcd
from pathlib import Path
from typing import Any

import httpx

from image.config import (
    IMAGE_CONTENT_MODE,
    IMAGE_JOB_TIMEOUT,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
)
from image.router import RouteDecision

logger = logging.getLogger(__name__)

SCHNELL_SIZES = frozenset(
    {"1024x1024", "512x1024", "768x512", "768x1024", "1024x576", "576x1024"}
)
QWEN_SIZES = frozenset(
    {
        "1328x1328",
        "1664x928",
        "928x1664",
        "1472x1140",
        "1140x1472",
        "1584x1056",
        "1056x1584",
    }
)


class SiliconFlowError(Exception):
    pass


def _encode_image(path: str) -> str:
    data = Path(path).read_bytes()
    ext = Path(path).suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext or 'png'}"
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _headers() -> dict[str, str]:
    if not SILICONFLOW_API_KEY:
        raise SiliconFlowError("SILICONFLOW_API_KEY not configured")
    return {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }


def _aspect_ratio(width: int, height: int) -> str:
    g = gcd(width, height)
    return f"{width // g}:{height // g}"


def _snap_size(width: int, height: int, allowed: frozenset[str], fallback: str) -> str:
    candidate = f"{width}x{height}"
    return candidate if candidate in allowed else fallback


def _safety_tolerance() -> int:
    return 6 if IMAGE_CONTENT_MODE == "unrestricted" else 2


def _build_payload(
    prompt: str,
    negative: str,
    route: RouteDecision,
    *,
    seed: int | None = None,
) -> dict[str, Any]:
    model = route.model

    if "Kontext" in model and "dev" not in model:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": _aspect_ratio(route.width, route.height),
            "output_format": "png",
            "prompt_upsampling": True,
            "safety_tolerance": _safety_tolerance(),
        }
        if seed is not None:
            payload["seed"] = seed
        if route.use_reference and route.reference_paths:
            payload["input_image"] = _encode_image(route.reference_paths[0])
        return payload

    if "Qwen" in model:
        size = _snap_size(route.width, route.height, QWEN_SIZES, "1140x1472")
        payload = {
            "model": model,
            "prompt": prompt,
            "image_size": size,
            "num_inference_steps": 30,
            "cfg": 4.0,
        }
        if negative:
            payload["negative_prompt"] = negative
        if seed is not None:
            payload["seed"] = seed
        if route.use_reference and route.reference_paths:
            payload["image"] = _encode_image(route.reference_paths[0])
        return payload

    if "Ultra" in model:
        payload = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": _aspect_ratio(route.width, route.height),
            "output_format": "png",
            "raw": True,
            "safety_tolerance": _safety_tolerance(),
        }
        if negative:
            payload["negative_prompt"] = negative
        if seed is not None:
            payload["seed"] = seed
        if route.use_reference and route.reference_paths:
            payload["image_prompt"] = _encode_image(route.reference_paths[0])
            payload["image_prompt_strength"] = 1
        return payload

    if "schnell" in model:
        size = _snap_size(route.width, route.height, SCHNELL_SIZES, "768x1024")
        payload = {
            "model": model,
            "prompt": prompt,
            "image_size": size,
        }
        if seed is not None:
            payload["seed"] = seed
        return payload

    payload = {
        "model": model,
        "prompt": prompt,
        "image_size": f"{route.width}x{route.height}",
    }
    if negative:
        payload["negative_prompt"] = negative
    if seed is not None:
        payload["seed"] = seed
    return payload


async def generate_image(
    prompt: str,
    negative: str,
    route: RouteDecision,
    *,
    seed: int | None = None,
) -> dict[str, Any]:
    """Call SiliconFlow /images/generations and return result metadata."""
    url = f"{SILICONFLOW_BASE_URL.rstrip('/')}/images/generations"
    payload = _build_payload(prompt, negative, route, seed=seed)

    async with httpx.AsyncClient(timeout=IMAGE_JOB_TIMEOUT) as client:
        resp = await client.post(url, headers=_headers(), json=payload)

    if resp.status_code >= 400:
        detail = resp.text[:800]
        logger.error("SiliconFlow error %s model=%s: %s", resp.status_code, route.model, detail)
        raise SiliconFlowError(f"SiliconFlow API {resp.status_code}: {detail}")

    data = resp.json()
    images = data.get("data") or data.get("images") or []
    if not images:
        raise SiliconFlowError("SiliconFlow returned no images")

    first = images[0]
    image_url = first.get("url") or first.get("b64_json")
    if not image_url:
        raise SiliconFlowError("SiliconFlow image entry missing url")

    return {
        "image_url": image_url,
        "model": route.model,
        "mode": route.mode,
        "width": route.width,
        "height": route.height,
        "reason": route.reason,
        "raw": data,
    }
