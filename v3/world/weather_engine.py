"""
天气系统

负责天气类型管理、天气变化模拟、天气对情绪和行为的影响计算。
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from ..config import (
    WEATHER_TYPES,
    WEATHER_TRANSITION_PROBABILITY,
    WEATHER_TRANSITION_WEIGHTS,
    WEATHER_EMOTION_EFFECTS,
    WEATHER_SELFIE_BIAS,
    SEASONS,
)


class WeatherEngine:
    """天气引擎 — 管理天气状态的变化和对角色的影响。

    天气变化基于概率模型：每次 tick 有一定概率发生天气切换，
    切换目标由当前天气类型的转移权重决定。
    """

    def __init__(self, initial_weather: str = "sunny", season: str = "summer"):
        """
        Args:
            initial_weather: 初始天气类型
            season: 当前季节
        """
        self.current_weather = initial_weather
        self.season = season
        self._weather_history: list = []  # 记录天气变化历史
        self._last_change_time: Optional[datetime] = None

    def set_season(self, season: str):
        """更新当前季节，可能影响天气切换倾向。"""
        self.season = season

    def get_current_weather(self) -> dict:
        """获取当前天气状态字典。

        Returns:
            包含 type / temperature / humidity / wind_level / mood_bias / label 的字典
        """
        weather_def = WEATHER_TYPES.get(self.current_weather, WEATHER_TYPES["sunny"])
        temp_range = weather_def["temperature_range"]
        season_info = SEASONS.get(self.season, SEASONS["summer"])

        # 基于季节偏移计算实际温度
        base_offset = season_info["base_temperature"] - 20  # 以 20°C 为基准
        temperature = random.uniform(*temp_range) + base_offset
        temperature = round(temperature, 1)

        humidity = self._generate_humidity()
        wind_level = self._generate_wind_level()

        return {
            "type": self.current_weather,
            "temperature": temperature,
            "humidity": humidity,
            "wind_level": wind_level,
            "mood_bias": weather_def["mood_bias"],
            "label": weather_def["label"],
        }

    def tick(self) -> dict:
        """每个 tick 调用一次，可能触发天气变化。

        Returns:
            更新后的天气状态字典
        """
        if random.random() < WEATHER_TRANSITION_PROBABILITY:
            self._transition_weather()

        return self.get_current_weather()

    def get_emotion_effects(self) -> dict:
        """获取当前天气对角色情绪的数值影响。

        Returns:
            情绪影响字典，键为情绪名，值为影响数值
        """
        return WEATHER_EMOTION_EFFECTS.get(self.current_weather, {})

    def get_selfie_probability_bias(self) -> float:
        """获取当前天气对自拍概率的修正值。

        Returns:
            概率修正值（-0.20 到 +0.20）
        """
        return WEATHER_SELFIE_BIAS.get(self.current_weather, 0.0)

    def get_chat_desire_bias(self) -> int:
        """获取当前天气对聊天欲望的加成。

        Returns:
            聊天欲望加成数值
        """
        effects = self.get_emotion_effects()
        return effects.get("desire_to_chat", 0)

    def _transition_weather(self):
        """根据转移权重表执行天气切换。"""
        weights = WEATHER_TRANSITION_WEIGHTS.get(self.current_weather, {})
        if not weights:
            return

        weather_types = list(weights.keys())
        weight_values = list(weights.values())

        new_weather = random.choices(weather_types, weights=weight_values, k=1)[0]
        self._weather_history.append({
            "from": self.current_weather,
            "to": new_weather,
        })
        self._last_change_time = datetime.now()
        self.current_weather = new_weather

        # 保持历史不超过 100 条
        if len(self._weather_history) > 100:
            self._weather_history = self._weather_history[-50:]

    def _generate_humidity(self) -> float:
        """根据天气类型生成合理的湿度值。"""
        base_map = {
            "sunny": (30, 55),
            "cloudy": (45, 65),
            "overcast": (55, 75),
            "rainy": (70, 90),
            "heavy_rain": (80, 98),
            "stormy": (75, 95),
            "foggy": (65, 85),
            "snowy": (50, 75),
        }
        r = base_map.get(self.current_weather, (40, 60))
        return round(random.uniform(*r), 1)

    def _generate_wind_level(self) -> int:
        """根据天气类型生成合理的风力等级。"""
        base_map = {
            "sunny": (0, 3),
            "cloudy": (1, 4),
            "overcast": (1, 3),
            "rainy": (1, 5),
            "heavy_rain": (2, 7),
            "stormy": (5, 11),
            "foggy": (0, 2),
            "snowy": (1, 5),
        }
        r = base_map.get(self.current_weather, (0, 3))
        return random.randint(*r)
