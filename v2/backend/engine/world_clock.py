"""Shared in-world clock — one timeline for all characters and chats."""

from __future__ import annotations

import time
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import yaml

from config import CONFIG_DIR

DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_LOCATION = "云栖里·许宅"
_WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


@lru_cache(maxsize=1)
def _load_worldview() -> dict:
    path = CONFIG_DIR / "worldview.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_time_config() -> dict:
    world = _load_worldview().get("world") or {}
    return world.get("time") or {}


_time_cfg = _load_time_config()
TIMEZONE: str = _time_cfg.get("timezone") or DEFAULT_TIMEZONE
LOCATION: str = _time_cfg.get("location") or DEFAULT_LOCATION


def now() -> float:
    """Authoritative world timestamp (Unix seconds, shared by private & group chat)."""
    return time.time()


def _tz() -> ZoneInfo:
    return ZoneInfo(TIMEZONE)


def _dt(ts: float | None = None) -> datetime:
    return datetime.fromtimestamp(ts if ts is not None else now(), tz=_tz())


def format_clock(ts: float | None = None) -> str:
    """24-hour HH:mm in world timezone."""
    return _dt(ts).strftime("%H:%M")


def format_datetime(ts: float | None = None) -> str:
    return _dt(ts).strftime("%Y-%m-%d %H:%M")


def snapshot(ts: float | None = None) -> dict:
    dt = _dt(ts)
    return {
        "timestamp": dt.timestamp(),
        "timezone": TIMEZONE,
        "location": LOCATION,
        "clock": dt.strftime("%H:%M"),
        "date": dt.strftime("%Y-%m-%d"),
        "weekday": _WEEKDAYS[dt.weekday()],
        "datetime": dt.strftime("%Y-%m-%d %H:%M"),
    }


def context_line(ts: float | None = None) -> str:
    s = snapshot(ts)
    return f"【世界时间】{s['datetime']}（{s['weekday']}）· {s['location']}"


def world_rules_block() -> str:
    """Formatted world rules for LLM system prompts."""
    section = _load_worldview().get("world_rules") or {}
    items = section.get("items") or []
    if not items:
        return ""

    lines = ["【世界规则——叙事须一致，角色默认知晓】"]
    if desc := section.get("description"):
        lines.append(str(desc).strip())

    for idx, item in enumerate(items, 1):
        title = item.get("title") or item.get("id") or f"规则{idx}"
        rule = str(item.get("rule") or "").strip()
        if not rule:
            continue
        lines.append(f"{idx}. {title}：{rule}")
        notes = item.get("narrative") or []
        for note in notes[:4]:
            lines.append(f"   - {note}")

    return "\n".join(lines) if len(lines) > 1 else ""
