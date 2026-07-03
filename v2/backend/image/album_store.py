"""Persist generated images locally (SiliconFlow URLs expire ~1h)."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import httpx

from config import get_db
from image.config import IMAGE_OUTPUT_DIR


def _albums_dir() -> Path:
    path = Path(IMAGE_OUTPUT_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def download_and_save(image_url: str, character_id: str, job_id: str) -> str:
    """Download remote image and return local relative URL."""
    char_dir = _albums_dir() / character_id
    char_dir.mkdir(parents=True, exist_ok=True)

    ext = ".png"
    if ".jpg" in image_url or ".jpeg" in image_url:
        ext = ".jpg"
    elif ".webp" in image_url:
        ext = ".webp"

    filename = f"{job_id}{ext}"
    dest = char_dir / filename

    if image_url.startswith("data:"):
        import base64

        b64 = image_url.split(",", 1)[-1]
        dest.write_bytes(base64.b64decode(b64))
    else:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)

    return f"/static/albums/{character_id}/{filename}"


def insert_album(
    *,
    job_id: str,
    character_id: str,
    local_url: str,
    prompt: str,
    model: str,
    scene: str,
    style: str,
    meta: dict | None = None,
    status: str = "completed",
) -> dict:
    conn = get_db()
    now = time.time()
    conn.execute(
        """
        INSERT INTO image_albums
            (job_id, character_id, url, prompt, model, scene, style, status, meta, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            character_id,
            local_url,
            prompt,
            model,
            scene,
            style,
            status,
            json.dumps(meta or {}, ensure_ascii=False),
            now,
        ),
    )
    conn.commit()
    return {
        "job_id": job_id,
        "character_id": character_id,
        "url": local_url,
        "status": status,
        "model": model,
        "scene": scene,
        "style": style,
        "created_at": now,
    }


def update_job_status(
    job_id: str,
    status: str,
    *,
    error: str = "",
    local_url: str = "",
    meta_patch: dict | None = None,
) -> None:
    conn = get_db()
    row = conn.execute(
        "SELECT meta FROM image_albums WHERE job_id = ?", (job_id,)
    ).fetchone()
    meta = {}
    if row and row["meta"]:
        try:
            meta = json.loads(row["meta"])
        except json.JSONDecodeError:
            meta = {}
    if error:
        meta["error"] = error
    if meta_patch:
        meta.update(meta_patch)
    conn.execute(
        """
        UPDATE image_albums
        SET status = ?, url = COALESCE(NULLIF(?, ''), url), meta = ?
        WHERE job_id = ?
        """,
        (status, local_url, json.dumps(meta, ensure_ascii=False), job_id),
    )
    conn.commit()


def create_pending_job(
    *,
    character_id: str,
    prompt: str,
    model: str,
    scene: str,
    style: str,
    meta: dict | None = None,
) -> str:
    job_id = str(uuid.uuid4())[:12]
    conn = get_db()
    conn.execute(
        """
        INSERT INTO image_albums
            (job_id, character_id, url, prompt, model, scene, style, status, meta, created_at)
        VALUES (?, ?, '', ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            job_id,
            character_id,
            prompt,
            model,
            scene,
            style,
            json.dumps(meta or {}, ensure_ascii=False),
            time.time(),
        ),
    )
    conn.commit()
    return job_id


def get_job(job_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM image_albums WHERE job_id = ?", (job_id,)
    ).fetchone()
    if not row:
        return None
    meta = {}
    if row["meta"]:
        try:
            meta = json.loads(row["meta"])
        except json.JSONDecodeError:
            pass
    return {
        "job_id": row["job_id"],
        "character_id": row["character_id"],
        "url": row["url"],
        "prompt": row["prompt"],
        "model": row["model"],
        "scene": row["scene"],
        "style": row["style"],
        "status": row["status"],
        "meta": meta,
        "created_at": row["created_at"],
    }


def list_album(character_id: str, limit: int = 30) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """
        SELECT job_id, character_id, url, model, scene, style, status, created_at
        FROM image_albums
        WHERE character_id = ? AND status = 'completed'
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (character_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]
