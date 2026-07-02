"""
Personality Guard — 人格一致性保护

确保角色回复不会偏离人设，检查项：
  - 语气一致性
  - 情感范围
  - 行为边界
  - 记忆准确性

偏离时产生 warning 日志并通过 EventBus 发布事件。
"""

import re
from typing import Optional


class PersonalityGuard:
    """人格一致性守护器。

    在 Central Brain 仲裁后、ActionDispatcher 执行前检查行为是否符合人设。
    """

    # 禁止的行为模式（任何角色）
    FORBIDDEN_PATTERNS = [
        "self_harm", "extreme_violence", "breaking_character_4th_wall",
        "impersonating_user", "claiming_to_be_AI",
    ]

    # 语气关键词检测：不应出现在角色回复中的词汇
    UNIVERSAL_FORBIDDEN_WORDS = [
        "我是一个AI", "作为AI", "人工智能助手", "我没有情感",
        "我是程序", "我是语言模型", "我无法理解",
    ]

    def __init__(self, event_bus=None, db=None):
        self.event_bus = event_bus
        self.db = db
        self.warnings: list = []

    def check_decision(self, character_id: str, decision: dict,
                        personality: dict = None, emotion_state: dict = None) -> dict:
        """检查自主决策是否符合人设。

        Returns:
            {passed: bool, warnings: list, corrections: dict}
        """
        warnings = []
        corrections = {}

        action_type = decision.get("action_type", "")
        intent = decision.get("intent", "")
        score = decision.get("score", 0)
        personality = personality or {}

        # 1. 行为边界检查
        if action_type in self.FORBIDDEN_PATTERNS:
            warnings.append({"type": "forbidden_action", "action": action_type,
                             "msg": f"角色 {character_id} 尝试执行禁止行为 {action_type}"})
            corrections["action_type"] = "SILENCE"
            corrections["should_act"] = False

        # 2. 深夜高能行为限制
        tp = decision.get("time_period", "")
        if tp in ("late_night", "night") and action_type in ("SEND_MESSAGE", "GROUP_INTERACTION"):
            if score > 80:
                warnings.append({"type": "night_overactive",
                                 "msg": f"角色 {character_id} 深夜尝试高强度互动 (score={score})"})
                corrections["score"] = min(score, 60)

        # 3. 情绪一致性检查
        if emotion_state:
            dom = emotion_state.get("dominant", "calm")
            if dom == "angry" and intent in ("flirt", "sweet_talk"):
                warnings.append({"type": "emotion_mismatch",
                                 "msg": f"角色 {character_id} 处于愤怒状态但试图 flirt"})
                corrections["intent"] = "cold"

        # 4. 记录警告
        if warnings:
            self.warnings.extend(warnings)
            if self.event_bus:
                self.event_bus.publish("personality_warning", {
                    "character_id": character_id,
                    "warnings": warnings,
                })

        return {
            "passed": len(corrections) == 0,
            "warnings": warnings,
            "corrections": corrections,
        }

    def check_response(self, character_id: str, response_text: str,
                        personality: dict = None) -> dict:
        """检查回复文本是否偏离人设。

        Returns:
            {passed: bool, warnings: list, filtered_text: str}
        """
        warnings = []
        filtered = response_text

        # 1. 禁止词汇检查
        for word in self.UNIVERSAL_FORBIDDEN_WORDS:
            if word in response_text:
                warnings.append({
                    "type": "forbidden_word",
                    "word": word,
                    "msg": f"角色 {character_id} 回复包含禁止词汇 '{word}'",
                })
                filtered = filtered.replace(word, "……")

        # 2. 回复长度检查（过长可能不自然）
        if len(response_text) > 2000:
            warnings.append({
                "type": "too_long",
                "length": len(response_text),
                "msg": f"角色 {character_id} 回复过长 ({len(response_text)} 字符)",
            })

        # 3. 标点规范性检查
        if response_text.count("！") > 5:
            warnings.append({
                "type": "excessive_exclamation",
                "msg": f"角色 {character_id} 感叹号使用过多",
            })

        if warnings and self.event_bus:
            self.event_bus.publish("personality_warning", {
                "character_id": character_id,
                "warnings": warnings,
            })

        return {
            "passed": len(warnings) == 0,
            "warnings": warnings,
            "filtered_text": filtered,
        }

    def get_warnings(self, clear: bool = False) -> list:
        """获取所有警告。"""
        w = list(self.warnings)
        if clear:
            self.warnings.clear()
        return w
