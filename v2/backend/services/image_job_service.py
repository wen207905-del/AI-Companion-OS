"""V4.1 image job state machine — queued → generating → completed/failed."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
import uuid
from typing import Any

from api.ws_hub import hub
from app_state import state
from engine.world_clock import now as world_now
from image.album_store import update_job_status
from image.config import SILICONFLOW_API_KEY
from image.orchestrator import ImageEngineError, generate_character_image
from services.emotion_tick import commit_emotion_delta, push_emotion_update

logger = logging.getLogger(__name__)

WAIT_HINT_SECONDS = 20
ATTEMPT_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 2

STATUS_QUEUED = "queued"
STATUS_GENERATING = "generating"
STATUS_UPLOADING = "uploading"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_RETRYING = "retrying"

_LEGACY_STATUS = {
    "pending": STATUS_QUEUED,
    "completed": STATUS_COMPLETED,
    "failed": STATUS_FAILED,
}

_IMAGE_JOB_COLUMNS = (
    ("updated_at", "REAL"),
    ("progress_text", "TEXT DEFAULT ''"),
    ("trigger_type", "TEXT DEFAULT ''"),
    ("attempt_count", "INTEGER DEFAULT 0"),
    ("error_message", "TEXT DEFAULT ''"),
)


def ensure_image_job_schema(db: sqlite3.Connection) -> None:
    """Add V4.1 image job columns if missing."""
    cols = {row[1] for row in db.execute("PRAGMA table_info(image_albums)").fetchall()}
    for name, typedef in _IMAGE_JOB_COLUMNS:
        if name not in cols:
            db.execute(f"ALTER TABLE image_albums ADD COLUMN {name} {typedef}")
            cols.add(name)
    if "updated_at" in cols:
        db.execute(
            "UPDATE image_albums SET updated_at = created_at WHERE updated_at IS NULL",
        )
    db.commit()


def normalize_status(status: str | None) -> str:
    raw = (status or STATUS_QUEUED).strip().lower()
    return _LEGACY_STATUS.get(raw, raw)


def _job_columns(conn) -> set[str]:
    try:
        rows = conn.execute("PRAGMA table_info(image_albums)").fetchall()
        return {row["name"] for row in rows}
    except Exception:
        return set()


def create_job(
    *,
    character_id: str,
    prompt: str,
    model: str,
    scene: str,
    style: str,
    meta: dict | None = None,
    trigger_type: str = "",
) -> str:
    job_id = str(uuid.uuid4())[:12]
    now = time.time()
    conn = state.db
    cols = _job_columns(conn)
    meta_json = json.dumps(meta or {}, ensure_ascii=False)

    if "updated_at" in cols:
        conn.execute(
            """
            INSERT INTO image_albums
            (job_id, character_id, url, prompt, model, scene, style, status,
             meta, created_at, updated_at, progress_text, trigger_type, attempt_count, error_message)
            VALUES (?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '')
            """,
            (
                job_id, character_id, prompt, model, scene, style,
                STATUS_QUEUED, meta_json, now, now,
                "排队中", trigger_type,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO image_albums
            (job_id, character_id, url, prompt, model, scene, style, status, meta, created_at)
            VALUES (?, ?, '', ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (job_id, character_id, prompt, model, scene, style, meta_json, now),
        )
    conn.commit()
    return job_id


def transition_job(
    job_id: str,
    status: str,
    *,
    progress_text: str = "",
    local_url: str = "",
    error_message: str = "",
    attempt_count: int | None = None,
    meta_patch: dict | None = None,
) -> dict[str, Any] | None:
    if not state.db:
        return None
    cols = _job_columns(state.db)
    meta = {}
    row = state.db.execute(
        "SELECT meta FROM image_albums WHERE job_id = ?", (job_id,),
    ).fetchone()
    if row and row["meta"]:
        try:
            meta = json.loads(row["meta"])
        except json.JSONDecodeError:
            meta = {}
    if meta_patch:
        meta.update(meta_patch)
    if error_message:
        meta["error"] = error_message

    if "updated_at" in cols:
        sets = ["status = ?", "meta = ?", "updated_at = ?"]
        params: list[Any] = [status, json.dumps(meta, ensure_ascii=False), time.time()]
        if progress_text:
            sets.append("progress_text = ?")
            params.append(progress_text)
        if local_url:
            sets.append("url = ?")
            params.append(local_url)
        if error_message and "error_message" in cols:
            sets.append("error_message = ?")
            params.append(error_message)
        if attempt_count is not None and "attempt_count" in cols:
            sets.append("attempt_count = ?")
            params.append(attempt_count)
        params.append(job_id)
        state.db.execute(
            f"UPDATE image_albums SET {', '.join(sets)} WHERE job_id = ?",
            params,
        )
    else:
        update_job_status(
            job_id,
            status,
            error=error_message,
            local_url=local_url,
            meta_patch=meta,
        )
    state.db.commit()
    return get_job(job_id)


def get_job(job_id: str) -> dict[str, Any] | None:
    if not state.db:
        return None
    row = state.db.execute(
        "SELECT * FROM image_albums WHERE job_id = ?", (job_id,),
    ).fetchone()
    if not row:
        return None
    meta: dict[str, Any] = {}
    if row["meta"]:
        try:
            meta = json.loads(row["meta"])
        except json.JSONDecodeError:
            meta = {}
    status = normalize_status(row["status"])
    created = float(row["created_at"] or time.time())
    keys = row.keys()
    updated = (
        float(row["updated_at"] or created)
        if "updated_at" in keys and row["updated_at"]
        else created
    )
    return {
        "job_id": row["job_id"],
        "character_id": row["character_id"],
        "url": row["url"],
        "prompt": row["prompt"],
        "model": row["model"],
        "scene": row["scene"],
        "style": row["style"],
        "status": status,
        "meta": meta,
        "created_at": created,
        "progress_text": (
            (row["progress_text"] if "progress_text" in keys else "") or _progress_for(status)
        ),
        "trigger_type": (row["trigger_type"] if "trigger_type" in keys else "") or "",
        "attempt_count": int(row["attempt_count"] or 0) if "attempt_count" in keys else 0,
        "error_message": (
            (row["error_message"] if "error_message" in keys else "")
            or meta.get("error", "")
        ),
        "updated_at": updated,
        "elapsed_seconds": max(0, int(time.time() - created)),
    }


def list_jobs_for_character(character_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    if not state.db:
        return []
    rows = state.db.execute(
        """
        SELECT job_id FROM image_albums
        WHERE character_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (character_id, limit),
    ).fetchall()
    return [get_job(r["job_id"]) for r in rows if get_job(r["job_id"])]


