"""
Memory Retriever — 记忆检索器

根据当前情境检索相关记忆，返回 scored memories。
支持多维度评分：时间相关性、情绪匹配、关键词匹配、重要性权重。
"""

from datetime import datetime
from typing import Optional


class MemoryRetriever:
    """记忆检索器 — 情境感知的记忆检索。"""

    def __init__(self, db=None):
        self.db = db

    def retrieve(self, character_id: str, context: dict = None,
                  memory_types: list = None, limit: int = 5) -> list:
        """检索相关记忆。

        Args:
            character_id: 角色 ID
            context: 当前情境（包含 emotion_dominant / time_period / keywords 等）
            memory_types: 限定记忆类型
            limit: 返回条数

        Returns:
            [{"memory_id": ..., "content": ..., "type": ..., "score": ...}, ...]
        """
        context = context or {}
        results = []

        if self.db:
            try:
                rows = self.db.get_recent_memories(character_id, limit=limit * 2)
                if rows:
                    results = [
                        {
                            "memory_id": r.get("id"),
                            "content": r.get("content", ""),
                            "summary": r.get("summary", ""),
                            "type": r.get("memory_type", "short"),
                            "importance": r.get("importance", 0.5),
                            "created_at": r.get("created_at", ""),
                            "score": 0.5,
                        }
                        for r in rows
                    ]
            except Exception:
                pass

        # 评分和排序
        scored = self._score_memories(results, context)
        scored.sort(key=lambda x: x["score"], reverse=True)

        # 类型过滤
        if memory_types:
            scored = [m for m in scored if m.get("type") in memory_types]

        return scored[:limit]

    def _score_memories(self, memories: list, context: dict) -> list:
        """对记忆进行多维评分。

        评分维度：
          1. 时间衰减：越近越高
          2. 情绪匹配：与当前主导情绪匹配
          3. 重要性权重
          4. 关键词匹配
        """
        now = datetime.now()
        dominant = context.get("emotion_dominant", "")
        keywords = context.get("keywords", [])
        time_period = context.get("time_period", "")

        for mem in memories:
            score = mem.get("importance", 0.5) * 0.3  # 基础分

            # 1. 时间衰减
            created = mem.get("created_at", "")
            if created:
                try:
                    if isinstance(created, str):
                        created = datetime.fromisoformat(created)
                    hours_ago = (now - created).total_seconds() / 3600
                    decay = max(0, 1.0 - hours_ago / (24 * 30))  # 30天衰减
                    score += decay * 0.3
                except Exception:
                    score += 0.15

            # 2. 情绪匹配
            emotion_tags = mem.get("emotion_tags", []) or []
            if dominant and dominant in emotion_tags:
                score += 0.2

            # 3. 关键词匹配
            content = mem.get("content", "") + " " + mem.get("summary", "")
            matched = sum(1 for kw in keywords if kw in content)
            if matched:
                score += min(0.2, matched * 0.05)

            # 4. 时间段匹配（深夜更容易触发怀旧记忆）
            if time_period in ("late_night", "evening"):
                score += 0.05

            mem["score"] = round(min(1.0, score), 3)

        return memories

    def retrieve_by_emotion(self, character_id: str, emotion: str,
                             limit: int = 3) -> list:
        """按情绪检索相关记忆。"""
        return self.retrieve(character_id,
                             context={"emotion_dominant": emotion},
                             limit=limit)
