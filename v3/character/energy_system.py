"""
Energy System — 精力系统

随时间恢复和消耗，影响回复长度和语气。
高精力：回复长、热情
低精力：回复短、慵懒
"""


class EnergySystem:
    """精力系统 — 影响回复质量和角色行为选择。"""

    MAX_ENERGY = 100.0
    MIN_ENERGY = 0.0

    # 活动精力消耗（每 tick）
    ACTIVITY_COST = {
        "sleeping":      -5.0,   # 睡觉回复精力
        "waking_up":     2.0,
        "working":       8.0,
        "studying":      6.0,
        "exercising":    10.0,
        "chatting":      3.0,
        "reading":       2.0,
        "thinking":      1.0,
        "idle":          0.5,
    }

    # 时间段精力自然回复
    TIME_RECOVERY = {
        "late_night": -2.0,   # 深夜持续消耗
        "night": -1.0,
        "morning": 5.0,
        "afternoon": 1.0,
        "evening": -0.5,
    }

    def __init__(self):
        self.energy = self.MAX_ENERGY

    def update(self, activity: str = None, time_period: str = None):
        """每 tick 更新精力。

        Args:
            activity: 当前活动
            time_period: 时间段（late_night/night/morning/afternoon/evening）
        """
        # 活动消耗/回复
        if activity and activity in self.ACTIVITY_COST:
            self.energy -= self.ACTIVITY_COST[activity]

        # 时间段自然回复
        if time_period and time_period in self.TIME_RECOVERY:
            self.energy += self.TIME_RECOVERY[time_period]

        # 睡觉时额外回复
        if activity == "sleeping":
            self.energy = min(self.MAX_ENERGY, self.energy + 8.0)

        self.energy = max(self.MIN_ENERGY, min(self.MAX_ENERGY, self.energy))

    def get_energy_level(self) -> str:
        """获取精力等级描述。"""
        if self.energy >= 80:
            return "energetic"
        elif self.energy >= 50:
            return "normal"
        elif self.energy >= 20:
            return "tired"
        return "exhausted"

    def get_reply_multiplier(self) -> float:
        """获取回复长度乘数。

        低精力时回复更短。
        """
        if self.energy >= 80:
            return 1.0
        elif self.energy >= 50:
            return 0.8
        elif self.energy >= 20:
            return 0.5
        return 0.3

    def get_status(self) -> dict:
        return {
            "energy": round(self.energy, 1),
            "level": self.get_energy_level(),
            "reply_multiplier": self.get_reply_multiplier(),
        }
