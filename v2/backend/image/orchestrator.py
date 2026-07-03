"""Image generation orchestrator."""

from __future__ import annotations

import logging

from image.album_store import (
    create_pending_job,
    download_and_save,
    get_job,
    update_job_status,
)
from image.config import IMAGE_CONTENT_MODE, SILICONFLOW_API_KEY
from image.identity_loader import load_identity
from image.prompt_composer import compose_prompt
from image.router import route_request
from image.siliconflow import SiliconFlowError, generate_image

logger = logging.getLogger(__name__)


class ImageEngineError(Exception):
    pass


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
) -> dict:
    if not SILICONFLOW_API_KEY:
        raise ImageEngineError("SILICONFLOW_API_KEY not configured — add it to .env")

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

    composed = compose_prompt(
        character_id,
        scene=scene,
        style=style,
        outfit=outfit,
        pose=pose,
        emotion=emotion,
        exposure=exposure if IMAGE_CONTENT_MODE == "unrestricted" else "full_clothed",
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

    job_id = create_pending_job(
        character_id=character_id,
        prompt=composed["prompt"],
        model=route.model,
        scene=scene,
        style=composed["style"],
        meta={
            "route_reason": route.reason,
            "mode": route.mode,
            "exposure": exposure,
            "content_mode": IMAGE_CONTENT_MODE,
        },
    )

    try:
        result = await generate_image(
            composed["prompt"],
            composed["negative_prompt"],
            route,
            seed=composed.get("identity_seed"),
        )
        local_url = await download_and_save(
            result["image_url"], character_id, job_id
        )
        update_job_status(
            job_id,
            "completed",
            local_url=local_url,
            meta_patch={
                "width": result["width"],
                "height": result["height"],
                "route_reason": result["reason"],
                "mode": result["mode"],
            },
        )
        record = get_job(job_id) or {}
        return {
            **record,
            "route": {
                "model": result["model"],
                "reason": result["reason"],
                "mode": result["mode"],
            },
        }
    except (SiliconFlowError, Exception) as exc:
        logger.exception("Image generation failed for %s", character_id)
        update_job_status(job_id, "failed", error=str(exc))
        raise ImageEngineError(str(exc)) from exc
