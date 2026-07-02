"""
World Engine 模块 — V3 的世界系统

Phase 1: 时间系统、天气系统、世界引擎和主循环
Phase 2: 情绪压力系统、缺席追踪系统
"""

from .world_state import WorldState, Weather, Environment, CharacterActivityState
from .time_engine import TimeEngine
from .weather_engine import WeatherEngine
from .world_engine import WorldEngine
from .world_tick import WorldTick, start_world

# Phase 2 子系统（可能不存在时容错导入）
try:
    from .mood_pressure import MoodPressureSystem
except ImportError:
    MoodPressureSystem = None
try:
    from .absence_system import AbsenceSystem
except ImportError:
    AbsenceSystem = None

__all__ = [
    "WorldState",
    "Weather",
    "Environment",
    "CharacterActivityState",
    "TimeEngine",
    "WeatherEngine",
    "WorldEngine",
    "WorldTick",
    "start_world",
    "MoodPressureSystem",
    "AbsenceSystem",
]
