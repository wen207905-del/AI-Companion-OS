"""Image generation orchestrator."""

from __future__ import annotations

import logging

from image.album_store import (
    create_pending_job,
    download_and_save,
    get_job,
    refresh_job_fields,
    update_job_status,
)
from image.config import IMAGE_CONTENT_MODE, SILICONFLOW_API_KEY
from image.exposure_fallback import fallback_exposures, is_content_filter_error
from image.identity_loader import load_identity
from image.prompt_composer import compose_prompt
from image.prompt_loader import get_default_exposure
from image.router import route_request
from image.siliconflow import SiliconFlowError, generate_image

logger = logging.getLogger(__name__)


class ImageEngineError(Exception):
    pass


async def _attempt_generate(
    character_id: str,
    *,
    scene: str,
    style: str,
    outfit: str,
    pose: str,
    emotion: str,
    exposure: str,
    extra: str,
    multi_characters: list[str] | None,
    priority: str,
    job_id: str,
) -> tuple[dict, dict, str]:
    identity = load_identity(character_id)
    ref_path = identity.get("reference_image_path") if identity else None

    extra_refs: list[str] = []
    if multi_characters:
        for cid in multi_characters:
            if cid == character_id:
                continue
            other = load_identity(cid)
            if other and other.get("reference_image_path"):
                extra_refs.append(other["reference_image_path"])

    effective_exposure = (
        exposure if IMAGE_CONTENT_MODE == "unrestricted" else "full_clothed"
    )
    composed = compose_prompt(
        character_id,
        scene=scene,
        style=style,
        outfit=outfit,
        pose=pose,
        emotion=emotion,
        exposure=effective_exposure,
        extra=extra,
        multi_characters=multi_characters,
    )

    route = route_request(
        character_id=character_id,
        style=composed["style"],
        exposure=exposure,
        multi_characters=multi_characters,
        reference_path=ref_path,
        extra_refs=extra_refs,
        priority=priority,
    )

    result = await generate_image(
        composed["prompt"],
        composed["negative_prompt"],
        route,
        seed=composed.get("identity_seed"),
    )
    update_job_status(job_id, "uploading")
    local_url = await download_and_save(result["image_url"], character_id, job_id)
    update_job_status(
        job_id,
        "completed",
        local_url=local_url,
        meta_patch={
            "width": result["width"],
            "height": result["height"],
            "route_reason": result["reason"],
            "mode": result["mode"],
            "exposure_requested": exposure,
        },
    )
    record = get_job(job_id) or {}
    return result, composed, exposure


async def generate_character_image(
    character_id: str,
    *,
    scene: str = "bedroom",
    style: str = "",
    outfit: str = "",
    pose: str = "",
    emotion: str = "",
    exposure: str = "full_clothed",
    extra: str = "",
    multi_characters: list[str] | None = None,
    priority: str = "quality",
    existing_job_id: str | None = None,
) -> dict:
    if not SILICONFLOW_API_KEY:
        raise ImageEngineError("SILICONFLOW_API_KEY not configured — add it to .env")

    if not exposure:
        exposure = get_default_exposure(character_id)
        if IMAGE_CONTENT_MODE != "unrestricted" and exposure == "nude":
            exposure = "full_clothed"

    exposures_to_try = [exposure] + fallback_exposures(exposure)
    last_error: Exception | None = None

    for attempt_exposure in exposures_to_try:
        composed_preview = compose_prompt(
            character_id,
            scene=scene,
            style=style,
            outfit=outfit,
            pose=pose,
            emotion=emotion,
            exposure=attempt_exposure if IMAGE_CONTENT_MODE == "unrestricted" else "full_clothed",
            extra=extra,
            multi_characters=multi_characters,
        )
        route_preview = route_request(
            character_id=character_id,
            style=composed_preview["style"],
            exposure=attempt_exposure,
            multi_characters=multi_characters,
            reference_path=(load_identity(character_id) or {}).get("reference_image_path"),
            priority=priority,
        )
        job_meta = {
            "route_reason": route_preview.reason,
            "mode": route_preview.mode,
            "exposure": attempt_exposure,
            "content_mode": IMAGE_CONTENT_MODE,
        }
        if existing_job_id:
            job_id = existing_job_id
            refresh_job_fields(
                job_id,
                prompt=composed_preview["prompt"],
                model=route_preview.model,
                scene=scene,
                style=composed_preview["style"],
                meta_patch=job_meta,
            )
            update_job_status(job_id, "generating")
        else:
            job_id = create_pending_job(
                character_id=character_id,
                prompt=composed_preview["prompt"],
                model=route_preview.model,
                scene=scene,
                style=composed_preview["style"],
                meta=job_meta,
            )

        try:
            result, composed, used_exposure = await _attempt_generate(
                character_id,
                scene=scene,
                style=style,
                outfit=outfit,
                pose=pose,
                emotion=emotion,
                exposure=attempt_exposure,
                extra=extra,
                multi_characters=multi_characters,
                priority=priority,
                job_id=job_id,
            )
            if used_exposure != exposure:
                logger.info(
                    "Image exposure fallback %s → %s for %s",
                    exposure,
                    used_exposure,
                    character_id,
                )
            record = get_job(job_id) or {}
            _write_visual_memory(character_id, job_id, record, composed, used_exposure)
            return {
                **record,
                "route": {
                    "model": result["model"],
                    "reason": result["reason"],
                    "mode": result["mode"],
                },
                "exposure_used": used_exposure,
                "exposure_requested": exposure,
                "fallback": used_exposure != exposure,
            }
        except SiliconFlowError as exc:
            last_error = exc
            update_job_status(job_id, "failed", error=str(exc))
            if is_content_filter_error(exc) and attempt_exposure != exposures_to_try[-1]:
                logger.warning(
                    "SiliconFlow content filter for %s exposure=%s, trying softer",
                    character_id,
                    attempt_exposure,
                )
                continue
            logger.exception("Image generation failed for %s", character_id)
            raise ImageEngineError(str(exc)) from exc
        except Exception as exc:
            last_error = exc
            update_job_status(job_id, "failed", error=str(exc))
            logger.exception("Image generation failed for %s", character_id)
            raise ImageEngineError(str(exc)) from exc

    raise ImageEngineError(str(last_error or "Image generation failed"))


def _write_visual_memory(
    character_id: str,
    job_id: str,
    record: dict,
    composed: dict,
    exposure: str,
) -> None:
    from app_state import state

    if not state.memory_manager:
        return
    url = record.get("url") or ""
    scene = composed.get("scene") or ""
    text = f"[照片] 场景={scene} 曝光={exposure} 风格={composed.get('style', '')} url={url}"
    state.memory_manager.store(
        character_id,
        text,
        role="character",
        scope="private",
        event_id=job_id,
        intensity=75.0,
        memory_type="visual",
    )