def _progress_for(status: str) -> str:
    return {
        STATUS_QUEUED: "排队中",
        STATUS_GENERATING: "生成中",
        STATUS_UPLOADING: "上传中",
        STATUS_RETRYING: "换模型重试中",
        STATUS_COMPLETED: "已完成",
        STATUS_FAILED: "生成失败",
    }.get(status, status)


async def push_image_job_update(room: str | None, job: dict[str, Any]) -> None:
    if not job:
        return
    cid = job.get("character_id", "")
    name = ""
    if state.persona_loader and cid:
        name = state.persona_loader.get_display_name(cid)
    payload = {
        "type": "image_job_update",
        "job_id": job.get("job_id"),
        "character_id": cid,
        "character_name": name,
        "status": normalize_status(job.get("status")),
        "model": job.get("model"),
        "progress_text": job.get("progress_text") or _progress_for(job.get("status", "")),
        "url": job.get("url") or "",
        "error_message": job.get("error_message") or "",
        "attempt_count": job.get("attempt_count") or 0,
        "elapsed_seconds": job.get("elapsed_seconds") or 0,
        "trigger_type": job.get("trigger_type") or "",
    }
    rooms = []
    if room:
        rooms.append(room)
    if cid:
        rooms.append(f"private:{cid}")
    rooms.append("global")
    await hub.send_rooms(list(dict.fromkeys(rooms)), payload)


async def _send_wait_hint(room: str, character_id: str, job_id: str) -> None:
    if not state.db:
        return
    msg_id = f"imgwait_{uuid.uuid4().hex[:10]}"
    content = "我还在整理，等我一下。"
    ts = world_now()
    state.db.execute(
        """INSERT INTO private_messages
           (id, character_id, sender_type, content, timestamp)
           VALUES (?, ?, ?, ?, ?)""",
        (msg_id, character_id, "character", content, ts),
    )
    state.db.commit()
    name = state.persona_loader.get_display_name(character_id) if state.persona_loader else character_id
    await hub.send_room(room, {
        "type": "message",
        "id": msg_id,
        "content": content,
        "sender_type": "character",
        "sender_id": character_id,
        "character_name": name,
        "timestamp": ts,
        "image_job_hint": True,
        "job_id": job_id,
    })
    transition_job(job_id, STATUS_GENERATING, progress_text="整理照片中，请稍等…")
    job = get_job(job_id)
    if job:
        await push_image_job_update(room, job)


