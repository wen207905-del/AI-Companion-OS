"""Current activity assignment for proactive sharing."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from config import CONFIG_DIR
from engine.world_clock import TIMEZONE

_PROACTIVE_PATH = CONFIG_DIR / "proactive_intents.yaml"
_cached_config: dict[str, Any] | None = None

_TIME_ACTIVITY_POOL: list[tuple[tuple[int, int], list[str]]] = [
    ((6, 11), ["备餐", "整理资料", "打扫", "整理房间"]),
    ((11, 17), ["温汤", "做题", "画画", "看剧", "整理资料"]),
    ((17, 22), ["吃烧烤", "备餐", "看剧", "刷手机"]),
    ((22, 6), ["休息", "刷手机", "看剧"]),
]


def load_proactive_config() -> dict[str, Any]:
    global _cached_config
    if _cached_config is not None:
        return _cached_config
    if not _PROACTIVE_PATH.exists():
        _cached_config = {}
        return _cached_config
    with open(_PROACTIVE_PATH, encoding="utf-8") as f:
        _cached_config = yaml.safe_load(f) or {}
    return _cached_config


def get_current_activity(db, character_id: str) -> str:
    row = db.execute(
        "SELECT current_activity FROM character_user_relation WHERE character_id = ?",
        (character_id,),
    ).fetchone()
    if row and row["current_activity"]:
        return row["current_activity"]
    init = load_proactive_config()
    return "日常"


def get_activity_share_desire(activity: str, config: dict[str, Any] | None = None) -> float:
    cfg = config or load_proactive_config()
    activities = cfg.get("activities") or {}
    entry = activities.get(activity) or activities.get("日常") or {}
    return float(entry.get("share_desire", 45))


def get_preferred_intents(activity: str, config: dict[str, Any] | None = None) -> list[str]:
    cfg = config or load_proactive_config()
    activities = cfg.get("activities") or {}
    entry = activities.get(activity) or activities.get("日常") or {}
    intents = entry.get("preferred_intents") or ["daily_share"]
    return list(intents)


def _hour_in_world() -> int:
    return datetime.now(tz=ZoneInfo(TIMEZONE)).hour


def _pick_activity_for_hour(character_id: str, hour: int) -> str:
    for (start, end), pool in _TIME_ACTIVITY_POOL:
        if start <= end:
            if start <= hour < end:
                idx = sum(ord(c) for c in character_id) % len(pool)
                return pool[idx]
        elif hour >= start or hour < end:
            idx = sum(ord(c) for c in character_id) % len(pool)
            return pool[idx]
    return "日常"


def maybe_refresh_activity(db, character_id: str, *, min_interval_hours: float = 4.0) -> str:
    """Rotate activity if stale; returns current activity."""
    row = db.execute(
        "SELECT current_activity, updated_at FROM character_user_relation WHERE character_id = ?",
        (character_id,),
    ).fetchone()
    if not row:
        return "日常"

    now = time.time()
    updated_at = float(row["updated_at"] or 0)
    current = row["current_activity"] or "日常"

    if now - updated_at < min_interval_hours * 3600:
        return current

    new_activity = _pick_activity_for_hour(character_id, _hour_in_world())
    if new_activity == current:
        db.execute(
            "UPDATE character_user_relation SET updated_at = ? WHERE character_id = ?",
            (now, character_id),
        )
        db.commit()
        return current

    db.execute(
        """
        UPDATE character_user_relation
        SET current_activity = ?, updated_at = ?
        WHERE character_id = ?
        """,
        (new_activity, now, character_id),
    )
    db.commit()
    return new_activity
