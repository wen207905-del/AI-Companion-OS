"""Tests for V4.1 image job state machine."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import init_db
from services.image_job_service import (
    ATTEMPT_TIMEOUT_SECONDS,
    MAX_ATTEMPTS,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_GENERATING,
    STATUS_QUEUED,
    STATUS_RETRYING,
    WAIT_HINT_SECONDS,
    create_job,
    ensure_image_job_schema,
    get_job,
    normalize_status,
    run_chat_image_job,
    transition_job,
)


def _memory_db():
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    ensure_image_job_schema(conn)
    return conn


def test_normalize_status_legacy():
    assert normalize_status("pending") == STATUS_QUEUED
    assert normalize_status("generating") == STATUS_GENERATING
    assert normalize_status("completed") == STATUS_COMPLETED


def test_create_and_transition_job():
    db = _memory_db()
    from app_state import state

    state.db = db
    job_id = create_job(
        character_id="ye_ruxue",
        prompt="test prompt",
        model="Qwen/Qwen-Image",
        scene="bedroom",
        style="selfie",
        trigger_type="user_request",
    )
    job = get_job(job_id)
    assert job is not None
    assert job["status"] == STATUS_QUEUED
    assert job["trigger_type"] == "user_request"

    transition_job(job_id, STATUS_GENERATING, progress_text="生成中", attempt_count=1)
    job = get_job(job_id)
    assert job["status"] == STATUS_GENERATING
    assert job["attempt_count"] == 1
    assert job["progress_text"] == "生成中"


def test_state_flow_to_completed():
    db = _memory_db()
    from app_state import state

    state.db = db
    job_id = create_job(
        character_id="ye_ruxue",
        prompt="p",
        model="m",
        scene="s",
        style="st",
    )
    for status, text in [
        (STATUS_QUEUED, "排队中"),
        (STATUS_GENERATING, "生成中"),
        (STATUS_GENERATING, "上传中"),
        (STATUS_COMPLETED, "已完成"),
    ]:
        transition_job(job_id, status, progress_text=text, local_url="/static/x.png" if status == STATUS_COMPLETED else "")
    job = get_job(job_id)
    assert job["status"] == STATUS_COMPLETED
    assert job["url"] == "/static/x.png"


def test_run_job_success(monkeypatch):
    async def _run():
        db = _memory_db()
        from app_state import state

        state.db = db
        state.persona_loader = MagicMock()
        state.persona_loader.get_display_name.return_value = "叶如雪"
        state.emo_engine = MagicMock()

        job_id = create_job(
            character_id="ye_ruxue",
            prompt="p",
            model="m",
            scene="bedroom",
            style="selfie",
        )

        async def fake_generate(*args, **kwargs):
            return {"url": "/static/albums/ye_ruxue/abc.png", "model": "fast", "route": {}}

        sent = []

        async def fake_push(room, job):
            sent.append((room, job["status"]))

        async def fake_hub(room, payload):
            sent.append((room, payload.get("type")))

        monkeypatch.setattr(
            "services.image_job_service.generate_character_image",
            fake_generate,
        )
        monkeypatch.setattr("services.image_job_service.push_image_job_update", fake_push)
        monkeypatch.setattr("services.image_job_service.hub.send_room", fake_hub)
        monkeypatch.setattr("services.image_job_service.SILICONFLOW_API_KEY", "test-key")

        await run_chat_image_job(
            "private:ye_ruxue",
            job_id,
            character_id="ye_ruxue",
            scene="bedroom",
            style="selfie",
            outfit="",
            pose="",
            emotion="",
            exposure="full_clothed",
            extra="自拍",
            trigger="user_request",
        )

        job = get_job(job_id)
        assert job["status"] == STATUS_COMPLETED
        row = db.execute(
            "SELECT content_type FROM private_messages WHERE character_id = ?",
            ("ye_ruxue",),
        ).fetchone()
        assert row is not None
        assert row["content_type"] == "image"
        statuses = [s for _, s in sent if isinstance(s, str) and s in (
            STATUS_QUEUED, STATUS_GENERATING, STATUS_RETRYING, STATUS_COMPLETED,
        )]
        assert STATUS_GENERATING in statuses
        assert STATUS_COMPLETED in statuses

    asyncio.run(_run())


def test_run_job_retries_then_fails(monkeypatch):
    async def _run():
        db = _memory_db()
        from app_state import state

        state.db = db
        state.persona_loader = MagicMock()
        state.persona_loader.get_display_name.return_value = "叶如雪"
        state.emo_engine = MagicMock()
        state.emo_engine.apply_delta.return_value = {"sad": 2.0, "stressed": 4.0}
        state.emo_engine.get_summary.return_value = {"primary_mood": "低落"}

        job_id = create_job(
            character_id="ye_ruxue",
            prompt="p",
            model="m",
            scene="bedroom",
            style="selfie",
        )

        calls = {"n": 0}

        async def always_fail(*args, **kwargs):
            calls["n"] += 1
            raise RuntimeError("api down")

        monkeypatch.setattr(
            "services.image_job_service.generate_character_image",
            always_fail,
        )
        monkeypatch.setattr("services.image_job_service.push_image_job_update", AsyncMock())
        monkeypatch.setattr("services.image_job_service.hub.send_room", AsyncMock())
        monkeypatch.setattr("services.image_job_service.SILICONFLOW_API_KEY", "test-key")
        monkeypatch.setattr("services.image_job_service.WAIT_HINT_SECONDS", 0.01)
        monkeypatch.setattr("services.image_job_service.ATTEMPT_TIMEOUT_SECONDS", 0.5)

        await run_chat_image_job(
            "private:ye_ruxue",
            job_id,
            character_id="ye_ruxue",
            scene="bedroom",
            style="selfie",
            outfit="",
            pose="",
            emotion="",
            exposure="full_clothed",
            extra="",
            trigger="user_request",
        )

        assert calls["n"] == MAX_ATTEMPTS
        job = get_job(job_id)
        assert job["status"] == STATUS_FAILED
        state.emo_engine.apply_delta.assert_called_once()

    asyncio.run(_run())


def test_wait_hint_after_20s(monkeypatch):
    async def _run():
        db = _memory_db()
        from app_state import state

        state.db = db
        state.persona_loader = MagicMock()
        state.persona_loader.get_display_name.return_value = "叶如雪"
        state.emo_engine = MagicMock()

        job_id = create_job(
            character_id="ye_ruxue",
            prompt="p",
            model="m",
            scene="bedroom",
            style="selfie",
        )

        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(0.05)
            return {"url": "/static/x.png", "model": "m", "route": {}}

        hub_calls = []

        async def capture_hub(room, payload):
            hub_calls.append(payload)

        monkeypatch.setattr("services.image_job_service.WAIT_HINT_SECONDS", 0.02)
        monkeypatch.setattr("services.image_job_service.generate_character_image", slow_generate)
        monkeypatch.setattr("services.image_job_service.push_image_job_update", AsyncMock())
        monkeypatch.setattr("services.image_job_service.hub.send_room", capture_hub)
        monkeypatch.setattr("services.image_job_service.SILICONFLOW_API_KEY", "test-key")

        await run_chat_image_job(
            "private:ye_ruxue",
            job_id,
            character_id="ye_ruxue",
            scene="bedroom",
            style="selfie",
            outfit="",
            pose="",
            emotion="",
            exposure="full_clothed",
            extra="",
            trigger="user_request",
        )

        hint_msgs = [
            p for p in hub_calls
            if p.get("type") == "message" and "整理" in p.get("content", "")
        ]
        assert hint_msgs, "expected wait-hint message after delay"
        row = db.execute(
            "SELECT content FROM private_messages WHERE character_id = ? AND content LIKE ?",
            ("ye_ruxue", "%整理%"),
        ).fetchone()
        assert row is not None

    asyncio.run(_run())