async def _apply_failure_emotion(character_id: str, room: str) -> None:
    if not state.emo_engine:
        return
    applied = commit_emotion_delta(
        character_id,
        {"sad": 2.0, "stressed": 4.0, "tired": 2.0},
        "image_job_failed",
    )
    if applied:
        emo = state.emo_engine.get_summary(character_id)
        await push_emotion_update(character_id, applied, emo, room=room)


async def run_chat_image_job(
    room: str,
    job_id: str,
    *,
    character_id: str,
    scene: str,
    style: str,
    outfit: str,
    pose: str,
    emotion: str,
    exposure: str,
    extra: str,
    trigger: str,
) -> None:
    """Background task: 20s wait hint, 60s timeout, one fast-model retry."""
    if not SILICONFLOW_API_KEY:
        transition_job(job_id, STATUS_FAILED, error_message="API key not configured")
        job = get_job(job_id)
        if job:
            await push_image_job_update(room, job)
        return

    hint_sent = False

    async def maybe_wait_hint():
        nonlocal hint_sent
        await asyncio.sleep(WAIT_HINT_SECONDS)
        job = get_job(job_id)
        if not job:
            return
        st = normalize_status(job.get("status"))
        if st in (STATUS_QUEUED, STATUS_GENERATING, STATUS_RETRYING, STATUS_UPLOADING):
            hint_sent = True
            await _send_wait_hint(room, character_id, job_id)

    hint_task = asyncio.create_task(maybe_wait_hint())
    last_error = ""

    try:
        for attempt in range(MAX_ATTEMPTS):
            priority = "quality" if attempt == 0 else "fast"
            status = STATUS_GENERATING if attempt == 0 else STATUS_RETRYING
            progress = "生成中" if attempt == 0 else "换模型重试中"
            transition_job(
                job_id, status,
                progress_text=progress,
                attempt_count=attempt + 1,
            )
            job = get_job(job_id)
            if job:
                await push_image_job_update(room, job)

            try:
                result = await asyncio.wait_for(
                    generate_character_image(
                        character_id,
                        scene=scene,
                        style=style,
                        outfit=outfit,
                        pose=pose,
                        emotion=emotion,
                        exposure=exposure,
                        extra=extra,
                        priority=priority,
                        existing_job_id=job_id,
                    ),
                    timeout=ATTEMPT_TIMEOUT_SECONDS,
                )
                transition_job(
                    job_id, STATUS_COMPLETED,
                    progress_text="已完成",
                    local_url=result.get("url", ""),
                    attempt_count=attempt + 1,
                )
                msg_id = str(uuid.uuid4())
                ts = world_now()
                url = result.get("url", "")
                state.db.execute(
                    """INSERT INTO private_messages
                       (id, character_id, sender_type, content, content_type, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (msg_id, character_id, "character", url, "image", ts),
                )
                state.db.commit()

                job = get_job(job_id)
                if job:
                    await push_image_job_update(room, job)
                await hub.send_room(room, {
                    "type": "image_ready",
                    "message_id": msg_id,
                    "character_id": character_id,
                    "url": url,
                    "model": result.get("model"),
                    "route": result.get("route"),
                    "trigger": trigger,
                    "job_id": job_id,
                })
                return
            except (ImageEngineError, asyncio.TimeoutError, Exception) as exc:
                last_error = str(exc)
                logger.warning(
                    "Image job %s attempt %s failed: %s",
                    job_id, attempt + 1, exc,
                )
                if attempt + 1 >= MAX_ATTEMPTS:
                    break
                transition_job(
                    job_id, STATUS_RETRYING,
                    progress_text="首次失败，换模型重试…",
                    error_message=last_error,
                    attempt_count=attempt + 1,
                )
                job = get_job(job_id)
                if job:
                    await push_image_job_update(room, job)

        transition_job(
            job_id, STATUS_FAILED,
            progress_text="生成失败",
            error_message=last_error or "unknown error",
        )
        job = get_job(job_id)
        if job:
            await push_image_job_update(room, job)
        await hub.send_room(room, {
            "type": "error",
            "message": f"照片发送失败：{last_error or '生成超时'}",
            "job_id": job_id,
        })
        await _apply_failure_emotion(character_id, room)
    finally:
        hint_task.cancel()
        try:
            await hint_task
        except asyncio.CancelledError:
            pass
