"""Shared in-world clock — one timeline for all characters and chats."""

from __future__ import annotations

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml

from config import CONFIG_DIR

DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_LOCATION = "云栖里·许宅"
_WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def _load_time_config() -> dict:
    path = CONFIG_DIR / "worldview.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    world = data.get("world") or {}
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
