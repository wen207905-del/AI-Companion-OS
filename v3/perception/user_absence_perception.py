"""
User Absence Perception — 用户缺席感知

检测用户缺席时长，计算情绪影响值。
缺席时间越长，情绪影响越大。
"""

from datetime import datetime, timedelta
from typing import Optional


class UserAbsencePerception:
    """用户缺席感知器。

    追踪用户最后在线时间，计算缺席时长和影响。
    """

    def __init__(self, db=None):
        self.db = db
        # 每个角色的最后交互时间（内存缓存，落库靠 db）
        self._last_interaction: dict = {}

    def check(self, character_id: str) -> dict:
        """检查用户缺席状态。

        Returns:
            {
                absent_hours: float,
                is_absent: bool,        # 是否缺席超过阈值
                absence_level: str,     # none / short / medium / long / extreme
                emotional_impact: {emotion_dim: delta, ...},
            }
        """
        now = datetime.now()
        last = self._last_interaction.get(character_id, now)
        delta = now - last
        hours = delta.total_seconds() / 3600.0

        # 缺席等级
        if hours < 0.5:
            level = "none"
        elif hours < 6:
            level = "short"
        elif hours < 24:
            level = "medium"
        elif hours < 72:
            level = "long"
        else:
            level = "extreme"

        # 情绪影响
        impact = self._calculate_impact(hours, level)

        return {
            "absent_hours": round(hours, 1),
            "is_absent": hours >= 0.5,
            "absence_level": level,
            "emotional_impact": impact,
        }

    def _calculate_impact(self, hours: float, level: str) -> dict:
        """根据缺席等级计算情绪影响。"""
        if level == "none":
            return {"lonely": 0, "miss_user": 0, "sad": 0}
        elif level == "short":
            return {"lonely": 5, "miss_user": 3, "sad": 1}
        elif level == "medium":
            factor = min(hours / 24, 1.0)
            return {
                "lonely": int(10 * factor),
                "miss_user": int(8 * factor),
                "sad": int(5 * factor),
            }
        elif level == "long":
            factor = min(hours / 72, 1.0)
            return {
                "lonely": int(20 * factor),
                "miss_user": int(15 * factor),
                "sad": int(10 * factor),
                "angry": int(5 * factor),
            }
        else:  # extreme
            return {
                "lonely": 30,
                "miss_user": 25,
                "sad": 20,
                "angry": 15,
            }

    def record_interaction(self, character_id: str):
        """记录用户交互时间。"""
        self._last_interaction[character_id] = datetime.now()

    def set_last_interaction(self, character_id: str, dt: datetime):
        """从数据库恢复最后交互时间。"""
        self._last_interaction[character_id] = dt
