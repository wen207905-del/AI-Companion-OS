"""
Emotion Dynamics Engine — 连续情绪引擎（V4 升级）

替代旧的 mood_pressure.py 的单一情绪压力模式。
实现情绪连续变化公式：

  emotion_now = base + world_bias + memory_trigger
               + relationship_bias + user_impact - natural_decay

10种情绪维度：
  happy / sad / angry / lonely / jealous / sleepy / calm / excited / shy / miss_user

4种情绪压力：
  loneliness_pressure / jealousy_pressure / unspoken_words_pressure / attachment_pressure

特性：
  - 情绪自然衰减（每tick衰减一定比例）
  - 事件冲击（用户行为产生瞬时偏移，缓慢恢复）
  - 世界状态影响（深夜→sleepy+lonely，下雨→calm+nostalgic）
"""

import math
import random
from typing import Optional


# ── 情绪维度定义 ──
EMOTION_DIMENSIONS = [
    "happy", "sad", "angry", "lonely", "jealous",
    "sleepy", "calm", "excited", "shy", "miss_user",
]

# ── 情绪压力类型 ──
PRESSURE_TYPES = [
    "loneliness_pressure",
    "jealousy_pressure",
    "unspoken_words_pressure",
    "attachment_pressure",
]

# ── 自然衰减率（每 tick 衰减比例） ──
NATURAL_DECAY = {
    "happy":      0.03,
    "sad":        0.02,
    "angry":      0.04,
    "lonely":     0.01,   # 孤独感衰减慢
    "jealous":    0.04,
    "sleepy":     0.08,   # 睡意消散快
    "calm":       0.02,
    "excited":    0.06,
    "shy":        0.03,
    "miss_user":  0.01,   # 思念衰减慢
}

# ── 世界状态影响映射 ──
WORLD_EMOTION_BIAS = {
    "late_night": {"sleepy": 15, "lonely": 10, "calm": 5},
    "night":      {"sleepy": 10, "lonely": 5, "calm": 5},
    "morning":    {"sleepy": -5, "happy": 5, "excited": 3},
    "afternoon":  {"happy": 3, "calm": 3},
    "evening":    {"calm": 5, "lonely": 5, "miss_user": 5},

    "rainy":      {"calm": 8, "lonely": 6, "sad": 3},
    "sunny":      {"happy": 8, "excited": 5},
    "cloudy":     {"calm": 5, "sad": 2},
    "snowy":      {"calm": 10, "lonely": 8, "shy": 3},
}

# ── 用户行为冲击（瞬时情绪偏移） ──
USER_ACTION_IMPACT = {
    "user_sent_message":      {"lonely": -10, "happy": 5, "miss_user": -5},
    "user_compliment":        {"happy": 15, "shy": 10, "lonely": -8},
    "user_cold_response":     {"sad": 10, "lonely": 8, "angry": 5},
    "user_left_6h":           {"lonely": 10, "miss_user": 8, "sad": 3},
    "user_left_24h":          {"lonely": 20, "sad": 10, "angry": 5, "miss_user": 15},
    "user_left_72h":          {"lonely": 30, "sad": 20, "angry": 15, "miss_user": 25},
    "user_returned_warm":     {"happy": 15, "lonely": -12, "miss_user": -10},
    "user_mentioned_memory":  {"happy": 10, "calm": 5, "shy": 5},
    "festival_event":         {"happy": 12, "excited": 8, "lonely": -5},
}


