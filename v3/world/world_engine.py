"""
世界引擎

整合时间系统、天气系统、环境系统，统一管理和生成世界状态。
是 World Tick 调度的核心对象。
"""

import random
from datetime import datetime
from typing import Optional

from .world_state import WorldState, Weather, Environment
from .time_engine import TimeEngine
from .weather_engine import WeatherEngine
from ..config import (
    DEFAULT_ACTIVITIES_BY_PERIOD,
    TIME_PERIODS,
    SEASONS,
)


class WorldEngine:
    """世界引擎 — 整合时间、天气、环境三大子系统。

    负责：
    - 每个 tick 生成完整的世界状态快照
    - 管理全局事件（天气变化、时间切换等）
    - 为角色推荐当前时间段的活动
    - 生成环境氛围描述
    """

    def __init__(self, acceleration_ratio: float = 0, initial_weather: str = "sunny"):
        """
        Args:
            acceleration_ratio: 时间加速倍率
            initial_weather: 初始天气类型
        """
        self.time_engine = TimeEngine(acceleration_ratio=acceleration_ratio)
        self.weather_engine = WeatherEngine(initial_weather=initial_weather)
        self._last_time_period: Optional[str] = None
        self._last_weather: Optional[str] = None
        self._global_events: list = []

    def tick(self) -> WorldState:
        """执行一次世界 tick，更新所有子系统并生成世界状态快照。

        Returns:
            完整的 WorldState 对象
        """
        # 1. 推进时间
        self.time_engine.advance_time(300)  # 默认 5 分钟
        time_summary = self.time_engine.get_current_state_summary()

        # 2. 更新季节信息并同步给天气引擎
        season = time_summary["season"]
        self.weather_engine.set_season(season)

        # 3. 更新天气
        weather_dict = self.weather_engine.tick()
        weather_obj = Weather.from_dict(weather_dict)

        # 4. 检测状态变化，生成全局事件
        self._global_events = []
        self._detect_transitions(time_summary, weather_dict)

        # 5. 生成环境状态
        env = self._generate_environment(season, time_summary["time_period"], weather_dict)

        # 6. 组装 WorldState
        world_state = WorldState(
            datetime_text=time_summary["datetime"],
            day_of_week=time_summary["day_of_week"],
            time_period=time_summary["time_period"],
            season=season,
            weather=weather_obj,
            environment=env,
            global_events=self._global_events,
        )

        return world_state

    def get_recommended_activity(self, character_id: str) -> str:
        """根据当前时间段为角色推荐活动。

        Args:
            character_id: 角色 ID（预留，未来可根据角色性格定制）

        Returns:
            推荐的活动描述字符串
        """
        period = self.time_engine.get_time_period()
        activities = DEFAULT_ACTIVITIES_BY_PERIOD.get(period, ["休息"])
        # 根据天气微调
        weather = self.weather_engine.current_weather
        if weather in ("rainy", "heavy_rain") and "散步" in activities:
            activities = [a for a in activities if a not in ("散步", "逛街", "运动")]
            activities.append("听雨发呆")

        return random.choice(activities)

    def get_atmosphere_description(self) -> str:
        """生成当前世界的氛围文字描述。

        Returns:
            氛围描述文本
        """
        period = self.time_engine.get_time_period()
        period_label = self.time_engine.get_time_period_label(period)
        weather = self.weather_engine.current_weather
        weather_label = self.weather_engine.get_current_weather()["label"]

        templates = {
            ("sunny", "morning"): f"{period_label}的阳光洒进来，新的一天开始了。",
            ("rainy", "night"): f"{period_label}的雨声让整个世界都安静了下来。",
            ("rainy", "late_night"): f"深夜的{weather_label}，窗外只有滴答的雨声。",
            ("snowy", "evening"): f"{period_label}的雪花飘落，世界一片洁白。",
        }

        key = (weather, period)
        if key in templates:
            return templates[key]

        return f"{period_label}，天气{weather_label}。"

    def get_global_events(self) -> list:
        """获取当前 tick 产生的全局事件列表。"""
        return self._global_events

    def _detect_transitions(self, time_summary: dict, weather_dict: dict):
        """检测时间和天气的状态切换，产生全局事件。"""
        current_period = time_summary["time_period"]
        current_weather = weather_dict["type"]

        # 时间段切换事件
        if self._last_time_period is not None and current_period != self._last_time_period:
            self._global_events.append({
                "type": "time_period_change",
                "from": self._last_time_period,
                "to": current_period,
                "desc": f"时间从 {self._last_time_period} 切换到 {current_period}",
            })

        # 天气切换事件
        if self._last_weather is not None and current_weather != self._last_weather:
            self._global_events.append({
                "type": "weather_change",
                "from": self._last_weather,
                "to": current_weather,
                "desc": f"天气从 {self._last_weather} 转变为 {current_weather}",
            })

        self._last_time_period = current_period
        self._last_weather = current_weather

    @staticmethod
    def _generate_environment(season: str, time_period: str, weather_dict: dict) -> Environment:
        """根据时间、季节和天气生成环境状态。"""
        from .world_state import Environment

        # 光线判定
        light_map = {
            "early_morning": "dim",
            "morning": "bright",
            "noon": "bright",
            "afternoon": "bright",
            "evening": "dim",
            "night": "dark",
            "late_night": "dark",
        }
        light = light_map.get(time_period, "bright")

        # 天气修正光线
        if weather_dict["type"] in ("rainy", "heavy_rain", "stormy", "overcast"):
            if light == "bright":
                light = "dim"
            elif light == "dim":
                light = "dark"

        # 噪音判定
        noise_map = {
            "early_morning": "quiet",
            "morning": "normal",
            "noon": "normal",
            "afternoon": "normal",
            "evening": "normal",
            "night": "quiet",
            "late_night": "quiet",
        }
        noise = noise_map.get(time_period, "normal")

        # 天气修正噪音
        if weather_dict["type"] in ("stormy", "heavy_rain"):
            noise = "noisy"

        # 氛围判定
        atmosphere = "peaceful"
        if weather_dict["type"] in ("rainy", "heavy_rain"):
            atmosphere = "lonely"
        elif weather_dict["type"] == "stormy":
            atmosphere = "restless"
        elif weather_dict["type"] == "snowy":
            atmosphere = "romantic"
        elif time_period == "late_night":
            atmosphere = "lonely"
        elif time_period == "evening":
            atmosphere = "warm"

        return Environment(
            season=season,
            light=light,
            noise=noise,
            atmosphere=atmosphere,
        )
