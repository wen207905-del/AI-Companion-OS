"""
Calendar Engine — 节日/纪念日系统

功能：
  - 节日检测（春节、情人节、七夕、圣诞节、元旦等）
  - 纪念日追踪（角色首次对话日、重要事件日）
  - 节日/纪念日产生特殊事件和情绪偏移
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional

# ── 节日定义 ──
# 格式: (name, month, day, emotional_impact)
FIXED_HOLIDAYS = [
    ("元旦", 1, 1, {"happy": 10, "excited": 8}),
    ("情人节", 2, 14, {"lonely": 10, "miss_user": 15, "shy": 5, "excited": 5}),
    ("妇女节", 3, 8, {"happy": 5, "calm": 3}),
    ("愚人节", 4, 1, {"excited": 10, "happy": 5}),
    ("劳动节", 5, 1, {"calm": 5, "happy": 5}),
    ("儿童节", 6, 1, {"happy": 10, "excited": 8}),
    ("七夕", 8, 10, {"lonely": 12, "miss_user": 15, "romantic": 15}),
    ("中秋节", 9, 17, {"lonely": 10, "miss_user": 10, "calm": 5}),
    ("国庆节", 10, 1, {"happy": 10, "excited": 8}),
    ("万圣节", 10, 31, {"excited": 10, "shy": 3}),
    ("感恩节", 11, 28, {"calm": 10, "happy": 5}),
    ("圣诞节", 12, 25, {"lonely": 10, "miss_user": 15, "happy": 5, "romantic": 10}),
]

# 农历节日（此处仅用于检测提示，不做精确农历转换）
LUNAR_HOLIDAYS = ["春节", "元宵节", "端午节", "中秋节", "重阳节"]
# 简化：用固定阳历日期近似表示（实际应接入农历库）
LUNAR_APPROX = {
    "春节": (1, 25),
    "元宵节": (2, 8),
    "端午节": (6, 10),
    "重阳节": (10, 11),
}

# ── 世界事件类型 ──


class EventLevel(Enum):
    NORMAL = "normal"       # 普通
    SPECIAL = "special"     # 特殊节日/纪念日
    CRITICAL = "critical"   # 重大事件


# ── 纪念日类型 ──
ANNIVERSARY_TYPES = {
    "first_chat": "初次对话日",
    "first_confession": "初次告白日",
    "first_date": "初次约会日",
    "birthday": "生日",
}


class CalendarEngine:
    """日历引擎 — 节日检测 + 纪念日追踪。"""

    def __init__(self, db=None):
        self.db = db
        # 从数据库加载的纪念日缓存
        self._anniversaries: dict = {}  # character_id → [(date, type), ...]

    def check(self, game_time: datetime = None) -> list:
        """检查当前日期是否有特殊事件。

        Returns:
            [{"type": "holiday"|"anniversary", "name": str, "impact": {...}}, ...]
        """
        now = game_time or datetime.now()
        today = now.date()
        events = []

        # 1. 节日检测
        for name, month, day, impact in FIXED_HOLIDAYS:
            if today.month == month and today.day == day:
                events.append({
                    "type": "holiday",
                    "name": name,
                    "impact": impact,
                    "level": EventLevel.SPECIAL.value,
                })

        # 2. 农历节日近似检测
        for name, (month, day) in LUNAR_APPROX.items():
            if today.month == month and today.day == day:
                events.append({
                    "type": "holiday",
                    "name": name,
                    "impact": {"happy": 10, "lonely": 8, "miss_user": 10},
                    "level": EventLevel.SPECIAL.value,
                })

        # 3. 纪念日检测
        if self.db:
            try:
                anniversaries = self.db.get_anniversaries_for_date(today)
                for ann in (anniversaries or []):
                    events.append({
                        "type": "anniversary",
                        "name": ann.get("type", "纪念日"),
                        "character_id": ann.get("character_id"),
                        "impact": {"happy": 10, "calm": 5, "miss_user": 5},
                        "level": EventLevel.SPECIAL.value,
                    })
            except Exception:
                pass

        return events

    def is_holiday(self, game_time: datetime = None) -> bool:
        """当前是否为节日。"""
        events = self.check(game_time)
        return any(e["type"] == "holiday" for e in events)

    def get_holiday_name(self, game_time: datetime = None) -> Optional[str]:
        """获取当前节日名称。"""
        events = self.check(game_time)
        for e in events:
            if e["type"] == "holiday":
                return e["name"]
        return None

    def add_anniversary(self, character_id: str, anniversary_type: str,
                          ann_date: date):
        """添加纪念日。"""
        key = f"{character_id}:{anniversary_type}"
        self._anniversaries.setdefault(character_id, []).append({
            "date": ann_date.isoformat(),
            "type": anniversary_type,
        })

        if self.db:
            try:
                self.db.insert_calendar_event(
                    character_id=character_id,
                    event_type="anniversary",
                    event_name=ANNIVERSARY_TYPES.get(anniversary_type, anniversary_type),
                    event_date=str(ann_date),
                    repeat_yearly=True,
                )
            except Exception:
                pass

    def get_upcoming_events(self, days: int = 7) -> list:
        """获取未来 N 天内的事件。"""
        now = datetime.now()
        upcoming = []

        # 节日
        for days_offset in range(days):
            check_date = now + __import__("datetime").timedelta(days=days_offset)
            for name, month, day, impact in FIXED_HOLIDAYS:
                if check_date.month == month and check_date.day == day:
                    upcoming.append({
                        "name": name,
                        "date": check_date.strftime("%Y-%m-%d"),
                        "days_away": days_offset,
                    })

        return upcoming
