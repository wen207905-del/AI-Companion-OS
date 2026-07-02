"""
Memory Perception — 记忆感知

检索与当前情境相关的记忆，返回 scored memories。
用于 Autonomy Engine 和 Emotion Dynamics 的上下文输入。
"""

from typing import Optional


class MemoryPerception:
    """记忆感知器。

    每次 tick 检索与当前情境最相关的记忆条目。
    """

    def __init__(self, db=None, memory_retriever=None):
        self.db = db
        self.retriever = memory_retriever

    def perceive(self, character_id: str, context: dict = None,
                  limit: int = 5) -> list:
        """感知相关记忆。

        Args:
            character_id: 角色 ID
            context: 当前情境（时间、情绪、世界状态等）
            limit: 返回最大条数

        Returns:
            [{"memory_id": ..., "content": ..., "type": ..., "score": ...}, ...]
        """
        if self.retriever:
            return self.retriever.retrieve(character_id, context=context, limit=limit)

        # 兜底：从数据库直接查询
        if self.db:
            try:
                rows = self.db.get_recent_memories(character_id, limit)
                return [
                    {"memory_id": r.get("id"), "content": r.get("content", ""),
                     "type": r.get("memory_type", "short"), "score": 0.5}
                    for r in rows
                ]
            except Exception:
                pass

        return []
