"""
行为策略 — Phase 2 完整实现

7 种行为类型定义、触发条件规则和冷却机制。
"""

from ..config import PHASE2_ACTION_TYPES, PHASE2_ACTION_COOLDOWNS


class ActionPolicy:
    """行为策略管理器。

    管理 7 种 Phase 2 行为类型的触发条件、冷却时间，
    并与 Central Brain 的 forbidden_actions 协同过滤。
    """

    PHASE2_ACTIONS = PHASE2_ACTION_TYPES

    # 每种行为的触发条件规则（条件函数或配置）
    TRIGGER_RULES = {
        "SEND_MESSAGE": {
            "min_confidence": 0.30,
            "description": "发送一条消息给用户",
        },
        "SEND_IMAGE": {
            "min_confidence": 0.60,
            "requires_night": False,
            "description": "发送一张自拍/图片给用户",
        },
        "WRITE_DIARY": {
            "min_confidence": 0.60,
            "prefers_night": True,
            "description": "写一篇日记",
        },
        "UPDATE_MEMORY": {
            "min_confidence": 0.40,
            "description": "更新内部记忆",
        },
        "RELATIONSHIP_EVENT": {
            "min_confidence": 0.80,
            "description": "触发关系事件",
        },
        "GROUP_INTERACTION": {
            "min_confidence": 0.70,
            "description": "群聊互动",
        },
        "SILENCE": {
            "min_confidence": 0.0,
            "description": "保持沉默",
        },
    }

    def __init__(self):
        # {character_id: {action_type: last_executed_timestamp}}
        self._cooldowns: dict = {}

    def get_allowed_actions(self, character_id: str, central_state: dict,
                            world_state, current_time: float) -> list:
        """获取当前允许执行的行为列表。

        Args:
            character_id: 角色 ID
            central_state: CentralBrain 输出的统一状态
            world_state: 当前世界状态
            current_time: Unix 时间戳

        Returns:
            允许的行为类型列表
        """
        allowed = []
        blocked = set(central_state.get("blocked_actions", []))
        blocked.update(central_state.get("forbidden_actions", []))

        for action_type in self.PHASE2_ACTIONS:
            if action_type in blocked:
                continue
            if self.is_action_allowed(character_id, action_type, current_time):
                allowed.append(action_type)
        return allowed

    def get_blocked_actions(self, central_state: dict) -> list:
        """从 CentralBrain 状态中提取被阻止的行为列表。"""
        blocked = set(central_state.get("blocked_actions", []))
        blocked.update(central_state.get("forbidden_actions", []))
        return list(blocked)

    def is_action_allowed(self, character_id: str, action_type: str,
                          current_time: float) -> bool:
        """检查某行为是否在冷却期外。

        Returns:
            True 表示可以执行
        """
        if action_type == "SILENCE":
            return True
        if self.is_on_cooldown(character_id, action_type, current_time):
            return False
        return True

    def is_on_cooldown(self, character_id: str, action_type: str,
                       current_time: float) -> bool:
        """检查是否在冷却中。"""
        char_cd = self._cooldowns.get(character_id, {})
        last_time = char_cd.get(action_type)
        if last_time is None:
            return False
        cd_seconds = PHASE2_ACTION_COOLDOWNS.get(action_type, 1800)
        return (current_time - last_time) < cd_seconds

    def record_action(self, character_id: str, action_type: str, timestamp: float):
        """记录行为执行时间，更新冷却。"""
        if character_id not in self._cooldowns:
            self._cooldowns[character_id] = {}
        self._cooldowns[character_id][action_type] = timestamp

    def get_cooldown_remaining(self, character_id: str, action_type: str,
                               current_time: float) -> float:
        """获取剩余冷却时间（秒）。

        Returns:
            剩余秒数，0 表示冷却已过
        """
        char_cd = self._cooldowns.get(character_id, {})
        last_time = char_cd.get(action_type)
        if last_time is None:
            return 0.0
        cd_seconds = PHASE2_ACTION_COOLDOWNS.get(action_type, 1800)
        remaining = cd_seconds - (current_time - last_time)
        return max(remaining, 0.0)

    def reset_cooldowns(self, character_id: str):
        """重置角色的所有冷却时间（调试用）。"""
        self._cooldowns.pop(character_id, None)
