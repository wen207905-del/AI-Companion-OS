"""V4 image generation REST API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from image.album_store import get_job, list_album
from image.config import IMAGE_CONTENT_MODE, SILICONFLOW_API_KEY
from image.orchestrator import ImageEngineError, generate_character_image

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


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/album/{character_id}")
def album(character_id: str, limit: int = 30):
    return {"character_id": character_id, "items": list_album(character_id, limit)}
