"""
World Event Generator — 世界事件生成器

基于时间 + 天气 + 节日生成世界事件。
事件类型：rain_started / rain_stopped / sunrise / sunset / holiday_arrived / midnight 等。

世界事件发布到 EventBus，由各引擎订阅处理。
"""

from datetime import datetime
from typing import Optional


class WorldEventGenerator:
    """世界事件生成器 — 动态世界事件系统。"""

    EVENT_TYPES = {
        "rain_started":      "开始下雨了",
        "rain_stopped":      "雨停了",
        "sunrise":           "太阳升起了",
        "sunset":            "太阳落山了",
        "holiday_arrived":   "节日到了",
        "midnight":          "午夜来临",
        "season_changed":    "季节变化",
        "heavy_snow":        "下起了大雪",
        "full_moon":         "满月之夜",
    }

    def __init__(self, event_bus=None, db=None):
        self.event_bus = event_bus
        self.db = db
        self._last_weather = None
        self._last_time_period = None
        self._last_season = None

    def generate(self, world_state, calendar_events: list = None) -> list:
        """生成当前世界事件。

        Returns:
            [{"event_type": str, "description": str, "timestamp": str}, ...]
        """
        events = []
        now = datetime.now()

        # 获取世界属性
        tp = getattr(world_state, "time_period", None) or "day"
        weather = getattr(world_state, "weather", None)
        weather_type = weather.type if hasattr(weather, "type") else (
            weather if isinstance(weather, str) else "clear"
        )
        season = getattr(world_state, "season", None) or "summer"
        hour = getattr(world_state, "hour", None) or now.hour

        # 1. 天气变化事件
        if weather_type != self._last_weather and self._last_weather is not None:
            if weather_type == "rainy":
                events.append({
                    "event_type": "rain_started",
                    "description": "开始下雨了",
                    "timestamp": now.isoformat(),
                    "emotional_impact": {"calm": 8, "lonely": 3},
                })
            elif self._last_weather == "rainy" and weather_type != "rainy":
                events.append({
                    "event_type": "rain_stopped",
                    "description": "雨停了",
                    "timestamp": now.isoformat(),
                    "emotional_impact": {"happy": 5},
                })

        self._last_weather = weather_type

        # 2. 时间段变化事件
        if tp != self._last_time_period and self._last_time_period is not None:
            if tp == "morning":
                events.append({
                    "event_type": "sunrise",
                    "description": "太阳升起了",
                    "timestamp": now.isoformat(),
                    "emotional_impact": {"excited": 5, "sleepy": -10},
                })
            elif tp == "evening":
                events.append({
                    "event_type": "sunset",
                    "description": "太阳落山了",
                    "timestamp": now.isoformat(),
                    "emotional_impact": {"calm": 5, "sad": 2},
                })
            elif tp == "late_night":
                events.append({
                    "event_type": "midnight",
                    "description": "午夜来临，世界安静了",
                    "timestamp": now.isoformat(),
                    "emotional_impact": {"lonely": 10, "sleepy": 15, "calm": 10},
                })

        self._last_time_period = tp

        # 3. 季节变化事件
        if season != self._last_season and self._last_season is not None:
            events.append({
                "event_type": "season_changed",
                "description": f"季节从{self._last_season}变为{season}",
                "timestamp": now.isoformat(),
                "emotional_impact": {},
            })

        self._last_season = season

        # 4. 节日事件
        if calendar_events:
            for ce in calendar_events:
                if ce.get("type") == "holiday":
                    events.append({
                        "event_type": "holiday_arrived",
                        "description": f"{ce.get('name')}到了！",
                        "timestamp": now.isoformat(),
                        "emotional_impact": ce.get("impact", {}),
                    })

        # 5. 发布到事件总线
        if self.event_bus:
            for event in events:
                self.event_bus.publish("world_event", event)

        return events

    def get_recent_events(self, limit: int = 10) -> list:
        """获取最近的世界事件（从数据库）。"""
        if self.db:
            try:
                return self.db.get_recent_world_events(limit)
            except Exception:
                pass
        return []
