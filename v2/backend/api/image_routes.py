"""V4 image generation REST API."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from image.config import IMAGE_CONTENT_MODE, SILICONFLOW_API_KEY
from image.orchestrator import ImageEngineError, generate_character_image
from services.image_job_service import (
    MAX_ATTEMPTS,
    get_job,
    list_jobs_for_character,
    push_image_job_update,
    run_chat_image_job,
)

router = APIRouter(prefix="/api/v4/image", tags=["image"])


class GenerateRequest(BaseModel):
    character_id: str
    scene: str = "bedroom"
    style: str = ""
    outfit: str = ""
    pose: str = ""
    emotion: str = ""
    exposure: str = "full_clothed"
    extra: str = ""
    multi_characters: list[str] = Field(default_factory=list)
    priority: str = "quality"


@router.get("/status")
def image_status():
    return {
        "enabled": bool(SILICONFLOW_API_KEY),
        "provider": "siliconflow",
        "content_mode": IMAGE_CONTENT_MODE,
    }


@router.post("/generate")
async def generate(req: GenerateRequest):
    try:
        result = await generate_character_image(
            req.character_id,
            scene=req.scene,
            style=req.style,
            outfit=req.outfit,
            pose=req.pose,
            emotion=req.emotion,
            exposure=req.exposure,
            extra=req.extra,
            multi_characters=req.multi_characters or None,
            priority=req.priority,
        )
        return {"ok": True, **result}
    except ImageEngineError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/jobs")
def list_jobs(character_id: str, limit: int = 20):
    return {
        "character_id": character_id,
        "items": list_jobs_for_character(character_id, limit=limit),
    }


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str, room: str = ""):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "failed":
        raise HTTPException(status_code=400, detail="only failed jobs can be retried")
    if int(job.get("attempt_count") or 0) >= MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="retry limit reached")

    target_room = room or f"private:{job['character_id']}"
    asyncio.create_task(
        run_chat_image_job(
            target_room,
            job_id,
            character_id=job["character_id"],
            scene=job.get("scene") or "bedroom",
            style=job.get("style") or "",
            outfit="",
            pose="",
            emotion="",
            exposure=job.get("meta", {}).get("exposure", "full_clothed"),
            extra="",
            trigger=job.get("trigger_type") or "manual_retry",
        )
    )
    refreshed = get_job(job_id)
    if refreshed:
        await push_image_job_update(target_room, refreshed)
    return {"ok": True, "job_id": job_id, "status": "retrying"}
