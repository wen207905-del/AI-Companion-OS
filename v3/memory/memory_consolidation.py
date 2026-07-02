"""
Memory Consolidation — 记忆巩固

每天 0 点执行：
  短期记忆 → 判断是否转长期
  情绪强度高的事件 → 情绪记忆
  关系节点 → 关系记忆
  图片事件 → 视觉记忆
"""

from datetime import datetime, timedelta
from typing import Optional
from .memory_types import MemoryType, CONSOLIDATION_RULES


class MemoryConsolidation:
    """记忆巩固引擎 — 定期将短期记忆转换为长期/情绪/关系/视觉记忆。"""

    def __init__(self, db=None):
        self.db = db

    def consolidate(self, character_id: str) -> dict:
        """执行一次记忆巩固。

        Returns:
            {promoted: int, archived: int, emotional_created: int, ...}
        """
        result = {
            "character_id": character_id,
            "promoted_to_long": 0,
            "promoted_to_emotional": 0,
            "promoted_to_relationship": 0,
            "archived_short": 0,
        }

        if not self.db:
            return result

        try:
            # 获取过去 7 天的短期记忆
            since = datetime.now() - timedelta(days=7)
            short_memories = self.db.get_memories_by_type(
                character_id, MemoryType.SHORT.value, since=since)

            min_importance = CONSOLIDATION_RULES["min_importance"]
            min_intensity = CONSOLIDATION_RULES["min_intensity"]

            for mem in short_memories:
                importance = mem.get("importance", 0.5)
                intensity = mem.get("intensity", 0.5)
                emotion_tags = mem.get("emotion_tags", []) or []

                # 判断是否升为长期记忆
                if importance >= min_importance:
                    self._promote(mem, MemoryType.LONG)
                    result["promoted_to_long"] += 1

                # 情绪强度高的 → 情绪记忆
                if intensity >= min_intensity:
                    self._promote(mem, MemoryType.EMOTIONAL)
                    result["promoted_to_emotional"] += 1

                # 关系相关的 → 关系记忆
                if "relationship" in emotion_tags or importance >= 0.8:
                    self._promote(mem, MemoryType.RELATIONSHIP)
                    result["promoted_to_relationship"] += 1

        except Exception:
            pass

        return result

    def _promote(self, memory: dict, target_type: MemoryType):
        """将记忆提升到目标类型（在数据库中更新或插入新类型记录）。"""
        if not self.db:
            return
        try:
            self.db.insert_memory(
                character_id=memory.get("character_id"),
                memory_type=target_type.value,
                content=memory.get("content", ""),
                summary=memory.get("summary", ""),
                importance=memory.get("importance", 0.5),
                intensity=memory.get("intensity", 0.5),
                emotion_tags=memory.get("emotion_tags", []),
                source="consolidation",
            )
        except Exception:
            pass

    def archive_stale_short_memories(self, character_id: str) -> int:
        """归档过期的短期记忆。"""
        if not self.db:
            return 0
        try:
            cutoff = datetime.now() - timedelta(days=CONSOLIDATION_RULES["max_age_days"])
            count = self.db.archive_memories(character_id, MemoryType.SHORT.value, cutoff)
            return count
        except Exception:
            return 0
