"""
时间系统

负责时间段划分、时间推进和时间段判定。
驱动角色一天 24 小时的生活节奏。
"""

from datetime import datetime, time as dt_time
from typing import Optional, Tuple

from ..config import TIME_PERIODS


class TimeEngine:
    """时间引擎 — 管理虚拟世界的时间推进和时间段判定。

    支持两种模式：
    - 跟随系统时间（默认）
    - 加速模拟时间（通过 TIME_ACCELERATION_RATIO 控制）
    """

    def __init__(self, acceleration_ratio: float = 0):
        """
        Args:
            acceleration_ratio: 加速倍率，0 表示跟随系统时间。
        """
        self.acceleration_ratio = acceleration_ratio
        self._simulated_time: Optional[datetime] = None
        self._last_tick_time: Optional[datetime] = None

    def get_current_time(self) -> datetime:
        """获取当前虚拟世界时间。

        Returns:
            当前 datetime 对象
        """
        if self.acceleration_ratio == 0 or self._simulated_time is None:
            self._simulated_time = datetime.now()
        return self._simulated_time

    def advance_time(self, real_seconds: int) -> datetime:
        """推进虚拟时间。

        Args:
            real_seconds: 真实世界中经过的秒数

        Returns:
            推进后的 datetime 对象
        """
        if self._simulated_time is None:
            self._simulated_time = datetime.now()

        if self.acceleration_ratio > 0:
            simulated_seconds = real_seconds * self.acceleration_ratio
        else:
            simulated_seconds = real_seconds

        from datetime import timedelta
        self._simulated_time += timedelta(seconds=simulated_seconds)
        return self._simulated_time

    def get_time_period(self, dt: datetime = None) -> str:
        """根据时间判定当前所属时间段。

        Args:
            dt: 要判定的 datetime，默认使用当前虚拟时间

        Returns:
            时间段键名（如 morning / late_night）
        """
        if dt is None:
            dt = self.get_current_time()

        t = dt.time()

        for period_key, period_def in TIME_PERIODS.items():
            start = self._parse_time_str(period_def["start"])
            end = self._parse_time_str(period_def["end"])

            if self._is_time_in_range(t, start, end):
                return period_key

        return "morning"  # 默认回退

    def get_time_period_label(self, period_key: str) -> str:
        """获取时间段的中文标签。

        Args:
            period_key: 时间段键名

        Returns:
            中文标签（如"上午"、"深夜"）
        """
        info = TIME_PERIODS.get(period_key, {})
        return info.get("label", period_key)

    def get_day_of_week(self, dt: datetime = None) -> str:
        """获取星期几的英文名。

        Args:
            dt: datetime 对象

        Returns:
            星期英文名（Monday / Tuesday 等）
        """
        if dt is None:
            dt = self.get_current_time()
        return dt.strftime("%A")

    def get_season(self, dt: datetime = None) -> str:
        """根据月份判定季节。

        Args:
            dt: datetime 对象

        Returns:
            季节（spring / summer / autumn / winter）
        """
        if dt is None:
            dt = self.get_current_time()

        month = dt.month
        from ..config import SEASONS

        for season_key, season_def in SEASONS.items():
            if month in season_def["months"]:
                return season_key

        return "summer"

    def get_current_state_summary(self) -> dict:
        """获取当前时间的完整状态摘要。

        Returns:
            包含 datetime、day_of_week、time_period、season 的字典
        """
        now = self.get_current_time()
        period = self.get_time_period(now)
        return {
            "datetime": now.isoformat(),
            "day_of_week": self.get_day_of_week(now),
            "time_period": period,
            "time_period_label": self.get_time_period_label(period),
            "season": self.get_season(now),
            "hour": now.hour,
            "minute": now.minute,
        }

    @staticmethod
    def _parse_time_str(time_str: str) -> dt_time:
        """解析 HH:MM 格式的时间字符串为 time 对象。"""
        hour, minute = map(int, time_str.split(":"))
        return dt_time(hour, minute)

    @staticmethod
    def _is_time_in_range(t: dt_time, start: dt_time, end: dt_time) -> bool:
        """判断时间 t 是否在 [start, end] 范围内，支持跨午夜。"""
        if start <= end:
            return start <= t <= end
        else:
            # 跨午夜范围（如 22:00 - 04:59）
            return t >= start or t <= end
