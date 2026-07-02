"""
Memory Types — 8种记忆类型定义

V4 记忆体系：
  - Session Memory    会话记忆（当前对话）
  - Short Memory      短期记忆（近期事件）
  - Long Memory       长期记忆（重要长期事件）
  - Core Memory       核心记忆（人格核心）
  - Episodic Memory   事件记忆（具体事件）
  - Emotional Memory  情绪记忆（情绪波动事件）
  - Relationship Memory 关系记忆（关系轨迹）
  - Visual Memory     视觉记忆（照片记忆）
"""

from enum import Enum
from datetime import datetime
from typing import Optional


class MemoryType(Enum):
    SESSION = "session"
    SHORT = "short"
    LONG = "long"
    CORE = "core"
    EPISODIC = "episodic"
    EMOTIONAL = "emotional"
    RELATIONSHIP = "relationship"
    VISUAL = "visual"


# 各类型记忆默认 TTL（小时）
MEMORY_TTL = {
    MemoryType.SESSION:       24,      # 1天
    MemoryType.SHORT:         168,     # 7天
    MemoryType.LONG:          8760,    # 365天
    MemoryType.CORE:          -1,      # 永久
    MemoryType.EPISODIC:      2160,    # 90天
    MemoryType.EMOTIONAL:     4320,    # 180天
    MemoryType.RELATIONSHIP:  8760,    # 365天
    MemoryType.VISUAL:        8760,    # 365天
}


class MemoryItem:
    """统一记忆条目。"""

    def __init__(
        self,
        memory_id: str = None,
        character_id: str = None,
        user_id: str = None,
        memory_type: MemoryType = MemoryType.SHORT,
        content: str = "",
        summary: str = "",
        emotion_tags: list = None,
        importance: float = 0.5,
        intensity: float = 0.5,        # 情绪强度 (0-1)
        created_at: datetime = None,
        last_accessed: datetime = None,
        access_count: int = 0,
        related_memories: list = None,
        source: str = "system",        # system / user / character / autonomy
        metadata: dict = None,
    ):
        self.memory_id = memory_id
        self.character_id = character_id
        self.user_id = user_id
        self.memory_type = memory_type
        self.content = content
        self.summary = summary
        self.emotion_tags = emotion_tags or []
        self.importance = importance
        self.intensity = intensity
        self.created_at = created_at or datetime.now()
        self.last_accessed = last_accessed or datetime.now()
        self.access_count = access_count
        self.related_memories = related_memories or []
        self.source = source
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "character_id": self.character_id,
            "user_id": self.user_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "summary": self.summary,
            "emotion_tags": self.emotion_tags,
            "importance": self.importance,
            "intensity": self.intensity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
            "source": self.source,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict) -> "MemoryItem":
        return MemoryItem(
            memory_id=data.get("memory_id"),
            character_id=data.get("character_id"),
            user_id=data.get("user_id"),
            memory_type=MemoryType(data.get("memory_type", "short")),
            content=data.get("content", ""),
            summary=data.get("summary", ""),
            emotion_tags=data.get("emotion_tags", []),
            importance=data.get("importance", 0.5),
            intensity=data.get("intensity", 0.5),
            source=data.get("source", "system"),
            metadata=data.get("metadata", {}),
        )


# 记忆类型转换规则：短期 → 长期
CONSOLIDATION_RULES = {
    "min_importance": 0.6,      # 重要性阈值
    "min_access_count": 3,      # 最少被访问次数
    "min_intensity": 0.5,       # 情绪强度阈值
    "max_age_days": 7,          # 最大保留天数
}
