"""
情绪压力累积系统

Phase 2 核心新增模块：情绪不会瞬时变化，而是随时间累积"压力"。
每 tick 压力增加，用户交互释放压力，压力超过阈值触发爆发。

数据流：
    世界 tick → 累积压力 → 检查阈值 → 写入数据库 → 供 Autonomy Engine 读取
"""

from ..db import V3Database
from ..config import (
    PRESSURE_ACCUMULATION_RATES,
    PRESSURE_RELEASE_ON_INTERACTION,
    PRESSURE_BURST_THRESHOLD,
)


class MoodPressureSystem:
    """情绪压力累积系统。

    每 tick 调用 update() 为所有角色累积情绪压力；
    用户互动时调用 release() 释放压力；
    压力超过阈值时触发 burst 事件，供 Autonomy Engine 作为高分因子。

    压力模型：
        pressure(t+1) = pressure(t) + rate * absence_modifier
        压力值域 [0, 100]
    """

    def __init__(self, db: V3Database = None):
        self.db = db or V3Database()
        self._pressure_cache: dict = {}  # {character_id: {emotion_type: value}}

    def load_pressures(self, character_id: str) -> dict:
        """从数据库加载角色当前所有情绪压力值。

        Returns:
            {emotion_type: pressure_value (0-100)}
        """
        if character_id not in self._pressure_cache:
            self._pressure_cache[character_id] = self.db.get_character_pressures(character_id)
        return self._pressure_cache.get(character_id, {})

    def update(self, character_id: str, tick_id: int,
               absence_modifier: float = 1.0) -> dict:
        """每个 tick 更新角色的情绪压力。

        Args:
            character_id: 角色 ID
            tick_id: 当前 tick ID
            absence_modifier: 缺席加速系数（≥1.0）

        Returns:
            {emotion_type: {"before","after","burst","delta"}}
        """
        pressures = self.load_pressures(character_id)
        results = {}

        for emotion_type, rate in PRESSURE_ACCUMULATION_RATES.items():
            before = pressures.get(emotion_type, 0.0)
            delta = rate * absence_modifier
            after = min(before + delta, 100.0)
            burst = after >= PRESSURE_BURST_THRESHOLD.get(emotion_type, 80)

            pressures[emotion_type] = after
            self.db.insert_mood_pressure_log(
                tick_id=tick_id, character_id=character_id,
                emotion_type=emotion_type, pressure_before=before,
                pressure_after=after, delta=delta, trigger="tick",
            )
            results[emotion_type] = {"before": before, "after": after, "delta": delta, "burst": burst}

        self._pressure_cache[character_id] = pressures
        return results

    def release(self, character_id: str, tick_id: int,
                interaction_type: str = "message") -> dict:
        """用户互动时释放情绪压力。

        Returns:
            {emotion_type: {"before","after","delta"}}
        """
        pressures = self.load_pressures(character_id)
        results = {}
        for emotion_type, release_ratio in PRESSURE_RELEASE_ON_INTERACTION.items():
            before = pressures.get(emotion_type, 0.0)
            delta = before * release_ratio  # 负值
            after = max(before + delta, 0.0)
            pressures[emotion_type] = after
            self.db.insert_mood_pressure_log(
                tick_id=tick_id, character_id=character_id,
                emotion_type=emotion_type, pressure_before=before,
                pressure_after=after, delta=delta,
                trigger=f"interaction:{interaction_type}",
            )
            results[emotion_type] = {"before": before, "after": after, "delta": delta}
        self._pressure_cache[character_id] = pressures
        return results

    def get_pressure_for_autonomy(self, character_id: str) -> dict:
        """返回压力值供 Autonomy Engine 评分使用。

        Returns:
            {emotion_type: pressure (0-100)}
        """
        return self.load_pressures(character_id)

    def check_burst(self, character_id: str) -> list:
        """检查是否有情绪压力超过爆发阈值。

        Returns:
            超过阈值的情绪类型列表
        """
        pressures = self.load_pressures(character_id)
        burst_emotions = []
        for etype, val in pressures.items():
            threshold = PRESSURE_BURST_THRESHOLD.get(etype, 80)
            if val >= threshold:
                burst_emotions.append(etype)
        return burst_emotions
