"""
记忆数据模型
包含 Memory、UserProfile 类
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class MemoryTier(str, Enum):
    """记忆层级枚举"""
    PERMANENT = "permanent"   # 永久记忆，永不过期
    LONG = "long"             # 长期记忆，365天
    SHORT = "short"           # 短期记忆，7天
    SESSION = "session"       # 会话记忆，30分钟


class Memory(BaseModel):
    """
    记忆数据模型
    对应 SQLite 表 memories
    """

    id: Optional[int] = None
    tier: MemoryTier = Field(default=MemoryTier.SESSION, description="记忆层级")
    content: str = Field(description="记忆内容文本")
    emotion_tags: list[str] = Field(default_factory=list, description="关联的情绪标签")
    intensity: float = Field(default=50.0, ge=0.0, le=100.0, description="情感强度 0-100")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="存储时间 ISO 格式")
    last_recall: Optional[str] = Field(default=None, description="最近一次召回时间")
    recall_count: int = Field(default=0, description="被召回次数")
    ttl: Optional[int] = Field(default=None, description="过期时间(Unix 秒)，None 表示永不过期")

    def is_expired(self) -> bool:
        """检查记忆是否已过期"""
        if self.tier == MemoryTier.PERMANENT or self.ttl is None:
            return False
        return int(datetime.now().timestamp()) > self.ttl

    def touch(self):
        """更新最后召回时间和计数"""
        self.last_recall = datetime.now().isoformat()
        self.recall_count += 1
        # 每次召回延长 TTL 1.5 倍，最多延长10次
        if self.tier != MemoryTier.PERMANENT and self.ttl is not None and self.recall_count <= 10:
            current_ttl = self.ttl - int(datetime.now().timestamp())
            if current_ttl > 0:
                self.ttl = int(datetime.now().timestamp()) + int(current_ttl * 1.5)

    @property
    def relevance_score(self) -> float:
        """
        计算记忆的相关度得分
        综合考虑情感强度、召回次数和时效性
        """
        recency = 1.0
        if self.last_recall:
            try:
                days_since = (datetime.now() - datetime.fromisoformat(self.last_recall)).days
                recency = max(0.1, 1.0 - days_since * 0.05)
            except Exception:
                pass
        return (self.intensity * 0.4 + self.recall_count * 5.0) * recency


class UserProfile(BaseModel):
    """
    用户画像数据模型
    对应 SQLite 表 user_profile
    """

    id: Optional[int] = None
    field: str = Field(description="画像字段名，如 favorite_color")
    value: str = Field(description="画像字段值")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="更新时间")

    @staticmethod
    def fields_schema() -> dict[str, str]:
        """返回标准用户画像字段定义"""
        return {
            "name": "用户姓名",
            "nickname": "用户昵称",
            "birthday": "生日",
            "occupation": "职业",
            "hobbies": "兴趣爱好",
            "favorite_food": "喜欢的食物",
            "disliked_food": "讨厌的食物",
            "favorite_color": "喜欢的颜色",
            "favorite_music": "喜欢的音乐类型",
            "favorite_movie_genre": "喜欢的电影类型",
            "personality_traits": "性格特点",
            "communication_style": "沟通风格",
            "love_language": "爱的语言",
            "daily_routine": "日常作息",
            "special_habits": "特殊习惯",
            "health_notes": "健康备注",
            "important_dates": "重要日期",
            "known_preferences": "已知偏好",
        }
