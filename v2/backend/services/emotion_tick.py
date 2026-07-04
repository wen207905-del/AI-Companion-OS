"""V4.1 emotion tick — decay, drift, delta commit, and WS push."""

from __future__ import annotations

import json
import logging
from typing import Any

from api.ws_hub import hub
from app_state import state
from engine.absence import hours_since_last_user_message
from services.social_relation_service import get_relation_meta

logger = logging.getLogger("companion.emotion_tick")


def _activity_table_exists() -> bool:
    try:
        row = state.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='activity_emotion_snapshots'"
        ).fetchone()
        return bool(row)
    except Exception:
        return False


def build_emotion_update_payload(
    character_id: str,
    emotion: dict[str, Any],
    emotion_delta: dict[str, float],
) -> dict[str, Any]:
    return {
        "type": "emotion_update",
        "character_id": character_id,
        "emotion": emotion,
        "emotion_delta": emotion_delta,
        "deltas": {"emotion": emotion_delta},
    }


async def push_emotion_update(
    character_id: str,
    emotion_delta: dict[str, float],
    emotion: dict[str, Any] | None = None,
    *,
    room: str | None = None,
) -> None:
    if not emotion_delta and not emotion:
        return
    emo = emotion or (state.emo_engine.get_summary(character_id) if state.emo_engine else {})
    payload = build_emotion_update_payload(character_id, emo, emotion_delta)
    rooms = []
    if room:
        rooms.append(room)
    rooms.extend([f"private:{character_id}", "global"])
    deduped = list(dict.fromkeys(rooms))
    await hub.send_rooms(deduped, payload)


def commit_emotion_delta(
    character_id: str,
    deltas: dict[str, float],
    event_id: str,
    *,
    activity: str = "",
    apply_rel_security: float | None = None,
) -> dict[str, float]:
    if not state.emo_engine:
        return {}
    applied = state.emo_engine.apply_delta(character_id, deltas)
    if apply_rel_security is not None and state.rel_engine:
        state.rel_engine.apply_effect(character_id, "security", apply_rel_security, event_id)
        state.rel_engine.save_snapshot(character_id, event_id)
    state.emo_engine.save_snapshot(
        character_id,
        event_id,
        activity=activity,
        delta_json=applied,
    )
    _save_activity_snapshot(character_id, activity, applied)
    return applied


def _save_activity_snapshot(
    character_id: str,
    activity: str,
    deltas: dict[str, float],
) -> None:
    if not state.db or not state.emo_engine or not _activity_table_exists():
        return
    emo = state.emo_engine.get_summary(character_id)
    state.db.execute(
        """
        INSERT INTO activity_emotion_snapshots
        (character_id, activity, happy, lonely, miss_user, primary_mood, delta_json, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            character_id,
            activity or "",
            emo.get("happy", 50),
            emo.get("lonely", 15),
            emo.get("miss_user", 20),
            emo.get("primary_mood", "平静"),
            json.dumps(deltas, ensure_ascii=False),
            __import__("time").time(),
        ),
    )
    state.db.commit()


def apply_user_message_emotion(
    character_id: str,
    user_message: str,
    rel_summary: dict | None = None,
) -> dict[str, float]:
    if not state.emo_engine:
        return {}
    meta = get_relation_meta(state.db, character_id) if state.db else {}
    grade = meta.get("affection_grade") or (rel_summary or {}).get("affection_grade", "在意")
    activity = meta.get("current_activity", "日常")

    emo_delta = state.emo_engine.apply_user_reply_delta(
        character_id, user_message, affection_grade=grade,
    )
    perfunctory = len((user_message or "").strip()) <= 4
    security_delta = -1.0 if perfunctory else min(5.0, 1.0 + len((user_message or "").strip()) * 0.05)
    return commit_emotion_delta(
        character_id,
        emo_delta,
        "user_reply",
        activity=activity,
        apply_rel_security=security_delta,
    )


def apply_character_reply_emotion(character_id: str) -> dict[str, float]:
    if not state.emo_engine:
        return {}
    meta = get_relation_meta(state.db, character_id) if state.db else {}
    activity = meta.get("current_activity", "日常")
    emo_delta = state.emo_engine.apply_character_reply_delta(character_id)
    return commit_emotion_delta(character_id, emo_delta, "character_reply", activity=activity)


def apply_scene_event_emotions(events: list[dict]) -> dict[str, dict[str, float]]:
    if not state.emo_engine:
        return {}
    applied_map: dict[str, dict[str, float]] = {}
    for ev in events or []:
        cid = ev.get("character_id")
        raw_delta = ev.get("emotion_delta")
        if not cid or not isinstance(raw_delta, dict):
            continue
        numeric = {k: float(v) for k, v in raw_delta.items() if isinstance(v, (int, float))}
        if not numeric:
            continue
        meta = get_relation_meta(state.db, cid) if state.db else {}
        applied = commit_emotion_delta(
            cid,
            numeric,
            "scene_event",
            activity=meta.get("current_activity", "日常"),
        )
        if applied:
            applied_map[cid] = applied
    return applied_map


async def run_emotion_tick() -> list[str]:
    """Run 5-minute emotion decay/drift for all characters."""
    if not state.emo_engine or not state.persona_loader or not state.db:
        return []

    updated: list[str] = []
    for character_id in state.persona_loader.personas:
        hours = hours_since_last_user_message(state.db, character_id)
        meta = get_relation_meta(state.db, character_id)
        grade = meta.get("affection_grade", "在意")
        activity = meta.get("current_activity", "日常")

        deltas = state.emo_engine.decay_tick(
            character_id,
            hours_since_user=hours,
            affection_grade=grade,
        )
        if not deltas and hours < 0.5:
            continue

        state.emo_engine.save_snapshot(
            character_id,
            "emotion_tick",
            activity=activity,
            delta_json=deltas,
        )
        _save_activity_snapshot(character_id, activity, deltas)

        if deltas:
            updated.append(character_id)
            emo = state.emo_engine.get_summary(character_id)
            await push_emotion_update(
                character_id,
                deltas,
                emo,
                room=f"private:{character_id}",
            )

    return updated
