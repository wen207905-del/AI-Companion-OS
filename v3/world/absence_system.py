"""
用户缺席追踪系统

Phase 2 核心新增模块：追踪用户 inactive 时长，缺席时间影响引擎权重。
缺席越久 → loneliness 压力越大 → 自主行为概率越高。

缺席阶段：
    early   (0-30min)   → neutral
    short   (30-120min) → miss_you
    medium  (2-6h)      → lonely + worried
    long    (6-24h)     → sad + memory_recall
    extreme (24h+)      → extreme_lonely + diary
"""

import time
from ..db import V3Database
from ..config import ABSENCE_STAGES, ABSENCE_FACTOR_BONUS


class AbsenceSystem:
    """用户缺席追踪系统。

    每次用户互动后调用 mark_interaction() 重置计时器；
    每 tick 调用 get_absence_status() 获取当前缺席状态。
    """

    def __init__(self, db: V3Database = None):
        self.db = db or V3Database()
        self._last_interaction_time: float = time.time()

    def mark_interaction(self):
        """用户互动时调用，重置缺席计时器。"""
        self._last_interaction_time = time.time()

    def get_inactive_minutes(self) -> int:
        """获取用户不活跃分钟数。"""
        return int((time.time() - self._last_interaction_time) / 60)

    def get_inactive_seconds(self) -> float:
        """获取用户不活跃秒数。"""
        return time.time() - self._last_interaction_time

    def get_absence_stage(self) -> dict:
        """获取当前缺席阶段信息。

        Returns:
            {"stage","label","inactive_minutes","effect"}
        """
        inactive_minutes = self.get_inactive_minutes()
        for stage_name, stage_def in ABSENCE_STAGES.items():
            if stage_def["min_minutes"] <= inactive_minutes < stage_def["max_minutes"]:
                return {
                    "stage": stage_name,
                    "label": stage_def["label"],
                    "inactive_minutes": inactive_minutes,
                    "effect": stage_def["effect"],
                }
        return {
            "stage": "extreme", "label": "极端缺席",
            "inactive_minutes": inactive_minutes,
            "effect": "extreme_lonely + diary",
        }

    def get_factor_bonus(self) -> dict:
        """获取缺席对各决策因子的加成权重。

        Returns:
            {lonely, initiative, attachment, sad, memory} 加成值
        """
        status = self.get_absence_stage()
        return ABSENCE_FACTOR_BONUS.get(status["stage"], {})

    def get_user_inactive_factor(self) -> float:
        """获取 user.inactive_time 因子值 [0,100]。

        1440 分钟（24h）映射到 100，线性 clamp。
        """
        inactive_minutes = self.get_inactive_minutes()
        return min(inactive_minutes / 1440.0 * 100.0, 100.0)

    def log_absence(self, tick_id: int):
        """将当前缺席状态写入数据库。"""
        status = self.get_absence_stage()
        self.db.insert_absence_log(
            tick_id=tick_id,
            inactive_minutes=status["inactive_minutes"],
            absence_stage=status["stage"],
            effect_summary=status["effect"],
        )

    def get_night_factor(self, time_period: str) -> float:
        """计算 world.night_factor [0,100]。

        夜晚时间段分值更高 → 角色更倾向主动联系。
        """
        night_map = {
            "early_morning": 60, "morning": 10, "noon": 15,
            "afternoon": 20, "evening": 50, "night": 80, "late_night": 95,
        }
        return night_map.get(time_period, 20)

    def get_absence_modifier_for_pressure(self) -> float:
        """获取情绪压力系统的缺席加速系数。

        Returns:
            加速系数 (≥1.0)
        """
        stage = self.get_absence_stage()["stage"]
        modifier_map = {
            "early": 1.0, "short": 1.5, "medium": 2.5, "long": 4.0, "extreme": 6.0,
        }
        return modifier_map.get(stage, 1.0)
