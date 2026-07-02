"""
Perception Layer — 感知层整合管理器

整合 5 种感知器：
  - 用户消息感知
  - 用户缺席感知
  - 世界感知
  - 记忆感知
  - 角色间社交感知

每次 tick 统一调用 PerceptionManager，生成感知结果供所有引擎使用。
"""

from datetime import datetime
from typing import Optional


class PerceptionManager:
    """感知层整合管理器 — 统一对外感知接口。"""

    def __init__(self, db=None, event_bus=None):
        self.db = db
        self.event_bus = event_bus

        # 子感知器（可选注入，默认使用内部实现）
        self.user_message = None     # UserMessagePerception
        self.user_absence = None     # UserAbsencePerception
        self.world = None            # WorldPerception
        self.memory = None           # MemoryPerception
        self.social = None           # SocialPerception

    def perceive(self, character_id: str, world_state=None,
                  user_message_text: str = None, game_time: datetime = None) -> dict:
        """执行一次完整感知循环，返回整合后的感知结果。

        Returns:
            {
                user_perception: {...},
                absence_info: {...},
                world_perception: {...},
                memory_triggers: [...],
                social_perception: {...},
            }
        """
        result = {
            "character_id": character_id,
            "timestamp": (game_time or datetime.now()).isoformat(),
        }

        # 1. 用户消息感知
        if user_message_text and self.user_message:
            result["user_perception"] = self.user_message.perceive(user_message_text)
        elif user_message_text:
            result["user_perception"] = {
                "has_message": True,
                "length": len(user_message_text),
                "message_preview": user_message_text[:200],
            }

        # 2. 用户缺席感知
        if self.user_absence:
            result["absence_info"] = self.user_absence.check(character_id)
        else:
            result["absence_info"] = {"absent_hours": 0, "is_absent": False}

        # 3. 世界感知
        if world_state and self.world:
            result["world_perception"] = self.world.perceive(world_state)
        elif world_state:
            result["world_perception"] = {
                "time_period": getattr(world_state, "time_period", "day"),
                "weather": getattr(world_state, "weather", None),
                "atmosphere": getattr(world_state, "atmosphere", "normal"),
            }

        # 4. 记忆感知
        if self.memory:
            result["memory_triggers"] = self.memory.perceive(character_id)
        else:
            result["memory_triggers"] = []

        # 5. 角色间社交感知
        if self.social:
            result["social_perception"] = self.social.perceive(character_id)

        return result
