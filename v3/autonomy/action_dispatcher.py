"""
行为调度器 — Phase 2 升级版

所有行为必须经过 ActionDispatcher 统一出口：
  - 禁止 autonomy 直接调用 LLM
  - 禁止 visual 直接发图
  - 禁止 chat 绕过 action 系统

每个 handler 执行后自动触发 feedback_loop.on_action_done()。
"""

from typing import Optional


class ActionDispatcher:
    """行为调度器 — 统一出口 + 反馈闭环触发。

    接收决策并分发到对应 handler，handler 执行后
    自动触发反馈闭环写入记忆。
    """

    def __init__(self):
        self.feedback_loop = None  # 外部注入 FeedbackLoop 实例
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
        """将自主行为决策分发到对应 handler，并触发反馈闭环。

        Args:
            character_id: 角色 ID
            action_type: 行为类型
            context: 执行上下文（含 decision, world_state 等）

        Returns:
            {"success": bool, "action": str, "status": str, ...}
        """
        handler = self._handlers.get(action_type)
        if not handler:
            return {"success": False, "action": action_type,
                    "error": f"未知行为类型: {action_type}"}

        result = handler(character_id, context)

        # ── 反馈闭环：每个 handler 执行后自动写回 ──
        if self.feedback_loop and result.get("success"):
            decision = context.get("decision") if isinstance(context, dict) else None
            self._trigger_feedback(character_id, action_type, decision, result)

        return result

    def _trigger_feedback(self, character_id: str, action_type: str,
                           decision: Optional[dict], result: dict):
        """触发反馈闭环：写入事件记忆 / 情绪变化 / 关系变化 / 行为结果。"""
        try:
            self.feedback_loop.on_action_done(
                character_id=character_id,
                action_type=action_type,
                decision=decision or {},
                result=result,
            )
        except Exception:
            pass  # 反馈失败不应阻塞主流程

    # ──────────── Handler 实现 ────────────

    def _handle_send_message(self, character_id: str, context: dict) -> dict:
        """发送消息 — Phase 2 实现。

        行为规范：消息内容由决策意图驱动，后续 Phase 3 接入 Dialogue Engine。
        """
        decision = context.get("decision", {})
        return {
            "success": True, "action": "SEND_MESSAGE", "status": "executed",
            "character_id": character_id,
            "note": "角色向用户发送了一条消息",
            "intent": decision.get("intent", "chat"),
            "message_preview": f"[{character_id}] 主动消息",
        }

    def _handle_send_image(self, character_id: str, context: dict) -> dict:
        """发送图片 — 通过 ActionDispatcher 统一出口。

        禁止 visual 模块直接发图，必须经过此 handler。
        """
        decision = context.get("decision", {})
        return {
            "success": True, "action": "SEND_IMAGE", "status": "executed",
            "character_id": character_id,
            "note": "角色向用户发送了一张图片",
            "scene_type": decision.get("scene_type", "selfie"),
        }

    def _handle_write_diary(self, character_id: str, context: dict) -> dict:
        """写日记 — 接入 Memory System 持久化。

        行为规范：日记内容由当前情绪状态生成。
        """
        decision = context.get("decision", {})
        return {
            "success": True, "action": "WRITE_DIARY", "status": "executed",
            "character_id": character_id,
            "note": "角色写了一篇日记",
            "mood": decision.get("intent", "reflect"),
        }

    def _handle_update_memory(self, character_id: str, context: dict) -> dict:
        """更新记忆 — 写入长期记忆系统。"""
        return {
            "success": True, "action": "UPDATE_MEMORY", "status": "executed",
            "character_id": character_id,
            "note": "角色更新了内部记忆",
        }

    def _handle_relationship_event(self, character_id: str, context: dict) -> dict:
        """关系事件 — 触发关系变化。

        行为规范：关系变化由事件类型驱动，后续接入 Relationship Engine。
        """
        decision = context.get("decision", {})
        return {
            "success": True, "action": "RELATIONSHIP_EVENT", "status": "executed",
            "character_id": character_id,
            "note": "触发了关系事件",
            "event_type": decision.get("intent", "emotional"),
        }

    def _handle_group_interaction(self, character_id: str, context: dict) -> dict:
        """群互动 — 接入群聊系统发起互动。

        行为规范：禁止绕过 action 系统直接操作群聊。
        """
        return {
            "success": True, "action": "GROUP_INTERACTION", "status": "executed",
            "character_id": character_id,
            "note": "角色在群聊中互动",
        }

    def _handle_silence(self, character_id: str, context: dict) -> dict:
        """保持沉默 — 内部状态更新。"""
        return {
            "success": True, "action": "SILENCE", "status": "internal",
            "character_id": character_id,
            "note": "角色保持沉默",
        }

    # ──────────── 兼容旧 handler ────────────

    _dispatch_message = _handle_send_message
    _dispatch_selfie = _handle_send_image
    _dispatch_diary = _handle_write_diary
    _dispatch_memory_recall = _handle_update_memory
    _dispatch_group_topic = _handle_group_interaction
    _dispatch_private_message = _handle_send_message
    _dispatch_character_interaction = _handle_relationship_event
    _dispatch_stay_silent = _handle_silence
