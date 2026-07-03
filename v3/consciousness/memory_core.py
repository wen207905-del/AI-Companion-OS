"""
V4 Memory Core — 统一记忆核心

8 种记忆类型管理 + 检索 + 巩固 + prompt 构建。
"""

import json
import time
from datetime import datetime
from enum import Enum
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


class MemoryCore:
    """V4 统一记忆系统。

    检索排序: relevance * 0.5 + recency * 0.3 + emotional_weight * 0.2
    """

    def __init__(self, db=None, event_bus=None):
        self.db = db
        self.event_bus = event_bus

    # ── 写入 ──

    def store(self, character_id: str, content: str,
              memory_type: str = "short", summary: str = "",
              emotion_tags: list = None, importance: float = 0.5,
              intensity: float = 0.5, source: str = "system",
              metadata: dict = None) -> Optional[int]:
        """存储记忆条目。"""
        if self.db:
            try:
                return self.db.insert_memory_item(
                    character_id=character_id,
                    memory_type=memory_type,
                    content=content,
                    summary=summary or content[:100],
                    emotion_tags=emotion_tags or [],
                    importance=importance,
                    intensity=intensity,
                    source=source,
                    metadata=metadata or {},
                )
            except Exception:
                pass
        return None

    # ── 检索 ──

    def retrieve(self, character_id: str,
                 memory_type: str = None,
                 keywords: list = None,
                 emotion_tags: list = None,
                 limit: int = 20) -> list:
        """检索角色记忆。

        从数据库拉取，按 relevance + recency + emotional_weight 排序。
        """
        if not self.db:
            return []

        try:
            if keywords or emotion_tags:
                raw = self.db.search_memories(
                    character_id, keywords, emotion_tags, limit * 2
                )
            else:
                raw = self.db.get_memories_by_character(
                    character_id, memory_type, limit * 2
                )
        except Exception:
            return []

        # 排序：relevance(0.5) + recency(0.3) + emotional_weight(0.2)
        now = time.time()
        scored = []
        for mem in (raw or []):
            try:
                importance = float(mem.get("importance", 0.5))
                intensity = float(mem.get("intensity", 0.5))
                created = mem.get("created_at", "")
                try:
                    t = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
                except Exception:
                    t = now - 86400 * 7  # 默认一周前
                age_hours = max(0, (now - t) / 3600)
                recency = max(0, 1.0 - age_hours / (24 * 7))  # 7天衰减到0

                score = importance * 0.5 + recency * 0.3 + intensity * 0.2
                scored.append((score, mem))
            except Exception:
                scored.append((0, mem))

        scored.sort(key=lambda x: x[0], reverse=True)

        # 更新访问计数
        if self.db:
            for _, mem in scored[:limit]:
                try:
                    mem_id = mem.get("id")
                    if mem_id:
                        self.db.update_memory_access(mem_id)
                except Exception:
                    pass

        return [mem for _, mem in scored[:limit]]

    def retrieve_context(self, character_id: str = None,
                          context: str = "current_tick",
                          limit: int = 5) -> dict:
        """为当前 tick 检索上下文记忆。"""
        if not character_id:
            return {"memories": [], "context_string": ""}

        memories = self.retrieve(character_id, limit=limit)
        context_parts = []
        for mem in memories:
            content = mem.get("content") or mem.get("summary", "")
            if content:
                context_parts.append(f"- {content[:120]}")

        return {
            "memories": memories,
            "context_string": "\n".join(context_parts[:limit]),
        }

    # ── 巩固 ──

    def consolidate(self, character_id: str) -> dict:
        """每天 0 点执行：短期记忆 → 长期/情绪/关系记忆。"""
        result = {"promoted": 0, "deleted": 0}

        try:
            # 获取短期记忆中重要性较高的
            short_mems = self.retrieve(
                character_id, memory_type="short", limit=50
            )

            for mem in short_mems:
                importance = float(mem.get("importance", 0))
                intensity = float(mem.get("intensity", 0))

                if importance >= 0.7 and intensity >= 0.6:
                    # 提升为长期记忆
                    self.store(
                        character_id=character_id,
                        content=mem.get("content", ""),
                        memory_type="long",
                        summary=mem.get("summary", ""),
                        importance=importance,
                        intensity=intensity,
                        source="consolidation",
                    )
                    result["promoted"] += 1
                elif importance >= 0.6:
                    # 情绪记忆
                    self.store(
                        character_id=character_id,
                        content=mem.get("content", ""),
                        memory_type="emotional",
                        summary=mem.get("summary", ""),
                        importance=importance,
                        intensity=intensity,
                        source="consolidation",
                    )
                    result["promoted"] += 1

            # 清理低重要性旧记忆
            if self.db:
                try:
                    self.db.delete_low_importance_memories(
                        character_id, threshold=0.15, older_than_days=14
                    )
                except Exception:
                    pass

        except Exception as e:
            result["error"] = str(e)

        return result

    # ── Prompt 构建 ──

    def build_memory_prompt(self, character_id: str, limit: int = 3) -> str:
        """构建可注入 LLM prompt 的记忆字符串。"""
        memories = self.retrieve(character_id, limit=limit)
        if not memories:
            return ""

        lines = ["[相关记忆]"]
        for mem in memories:
            content = mem.get("content") or mem.get("summary", "")
            mtype = mem.get("memory_type", "short")
            lines.append(f"({mtype}) {content[:150]}")
        return "\n".join(lines)
