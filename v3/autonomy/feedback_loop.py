"""
反馈闭环 — Memory Writeback 升级版（P2 重写）

每次行为结束必须写入：
  - 事件记忆（memory_record）
  - 情绪变化（emotion_delta）
  - 关系变化（relationship_delta）
  - 行为结果（execution status + world_affect）

写入数据库：
  - feedback_events       — 行为事件记录
  - mood_pressure_log     — 情绪压力变化
  - character_state       — 角色状态更新
"""

import json
from typing import Optional

from ..db import V3Database


class FeedbackLoop:
    """行为完成后的状态回写 + 记忆写入。

    将每个自主行为的结果回写到：
    1. feedback_events 表 — 事件记忆 + 情绪/关系变化
    2. mood_pressure_log — 情绪压力变化（通过 db 直接记录）
    3. 通过回调影响下一轮 tick
    """

    def __init__(self, db: V3Database = None):
        self.db = db or V3Database()
        self._on_memory_written_callbacks: list = []

    def register_callback(self, callback):
        """注册记忆写入回调。"""
        self._on_memory_written_callbacks.append(callback)

    def on_action_done(self, character_id: str, action_type: str,
                       decision: dict, result: dict) -> dict:
        """行为完成后的反馈处理 — 写入事件记忆 + 情绪/关系变化。

        Args:
            character_id: 角色 ID
            action_type: 行为类型
            decision: 自主决策内容
            result: 行为执行结果

        Returns:
            {emotion_delta, relationship_delta, memory_record, world_affect}
        """
        user_responded = result.get("user_responded", False)
        execution_status = result.get("status", "executed")

        # 计算反馈增量
        feedback = self._compute_feedback(
            action_type, user_responded, execution_status, result)

        # ── 写入 feedback_events 表（事件记忆 + 情绪/关系变化） ──
        try:
            self.db.insert_feedback_event(
                character_id=character_id,
                action_type=action_type,
                action_target=result.get("target", "user"),
                intent=decision.get("intent", ""),
                confidence=decision.get("confidence", 0.0),
                priority=decision.get("priority", 0),
                execution_status=execution_status,
                user_response="replied" if user_responded else "none",
                emotion_delta=feedback.get("emotion_delta", {}),
                relationship_delta=feedback.get("relationship_delta", {}),
                memory_entry=feedback.get("memory_record", ""),
            )
        except Exception:
            pass

        # ── 写入情绪压力变化 ──
        try:
            for emo_type, delta in feedback.get("emotion_delta", {}).items():
                if abs(delta) >= 1:
                    self.db.insert_mood_pressure_log(
                        tick_id=None,
                        character_id=character_id,
                        emotion_type=emo_type,
                        pressure_before=0.0,
                        pressure_after=delta,
                        delta=delta,
                        trigger=f"action:{action_type}",
                    )
        except Exception:
            pass

        # ── 触发外部回调 ──
        for cb in self._on_memory_written_callbacks:
            try:
                cb(character_id, action_type, feedback)
            except Exception:
                pass

        return feedback

    # ── 反馈计算 ──

    def _compute_feedback(self, action_type: str, user_responded: bool,
                           execution_status: str, result: dict) -> dict:
        """根据行为类型和结果计算反馈增量。"""
        feedback_map = {
            "SEND_MESSAGE":       lambda: self._feedback_message(user_responded),
            "SEND_IMAGE":         lambda: self._feedback_image(user_responded),
            "WRITE_DIARY":        lambda: self._feedback_diary(result),
            "RELATIONSHIP_EVENT": lambda: self._feedback_rel_event(result, user_responded),
            "GROUP_INTERACTION":  lambda: self._feedback_group(result),
            "UPDATE_MEMORY":      lambda: self._feedback_memory(result),
        }

        fb = feedback_map.get(action_type, lambda: {
            "emotion_delta": {}, "relationship_delta": {},
            "memory_record": "", "world_affect": ""})()

        # 执行状态影响
        if execution_status != "executed":
            fb["world_affect"] = f"{fb.get('world_affect', '')}_partial"

        return fb

    def _feedback_message(self, user_responded: bool) -> dict:
        if user_responded:
            return {
                "emotion_delta": {"lonely": -10, "happy": 5},
                "relationship_delta": {"attachment": 2},
                "memory_record": f"发送消息，用户回复了",
                "world_affect": "connection_strengthened",
            }
        return {
            "emotion_delta": {"lonely": 10, "sad": 5},
            "relationship_delta": {"attachment": 2},
            "memory_record": "发送消息，用户未回应",
            "world_affect": "silence_pressure_up",
        }

    def _feedback_image(self, user_responded: bool) -> dict:
        if user_responded:
            return {
                "emotion_delta": {"lonely": -15, "happy": 10},
                "relationship_delta": {"attachment": 5, "love": 3},
                "memory_record": "发送自拍，用户回应了",
                "world_affect": "visual_interaction_positive",
            }
        return {
            "emotion_delta": {"lonely": 15, "sad": 10},
            "relationship_delta": {"attachment": 2},
            "memory_record": "发送自拍，用户没有回应",
            "world_affect": "unanswered_selfie_negative",
        }

    def _feedback_diary(self, result: dict) -> dict:
        mood = result.get("mood", "reflect")
        return {
            "emotion_delta": {"lonely": -5, "calm": 5},
            "relationship_delta": {},
            "memory_record": f"写了一篇日记（心情：{mood}）",
            "world_affect": "diary_reflection",
        }

    def _feedback_rel_event(self, result: dict, user_responded: bool) -> dict:
        if user_responded:
            return {
                "emotion_delta": {"lonely": -8, "happy": 8},
                "relationship_delta": {"attachment": 5, "trust": 2},
                "memory_record": "关系事件获得用户回应",
                "world_affect": "relationship_event_positive",
            }
        return {
            "emotion_delta": {"lonely": 5, "sad": 8},
            "relationship_delta": {"attachment": -3, "trust": -1},
            "memory_record": "关系事件未获得用户回应",
            "world_affect": "relationship_event_negative",
        }

    def _feedback_group(self, result: dict) -> dict:
        return {
            "emotion_delta": {"lonely": -3, "happy": 2},
            "relationship_delta": {},
            "memory_record": "群聊互动获得社交满足",
            "world_affect": "social_connection",
        }

    def _feedback_memory(self, result: dict) -> dict:
        return {
            "emotion_delta": {},
            "relationship_delta": {},
            "memory_record": "内部记忆已更新",
            "world_affect": "",
        }

    # ── 兼容旧签名 ──

    def _log(self, character_id, action_type, decision, feedback):
        """已废弃：由 on_action_done 直接处理。保留以兼容旧代码。"""
        pass
