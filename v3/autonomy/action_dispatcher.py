"""
行为调度器 — Phase 2 完整实现

execute(action) 路由到 7 个 handler，每个 handler 提供占位实现。
"""


class ActionDispatcher:
    """行为调度器 — 接收决策并分发到对应 handler。

    Phase 2 实现 7 种行为类型的路由，各 handler 写占位实现，
    后续 Phase 3 接入真实的消息/图片/记忆系统。
    """

    def __init__(self):
        self._handlers = {
            "SEND_MESSAGE":        self._handle_send_message,
            "SEND_IMAGE":          self._handle_send_image,
            "WRITE_DIARY":         self._handle_write_diary,
            "UPDATE_MEMORY":       self._handle_update_memory,
            "RELATIONSHIP_EVENT":  self._handle_relationship_event,
            "GROUP_INTERACTION":   self._handle_group_interaction,
            "SILENCE":             self._handle_silence,
        }

    def dispatch(self, character_id: str, action_type: str,
                 context: dict) -> dict:
        """将自主行为决策分发到对应 handler。

        Args:
            character_id: 角色 ID
            action_type: 行为类型（7 种之一）
            context: 执行上下文

        Returns:
            {"success": bool, "action": str, "status": str, "note": str, ...}
        """
        handler = self._handlers.get(action_type)
        if handler:
            return handler(character_id, context)
        return {"success": False, "action": action_type,
                "error": f"未知行为类型: {action_type}"}

    # ──────────── 7 个 Handler ────────────

    def _handle_send_message(self, character_id: str, context: dict) -> dict:
        """发送消息 — Phase 2 占位实现。

        Phase 3: 接入 Dialogue Engine 生成真实消息内容。
        """
        return {
            "success": True, "action": "SEND_MESSAGE", "status": "placeholder",
            "character_id": character_id,
            "note": "[Phase 2 占位] 角色向用户发送了一条消息",
            "intent": context.get("intent", "chat"),
        }

    def _handle_send_image(self, character_id: str, context: dict) -> dict:
        """发送图片 — Phase 2 占位实现。

        Phase 3: 接入 Visual Engine 生成自拍/图片。
        """
        return {
            "success": True, "action": "SEND_IMAGE", "status": "placeholder",
            "character_id": character_id,
            "note": "[Phase 2 占位] 角色向用户发送了一张图片",
            "scene_type": context.get("scene_type", "selfie"),
        }

    def _handle_write_diary(self, character_id: str, context: dict) -> dict:
        """写日记 — Phase 2 占位实现。

        Phase 3: 接入 Memory System 生成日记内容并持久化。
        """
        return {
            "success": True, "action": "WRITE_DIARY", "status": "placeholder",
            "character_id": character_id,
            "note": "[Phase 2 占位] 角色写了一篇日记",
            "mood": context.get("mood", "reflect"),
        }

    def _handle_update_memory(self, character_id: str, context: dict) -> dict:
        """更新记忆 — Phase 2 占位实现。

        Phase 3: 接入 Memory System 写入长期记忆。
        """
        return {
            "success": True, "action": "UPDATE_MEMORY", "status": "placeholder",
            "character_id": character_id,
            "note": "[Phase 2 占位] 角色更新了内部记忆",
        }

    def _handle_relationship_event(self, character_id: str, context: dict) -> dict:
        """关系事件 — Phase 2 占位实现。

        Phase 3: 接入 Relationship Engine 触发关系变化事件。
        """
        return {
            "success": True, "action": "RELATIONSHIP_EVENT", "status": "placeholder",
            "character_id": character_id,
            "note": "[Phase 2 占位] 触发了关系事件",
            "event_type": context.get("event_type", "emotional"),
        }

    def _handle_group_interaction(self, character_id: str, context: dict) -> dict:
        """群互动 — Phase 2 占位实现。

        Phase 3: 接入群聊系统发起群互动。
        """
        return {
            "success": True, "action": "GROUP_INTERACTION", "status": "placeholder",
            "character_id": character_id,
            "note": "[Phase 2 占位] 角色在群聊中互动",
        }

    def _handle_silence(self, character_id: str, context: dict) -> dict:
        """保持沉默 — 仅内部状态更新，无外显行为。"""
        return {
            "success": True, "action": "SILENCE", "status": "internal",
            "character_id": character_id,
            "note": "角色保持沉默",
        }

    # ──────────── 兼容旧 Phase 1 handler ────────────

    _dispatch_message = _handle_send_message
    _dispatch_selfie = _handle_send_image
    _dispatch_diary = _handle_write_diary
    _dispatch_memory_recall = _handle_update_memory
    _dispatch_group_topic = _handle_group_interaction
    _dispatch_private_message = _handle_send_message
    _dispatch_character_interaction = _handle_relationship_event
    _dispatch_stay_silent = _handle_silence
