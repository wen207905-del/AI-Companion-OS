"""Quality-first model routing for SiliconFlow."""

from __future__ import annotations

from dataclasses import dataclass

from image.config import (
    MODEL_FAST,
    MODEL_MULTI,
    MODEL_PORTRAIT_REF,
    MODEL_PORTRAIT_T2I,
    MODEL_ULTRA,
)


@dataclass
class RouteDecision:
    model: str
    mode: str  # text2img | img2img | multi_ref
    width: int
    height: int
    reason: str
    use_reference: bool = False
    reference_paths: list[str] | None = None


def route_request(
    *,
    character_id: str,
    style: str = "cinematic_portrait",
    exposure: str = "full_clothed",
    multi_characters: list[str] | None = None,
    reference_path: str | None = None,
    extra_refs: list[str] | None = None,
    priority: str = "quality",
) -> RouteDecision:
    """Pick the best SiliconFlow model for the scene."""
    refs: list[str] = []
    if reference_path:
        refs.append(reference_path)
    if extra_refs:
        refs.extend(extra_refs)

    multi = multi_characters or []
    is_multi = len(multi) > 1
    is_full_body = style in ("full_body", "candid") or exposure in ("nude", "towel", "partial")
    is_portrait = style in ("selfie", "portrait", "cinematic_portrait")

    if priority == "fast":
        return RouteDecision(
            model=MODEL_FAST,
            mode="text2img",
            width=768,
            height=1024,
            reason="fast priority (Qwen-Image)",
            use_reference=False,
        )

    if is_multi and len(refs) >= 1:
        return RouteDecision(
            model=MODEL_MULTI,
            mode="multi_ref",
            width=1140,
            height=1472,
            reason="multi-character scene (Qwen-Image-Edit + refs)",
            use_reference=True,
            reference_paths=refs[:3],
        )

    if refs and is_portrait:
        return RouteDecision(
            model=MODEL_PORTRAIT_REF,
            mode="img2img",
            width=768,
            height=1024,
            reason="portrait with face reference (Qwen-Image-Edit)",
            use_reference=True,
            reference_paths=[refs[0]],
        )

    if is_full_body and refs:
        return RouteDecision(
            model=MODEL_ULTRA,
            mode="img2img",
            width=960,
            height=1280,
            reason="full body scene with reference (Qwen-Image-Edit)",
            use_reference=True,
            reference_paths=[refs[0]],
        )

    if refs:
        return RouteDecision(
            model=MODEL_PORTRAIT_REF,
            mode="img2img",
            width=768,
            height=1024,
            reason="single character with reference (Qwen-Image-Edit)",
            use_reference=True,
            reference_paths=[refs[0]],
        )

    if is_multi:
        return RouteDecision(
            model=MODEL_PORTRAIT_T2I,
            mode="text2img",
            width=1140,
            height=1472,
            reason="multi-character text2img (Qwen-Image)",
            use_reference=False,
        )

    return RouteDecision(
        model=MODEL_PORTRAIT_T2I,
        mode="text2img",
        width=1056,
        height=1584,
        reason="high quality text2img (Qwen-Image)",
        use_reference=False,
    )
