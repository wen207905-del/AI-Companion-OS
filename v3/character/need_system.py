"""
Need System — 需求系统

管理角色的生理、社交、情感需求，影响行为优先级。
需求值越高 → 越倾向于选择满足该需求的行为。
"""

from typing import Optional


class NeedSystem:
    """需求系统 — 三维需求驱动行为选择。"""

    # 需求衰减/恢复率（每 tick）
    DECAY_RATES = {
        "physiological": 1.0,   # 生理需求自然增长（越久不满足越需要）
        "social": 0.8,          # 社交需求增长
        "emotional": 0.6,       # 情感需求增长
    }

    # 行为对需求的满足量
    SATISFACTION = {
        "sleeping":      {"physiological": 20, "social": 0,  "emotional": 5},
        "eating":        {"physiological": 25, "social": 0,  "emotional": 5},
        "socializing":   {"physiological": 0,  "social": 20, "emotional": 10},
        "being_with_user": {"physiological": 0,  "social": 30, "emotional": 25},
        "reading":       {"physiological": 0,  "social": 0,  "emotional": 10},
        "drawing":       {"physiological": 0,  "social": 0,  "emotional": 15},
        "thinking":      {"physiological": 0,  "social": 0,  "emotional": 5},
        "writing_diary": {"physiological": 0,  "social": 0,  "emotional": 20},
    }

    def __init__(self):
        self.needs = {
            "physiological": 0.0,   # 生理需求（饥饿/困倦）
            "social": 0.0,          # 社交需求
            "emotional": 0.0,       # 情感需求
        }

    def update(self, current_activity: str = None, user_present: bool = False):
        """每 tick 更新需求值。

        Args:
            current_activity: 当前活动
            user_present: 用户是否在线
        """
        # 需求自然增长
        for need_type, rate in self.DECAY_RATES.items():
            self.needs[need_type] = min(100, self.needs[need_type] + rate)

        # 活动满足需求
        if current_activity and current_activity in self.SATISFACTION:
            sat = self.SATISFACTION[current_activity]
            for need_type, val in sat.items():
                self.needs[need_type] = max(0, self.needs[need_type] - val)

        # 用户在时社交需求满足更快
        if user_present:
            self.needs["social"] = max(0, self.needs["social"] - 2)

    def get_priorities(self) -> dict:
        """获取需求优先级排序。"""
        return dict(sorted(self.needs.items(), key=lambda x: x[1], reverse=True))

    def get_highest_need(self) -> str:
        """获取当前最高需求类型。"""
        return max(self.needs, key=self.needs.get)

    def get_status(self) -> dict:
        return {k: round(v, 1) for k, v in self.needs.items()}
