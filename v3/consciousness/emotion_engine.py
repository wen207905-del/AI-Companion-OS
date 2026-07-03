"""
V4 Emotion Engine — 情绪融合引擎

替代 v3/brain/emotion_dynamics.py，提供完整的连续情绪计算。
10 维度 + 4 种压力 + 连续变化公式 + 压力阈值触发自主行为。
"""

import random
from typing import Optional

# ── 10 种情绪维度 ──
EMOTION_DIMENSIONS = [
    "happy", "sad", "angry", "lonely", "jealous",
    "sleepy", "calm", "excited", "shy", "miss_user",
]

# ── 4 种情绪压力 ──
PRESSURE_TYPES = [
    "loneliness_pressure",
    "jealousy_pressure",
    "unspoken_words_pressure",
    "attachment_pressure",
]

# ── 压力阈值 ──
PRESSURE_THRESHOLD_HIGH = 70  # 高于此值触发主动行为
PRESSURE_THRESHOLD_CRITICAL = 90  # 高于此值触发紧急行为


class EmotionEngine:
    """情绪融合引擎 — 连续情绪变化。

    公式：
        emotion_now = base + world_bias + memory_trigger
                     + relationship_bias + user_impact - natural_decay
    """

    def __init__(self, db=None, event_bus=None):
        self.db = db
        self.event_bus = event_bus

        # 衰减率：每 tick 衰减当前值的百分比
        self.decay_rates = {
            "happy": 0.02, "sad": 0.03, "angry": 0.05,
            "lonely": 0.01, "jealous": 0.03, "sleepy": 0.04,
            "calm": 0.02, "excited": 0.05, "shy": 0.03,
            "miss_user": 0.01,
        }

        # 基础值（0-100）
        self.default_base = {
            "happy": 50, "sad": 20, "angry": 10, "lonely": 30,
            "jealous": 5, "sleepy": 20, "calm": 60, "excited": 30,
            "shy": 15, "miss_user": 20,
        }

        # 每个角色的当前情绪缓存
        self._emotions: dict = {}     # char_id → {emotion: value}
        self._pressures: dict = {}    # char_id → {pressure: value}

    def get_emotions(self, character_id: str) -> dict:
        """获取角色当前情绪快照。"""
        if character_id not in self._emotions:
            self._emotions[character_id] = dict(self.default_base)
        return dict(self._emotions[character_id])

    def get_pressures(self, character_id: str) -> dict:
        """获取角色当前情绪压力。"""
        if character_id not in self._pressures:
            self._pressures[character_id] = {
                "loneliness_pressure": 20,
                "jealousy_pressure": 5,
                "unspoken_words_pressure": 15,
                "attachment_pressure": 30,
            }
        return dict(self._pressures[character_id])

    def get_dominant_emotion(self, character_id: str) -> str:
        """获取主导情绪。"""
        emos = self.get_emotions(character_id)
        return max(emos, key=emos.get) if emos else "calm"

    # ── 更新方法 ──

    def update(self, character_id: str,
               world_bias: dict = None,
               memory_trigger: dict = None,
               relationship_bias: dict = None,
               user_impact: dict = None) -> dict:
        """更新单个角色的情绪。

        Returns:
            {emotion: new_value, ..., "_dominant": str, "_pressures": {...}}
        """
        old = self.get_emotions(character_id)
        p_old = self.get_pressures(character_id)

        # 1. 自然衰减
        new = {}
        for dim in EMOTION_DIMENSIONS:
            decay = old[dim] * self.decay_rates.get(dim, 0.02)
            new[dim] = old[dim] - decay

        # 2. 世界偏差
        if world_bias:
            for dim, bias in world_bias.items():
                if dim in new:
                    new[dim] += bias

        # 3. 记忆触发
        if memory_trigger:
            for dim, trigger in memory_trigger.items():
                if dim in new:
                    new[dim] += trigger

        # 4. 关系偏差
        if relationship_bias:
            for dim, bias in relationship_bias.items():
                if dim in new:
                    new[dim] += bias

        # 5. 用户影响
        if user_impact:
            for dim, impact in user_impact.items():
                if dim in new:
                    new[dim] += impact

        # 6. 钳位 0-100
        for dim in new:
            new[dim] = max(0.0, min(100.0, round(new[dim], 1)))

        # 7. 更新压力
        new_pressures = dict(p_old)
        new_pressures["loneliness_pressure"] = round(
            (new["lonely"] + new["miss_user"] * 1.5 + (100 - new["happy"]) * 0.3) / 3, 1
        )
        new_pressures["jealousy_pressure"] = round(
            new["jealous"] * 2.0 + (100 - new["calm"]) * 0.2, 1
        )
        new_pressures["unspoken_words_pressure"] = round(
            new["miss_user"] * 1.2 + new["shy"] * 0.5, 1
        )
        new_pressures["attachment_pressure"] = round(
            new["miss_user"] * 1.5 + (100 - new["calm"]) * 0.3, 1
        )

        self._emotions[character_id] = new
        self._pressures[character_id] = new_pressures

        # 8. 事件发布
        dominant = max(new, key=new.get)
        if self.event_bus:
            self.event_bus.publish("emotion_change", {
                "character_id": character_id,
                "dominant": dominant,
                "delta": {dim: round(new[dim] - old[dim], 1) for dim in EMOTION_DIMENSIONS},
            })

        # 9. 持久化快照
        if self.db:
            try:
                self.db.insert_emotion_snapshot(
                    character_id=character_id,
                    tick_id=0,  # 由 LifeKernel 覆盖
                    emotions=new,
                    pressures=new_pressures,
                    dominant=dominant,
                )
            except Exception:
                pass

        return {"emotions": new, "_dominant": dominant, "_pressures": new_pressures}

    def update_all(self, character_ids: list = None) -> dict:
        """批量更新所有角色的情绪。"""
        if not character_ids and self.db:
            try:
                chars = self.db.get_all_characters()
                character_ids = [c.get("character_id") if isinstance(c, dict) else c[0]
                                 for c in (chars or [])]
            except Exception:
                character_ids = []

        results = {}
        for cid in (character_ids or []):
            results[cid] = self.update(character_id=cid)
        return {"updated": len(results), "details": results}

    # ── 压力检查 ──

    def check_pressure_triggers(self, character_id: str) -> list:
        """检查压力是否触发自主行为。

        Returns:
            [{"pressure": str, "level": float, "action_hint": str}, ...]
        """
        pressures = self.get_pressures(character_id)
        triggers = []

        if pressures.get("loneliness_pressure", 0) >= PRESSURE_THRESHOLD_HIGH:
            triggers.append({
                "pressure": "loneliness_pressure",
                "level": pressures["loneliness_pressure"],
                "action_hint": "send_message" if pressures["loneliness_pressure"] < PRESSURE_THRESHOLD_CRITICAL else "private_message_user",
            })

        if pressures.get("unspoken_words_pressure", 0) >= PRESSURE_THRESHOLD_HIGH:
            triggers.append({
                "pressure": "unspoken_words_pressure",
                "level": pressures["unspoken_words_pressure"],
                "action_hint": "write_diary",
            })

        if pressures.get("jealousy_pressure", 0) >= PRESSURE_THRESHOLD_HIGH:
            triggers.append({
                "pressure": "jealousy_pressure",
                "level": pressures["jealousy_pressure"],
                "action_hint": "send_message",
            })

        return triggers
