"""
反馈闭环 — Phase 2 核心新增模块

on_action_done() → 回写 emotion / relationship / memory / world_affect。
每个自主行为完成后必须经过反馈闭环，让系统"活起来"。
"""

from ..db import V3Database


class FeedbackLoop:
    """行为完成后的状态回写。

    将每个自主行为的结果回写到情绪/关系/记忆/世界影响。
    """

    def __init__(self, db: V3Database = None):
        self.db = db or V3Database()

    def on_action_done(self, character_id: str, action_type: str,
                       decision: dict, result: dict) -> dict:
        """行为完成后的反馈处理。"""
        user_responded = result.get("user_responded", False)

        feedback_map = {
            "SEND_MESSAGE":       lambda: self._feedback_message(user_responded),
            "SEND_IMAGE":         lambda: self._feedback_image(user_responded),
            "WRITE_DIARY":        lambda: self._feedback_diary(result),
            "RELATIONSHIP_EVENT": lambda: self._feedback_rel_event(result),
            "GROUP_INTERACTION":  lambda: self._feedback_group(result),
            "UPDATE_MEMORY":      lambda: self._feedback_memory(result),
        }

        feedback = feedback_map.get(action_type, lambda: {
            "emotion_delta": {}, "relationship_delta": {},
            "memory_record": "", "world_affect": ""})()
        self._log(character_id, action_type, decision, feedback)
        return feedback

    def _feedback_message(self, user_responded: bool) -> dict:
        if user_responded:
            return {"emotion_delta": {"lonely": -10, "happy": +5},
                    "relationship_delta": {"attachment": +2},
                    "memory_record": "用户回复了消息", "world_affect": "connection_strengthened"}
        return {"emotion_delta": {"lonely": +10, "sad": +5},
                "relationship_delta": {"attachment": +3},
                "memory_record": "发了消息但用户未回应", "world_affect": "silence_pressure_up"}

    def _feedback_image(self, user_responded: bool) -> dict:
        if user_responded:
            return {"emotion_delta": {"lonely": -15, "happy": +10},
                    "relationship_delta": {"attachment": +5, "love": +3},
                    "memory_record": "发了自拍用户回应了", "world_affect": "visual_interaction_positive"}
        return {"emotion_delta": {"lonely": +15, "sad": +10},
                "relationship_delta": {"attachment": +2},
                "memory_record": "发了自拍但用户没有回应", "world_affect": "unanswered_selfie_negative"}

    def _feedback_diary(self, result: dict) -> dict:
        return {"emotion_delta": {"lonely": -5, "calm": +5},
                "relationship_delta": {},
                "memory_record": "写了一篇日记", "world_affect": "diary_reflection"}

    def _feedback_rel_event(self, result: dict) -> dict:
        return {"emotion_delta": {"lonely": -8, "happy": +3},
                "relationship_delta": {"attachment": +4, "trust": +2},
                "memory_record": "触发关系事件", "world_affect": "relationship_event_positive"}

    def _feedback_group(self, result: dict) -> dict:
        return {"emotion_delta": {"lonely": -3, "happy": +2},
                "relationship_delta": {},
                "memory_record": "群聊互动获得社交满足", "world_affect": "social_connection"}

    def _feedback_memory(self, result: dict) -> dict:
        return {"emotion_delta": {}, "relationship_delta": {},
                "memory_record": "内部记忆已更新", "world_affect": ""}

    def _log(self, character_id, action_type, decision, feedback):
        try:
            self.db.insert_feedback_event(
                character_id=character_id, action_type=action_type,
                score=decision.get("score", 0), intent=decision.get("intent", ""),
                emotion_delta=feedback["emotion_delta"],
                relationship_delta=feedback["relationship_delta"],
                memory_record=feedback["memory_record"],
                world_affect=feedback["world_affect"])
        except Exception:
            pass
