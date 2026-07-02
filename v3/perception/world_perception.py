"""
World Perception — 世界状态感知

将世界客观状态（天气、时间、气氛）转换为角色的内部表示。
不同角色对同一世界状态的感知可以不同。
"""


class WorldPerception:
    """世界状态感知器。"""

    def perceive(self, world_state) -> dict:
        """将世界状态转换为内部感知表示。

        Returns:
            {
                time_period: str,
                weather: str,
                temperature: float,
                season: str,
                atmosphere: str,
                mood_bias: str,
                emotional_impact: {dim: delta, ...},
            }
        """
        # 获取世界状态属性
        tp = getattr(world_state, "time_period", None) or "day"
        weather = getattr(world_state, "weather", None)
        weather_type = weather.type if hasattr(weather, "type") else (
            weather if isinstance(weather, str) else "clear"
        )
        temperature = getattr(world_state, "temperature", None) or 20
        season = getattr(world_state, "season", None) or "summer"
        atmosphere = getattr(world_state, "atmosphere", None) or "normal"

        result = {
            "time_period": tp,
            "weather": str(weather_type),
            "temperature": temperature,
            "season": season,
            "atmosphere": atmosphere,
            "mood_bias": self._get_mood_bias(tp, weather_type),
            "emotional_impact": self._calculate_impact(tp, weather_type),
        }

        return result

    def _get_mood_bias(self, time_period: str, weather: str) -> str:
        """计算世界状态的情绪偏差倾向。"""
        biases = []

        if time_period in ("late_night",):
            biases.append("nostalgic")
        elif time_period in ("morning",):
            biases.append("fresh")
        elif time_period in ("evening",):
            biases.append("calm")

        if weather == "rainy":
            biases.append("melancholic")
        elif weather == "sunny":
            biases.append("energetic")
        elif weather == "snowy":
            biases.append("romantic")

        return ", ".join(biases) if biases else "neutral"

    def _calculate_impact(self, time_period: str, weather: str) -> dict:
        """计算世界状态的情绪影响。"""
        impact = {}

        # 时间段影响
        TIME_IMPACT = {
            "late_night": {"sleepy": 15, "lonely": 10},
            "night":      {"sleepy": 10, "lonely": 5},
            "morning":    {"sleepy": -5, "excited": 5},
            "evening":    {"calm": 5, "lonely": 3},
        }
        if time_period in TIME_IMPACT:
            impact.update(TIME_IMPACT[time_period])

        # 天气影响
        WEATHER_IMPACT = {
            "rainy":  {"calm": 8, "lonely": 6, "sad": 3},
            "sunny":  {"happy": 8, "excited": 5},
            "snowy":  {"calm": 10, "lonely": 5, "shy": 3},
            "cloudy": {"calm": 5, "sad": 2},
        }
        if weather in WEATHER_IMPACT:
            impact.update(WEATHER_IMPACT[weather])

        return impact
