"""
Social Perception — 角色间社交感知

感知其他角色的状态和行为，用于群聊和角色互动。
"""

from typing import Optional


class SocialPerception:
    """角色间社交感知器。"""

    def __init__(self, db=None):
        self.db = db
        # 角色间关系缓存
        self._inter_char_relations: dict = {}

    def perceive(self, character_id: str) -> dict:
        """感知其他角色状态。

        Returns:
            {
                nearby_characters: [...],
                recent_interactions: [...],
                group_atmosphere: str,
            }
        """
        result = {
            "nearby_characters": [],
            "recent_interactions": [],
            "group_atmosphere": "neutral",
        }

        if self.db:
            try:
                # 获取其他角色活跃状态
                chars = self.db.get_active_characters()
                if chars:
                    result["nearby_characters"] = [
                        {"id": c.get("id"), "name": c.get("name"),
                         "activity": c.get("current_activity", "idle")}
                        for c in chars if c.get("id") != character_id
                    ]
            except Exception:
                pass

        return result

    def record_interaction(self, from_char: str, to_char: str, event_type: str):
        """记录角色间互动。"""
        key = f"{from_char}:{to_char}"
        if key not in self._inter_char_relations:
            self._inter_char_relations[key] = []
        self._inter_char_relations[key].append({
            "event_type": event_type,
            "timestamp": None,  # 简化处理
        })
