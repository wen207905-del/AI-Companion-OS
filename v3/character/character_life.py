"""
Character Life Engine — 角色生活状态管理

每个角色不是 24 小时等你，而是有自己的生活。
管理：当前活动、位置、精力、社交欲望、孤独压力、最后交互时间。
根据时间段自动推荐活动。
"""

from datetime import datetime, time as dt_time
from typing import Optional
from enum import Enum


class ActivityType(Enum):
    SLEEPING = "sleeping"
    WAKING_UP = "waking_up"
    BREAKFAST = "breakfast"
    WORKING = "working"
    STUDYING = "studying"
    DRAWING = "drawing"
    COOKING = "cooking"
    WATCHING_MOVIE = "watching_movie"
    TAKING_BATH = "taking_bath"
    THINKING = "thinking"
    MISSING_USER = "missing_user"
    WRITING_DIARY = "writing_diary"
    READING = "reading"
    SHOPPING = "shopping"
    EXERCISING = "exercising"
    IDLE = "idle"


# 时间→活动推荐映射
TIME_ACTIVITY_MAP = {
    (0, 5):   [ActivityType.SLEEPING],
    (6, 7):   [ActivityType.WAKING_UP, ActivityType.BREAKFAST],
    (8, 11):  [ActivityType.WORKING, ActivityType.STUDYING],
    (12, 13): [ActivityType.BREAKFAST, ActivityType.COOKING],
    (14, 17): [ActivityType.WORKING, ActivityType.STUDYING, ActivityType.DRAWING, ActivityType.READING],
    (18, 19): [ActivityType.COOKING, ActivityType.EXERCISING, ActivityType.SHOPPING],
    (20, 22): [ActivityType.WATCHING_MOVIE, ActivityType.READING, ActivityType.TAKING_BATH, ActivityType.THINKING],
    (23, 23): [ActivityType.THINKING, ActivityType.WRITING_DIARY, ActivityType.MISSING_USER],
}


class CharacterLife:
    """角色生活状态管理器。"""

    def __init__(self, character_id: str):
        self.character_id = character_id
        self.current_activity: ActivityType = ActivityType.IDLE
        self.location: str = "home"
        self.energy: float = 100.0
        self.social_desire: float = 50.0
        self.loneliness_pressure: float = 0.0
        self.last_user_interaction: Optional[datetime] = None
        self.last_activity_change: datetime = datetime.now()
        self.activity_history: list = []

    def update(self, game_time: datetime, absence_hours: float = 0):
        """每 tick 更新生活状态。

        Args:
            game_time: 游戏内时间
            absence_hours: 用户缺席时长（小时）
        """
        hour = game_time.hour
        now = game_time

        # 1. 推荐活动
        recommended = self._recommend_activity(hour)

        # 2. 如果当前活动不合理或在推荐列表中 -> 切换
        if self.current_activity not in recommended:
            # 如果已经 30+ 分钟没换活动了
            if (now - self.last_activity_change).total_seconds() > 1800:
                self.current_activity = recommended[0]
                self.last_activity_change = now
                self.activity_history.append({
                    "time": now.isoformat(),
                    "activity": self.current_activity.value,
                })

        # 3. 更新内部数值
        self.loneliness_pressure = min(100, absence_hours * 2.0)

        if absence_hours > 6:
            self.social_desire = min(100, self.social_desire + absence_hours * 1.5)
        else:
            self.social_desire = max(0, self.social_desire - 1)

    def _recommend_activity(self, hour: int) -> list:
        """根据时间段推荐活动。"""
        for (start, end), activities in TIME_ACTIVITY_MAP.items():
            if start <= hour <= end:
                return activities
        return [ActivityType.IDLE]

    def get_status(self) -> dict:
        """获取当前状态快照。"""
        return {
            "character_id": self.character_id,
            "current_activity": self.current_activity.value,
            "location": self.location,
            "energy": round(self.energy, 1),
            "social_desire": round(self.social_desire, 1),
            "loneliness_pressure": round(self.loneliness_pressure, 1),
            "last_user_interaction": (
                self.last_user_interaction.isoformat() if self.last_user_interaction else None
            ),
            "minutes_since_activity_change": int(
                (datetime.now() - self.last_activity_change).total_seconds() / 60
            ),
        }

    def set_activity(self, activity: ActivityType):
        """手动设置当前活动。"""
        self.current_activity = activity
        self.last_activity_change = datetime.now()

    def record_user_interaction(self):
        """记录一次用户交互。"""
        self.last_user_interaction = datetime.now()
        self.social_desire = max(0, self.social_desire - 10)
        self.loneliness_pressure = max(0, self.loneliness_pressure - 15)