class EmotionDynamics:
    """连续情绪引擎 — 每次 tick 调用 update() 更新情绪。

    支持世界影响、事件冲击、自然衰减三层叠加。
    """

    def __init__(self, character_id: str, base_emotion: dict = None):
        self.character_id = character_id
        self.db = None  # 外部注入

        # 基础情绪：每个角色可以有不同基线
        self.base = base_emotion or {
            "happy": 50, "sad": 5, "angry": 0, "lonely": 20, "jealous": 0,
            "sleepy": 10, "calm": 60, "excited": 10, "shy": 20, "miss_user": 10,
        }

        # 当前情绪（0-100 标定）
        self.current = dict(self.base)

        # 情绪压力
        self.pressure = {
            "loneliness_pressure": 0.0,
            "jealousy_pressure": 0.0,
            "unspoken_words_pressure": 0.0,
            "attachment_pressure": 20.0,
        }

        # 瞬时冲击缓冲（逐步消散）
        self._impact_buffer: dict = {k: 0.0 for k in EMOTION_DIMENSIONS}

        self._clamp = lambda v: max(0.0, min(100.0, v))

    # ── 主更新 ──

    def update(self, world_state=None, memory_trigger: dict = None,
               relationship_state: dict = None, user_impact: str = None,
               absence_hours: float = 0) -> dict:
        """每 tick 调用一次，更新所有情绪维度。

        Returns:
            {emotion_deltas, current_emotions, pressures}
        """
        deltas = {k: 0.0 for k in EMOTION_DIMENSIONS}

        # 1. 自然衰减
        for dim in EMOTION_DIMENSIONS:
            decay = self.current[dim] * NATURAL_DECAY[dim]
            # 不能降到 base 以下太远
            decay = min(decay, max(0, self.current[dim] - self.base[dim] * 0.5))
            self.current[dim] = self._clamp(self.current[dim] - decay)
            deltas[dim] -= decay

        # 2. 世界偏差
        if world_state:
            tp = getattr(world_state, "time_period", None)
            weather = getattr(world_state, "weather", None)
            weather_type = weather.type if weather and hasattr(weather, "type") else None

            for bias_source in [tp, weather_type]:
                if bias_source and bias_source in WORLD_EMOTION_BIAS:
                    for dim, val in WORLD_EMOTION_BIAS[bias_source].items():
                        self.current[dim] = self._clamp(self.current[dim] + val)
                        deltas[dim] += val

        # 3. 记忆触发偏差
        if memory_trigger:
            for dim, val in memory_trigger.items():
                self.current[dim] = self._clamp(self.current[dim] + val)
                deltas[dim] += val

        # 4. 关系偏差
        if relationship_state:
            attachment = relationship_state.get("attachment", 0)
            trust = relationship_state.get("trust", 0)
            # 高亲密度 → 降低孤独感、增加想念
            if attachment > 70:
                deltas["lonely"] -= 5
                deltas["miss_user"] += 3
                self.current["lonely"] = self._clamp(self.current["lonely"] - 5)
                self.current["miss_user"] = self._clamp(self.current["miss_user"] + 3)
            if trust < 30:
                deltas["sad"] += 3
                deltas["angry"] += 2
                self.current["sad"] = self._clamp(self.current["sad"] + 3)
                self.current["angry"] = self._clamp(self.current["angry"] + 2)

        # 5. 用户行为冲击
        if user_impact and user_impact in USER_ACTION_IMPACT:
            impact = USER_ACTION_IMPACT[user_impact]
            for dim, val in impact.items():
                self._impact_buffer[dim] += val
                self.current[dim] = self._clamp(self.current[dim] + val)
                deltas[dim] += val

        # 6. 缺席时长影响
        if absence_hours >= 6:
            self._apply_absence_impact(absence_hours, deltas)

        # 7. 冲击缓冲逐渐消散（每次tick释放25%）
        for dim in EMOTION_DIMENSIONS:
            if abs(self._impact_buffer[dim]) > 0.1:
                release = self._impact_buffer[dim] * 0.25
                self._impact_buffer[dim] -= release

        # 8. 更新情绪压力
        self._update_pressures(absence_hours)

        return {
            "emotion_deltas": deltas,
            "current_emotions": dict(self.current),
            "pressures": dict(self.pressure),
        }

    def _apply_absence_impact(self, hours: float, deltas: dict):
        """根据缺席时长施加情绪影响。"""
        if hours >= 72:
            impact_key = "user_left_72h"
        elif hours >= 24:
            impact_key = "user_left_24h"
        else:
            impact_key = "user_left_6h"

        if impact_key in USER_ACTION_IMPACT:
            for dim, val in USER_ACTION_IMPACT[impact_key].items():
                # 不在短时间内重复施加相同冲击
                self.current[dim] = self._clamp(self.current[dim] + val * 0.3)
                deltas[dim] += val * 0.3

    def _update_pressures(self, absence_hours: float):
        """更新情绪压力值。"""
        # 孤独压力 = 当前孤独感 + 缺席时长加权
        self.pressure["loneliness_pressure"] = self._clamp(
            self.current["lonely"] * 0.3 + min(absence_hours, 72) * 0.8)

        # 嫉妒压力（与关系状态相关，此处用近似值）
        self.pressure["jealousy_pressure"] = self._clamp(
            self.current["jealous"] * 0.5)

        # 未说出口的话压力
        self.pressure["unspoken_words_pressure"] = self._clamp(
            self.current["miss_user"] * 0.4 + self.current["lonely"] * 0.2)

        # 依恋压力
        self.pressure["attachment_pressure"] = self._clamp(
            self.current["miss_user"] * 0.6 + self.current["lonely"] * 0.2)

    # ── 查询接口 ──

    def get_emotion(self, dim: str = None) -> float:
        """获取指定情绪维度值，不传返回全部。"""
        if dim:
            return self.current.get(dim, 0)
        return dict(self.current)

    def get_dominant_emotion(self) -> str:
        """返回当前主导情绪。"""
        if not self.current:
            return "calm"
        return max(self.current, key=self.current.get)

    def get_pressure(self, ptype: str = None) -> float:
        """获取指定压力类型。"""
        if ptype:
            return self.pressure.get(ptype, 0)
        return dict(self.pressure)

    def get_emotion_summary(self) -> dict:
        """获取情绪摘要（供 prompt 注入）。"""
        dominant = self.get_dominant_emotion()
        top3 = sorted(self.current.items(), key=lambda x: x[1], reverse=True)[:3]
        return {
            "dominant": dominant,
            "top_emotions": dict(top3),
            "pressures": {k: round(v, 1) for k, v in self.pressure.items() if v > 10},
        }

    # ── 持久化 ──

    def snapshot(self) -> dict:
        """生成情绪快照（用于数据库写入或恢复）。"""
        return {
            "character_id": self.character_id,
            "emotions": dict(self.current),
            "pressures": dict(self.pressure),
            "dominant": self.get_dominant_emotion(),
        }

    def restore(self, snapshot: dict):
        """从快照恢复情绪状态。"""
        if "emotions" in snapshot:
            self.current.update(snapshot["emotions"])
        if "pressures" in snapshot:
            self.pressure.update(snapshot["pressures"])
