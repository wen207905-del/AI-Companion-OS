"""
世界状态数据结构

定义 WorldState、Weather、Environment 等核心数据类，
作为 V3 系统中所有模块的通用数据交换格式。
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Weather:
    """天气状态数据类。

    Attributes:
        type: 天气类型（sunny / cloudy / rainy 等）
        temperature: 温度（摄氏度）
        humidity: 湿度百分比（0-100）
        wind_level: 风力等级（0-12）
        mood_bias: 天气带来的情绪倾向
        label: 中文天气名称
    """
    type: str = "sunny"
    temperature: float = 25.0
    humidity: float = 50.0
    wind_level: int = 1
    mood_bias: str = "neutral"
    label: str = "晴天"

    def to_dict(self) -> dict:
        """转换为字典，便于序列化和数据库写入。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Weather":
        """从字典创建 Weather 实例。"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Environment:
    """环境状态数据类。

    Attributes:
        season: 季节（spring / summer / autumn / winter）
        light: 光线状态（bright / dim / dark）
        noise: 噪音水平（quiet / normal / noisy）
        atmosphere: 整体氛围描述
    """
    season: str = "summer"
    light: str = "bright"
    noise: str = "quiet"
    atmosphere: str = "peaceful"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Environment":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WorldState:
    """世界状态数据类 — V3 系统中所有模块的全局状态载体。

    Attributes:
        datetime_text: ISO 格式时间字符串
        day_of_week: 星期几（英文，如 Monday）
        time_period: 时间段（early_morning / morning / noon 等）
        weather: 天气状态对象
        environment: 环境状态对象
        global_events: 当前 tick 发生的全局事件列表
        season: 当前季节
    """
    datetime_text: str = ""
    day_of_week: str = ""
    time_period: str = "morning"
    weather: Weather = field(default_factory=Weather)
    environment: Environment = field(default_factory=Environment)
    global_events: list = field(default_factory=list)
    season: str = "summer"

    @property
    def dt(self) -> Optional[datetime]:
        """将 datetime_text 解析为 datetime 对象。"""
        try:
            return datetime.fromisoformat(self.datetime_text)
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> dict:
        """转换为字典，便于数据库写入。"""
        return {
            "datetime": self.datetime_text,
            "day_of_week": self.day_of_week,
            "time_period": self.time_period,
            "season": self.season,
            "weather": self.weather.to_dict(),
            "environment": self.environment.to_dict(),
            "global_events": self.global_events,
        }

    def get_scene_key(self) -> str:
        """
        生成场景标识键，用于中央意识层的场景分类。

        Returns:
            形如 "late_night_rainy_lonely" 的场景键
        """
        parts = [self.time_period, self.weather.type]
        if self.weather.mood_bias:
            parts.append(self.weather.mood_bias)
        return "_".join(parts)

    def __repr__(self) -> str:
        return (
            f"WorldState(time={self.datetime_text}, period={self.time_period}, "
            f"weather={self.weather.type}, temp={self.weather.temperature}°C, "
            f"events={len(self.global_events)})"
        )


@dataclass
class CharacterActivityState:
    """角色活动状态数据类。

    Attributes:
        character_id: 角色唯一标识
        current_activity: 当前正在进行的活动
        current_location: 当前所在位置
        activity_started: 活动开始时间（ISO 字符串）
        updated_at: 状态最后更新时间
    """
    character_id: str = ""
    current_activity: str = "idle"
    current_location: str = "home"
    activity_started: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
