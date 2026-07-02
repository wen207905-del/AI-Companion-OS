"""
边界安全检查（骨架）

所有图片生成行为必须经过此模块的验证。
包括年龄验证、内容边界检查和角色意愿机制。
"""

from ..config import (
    MIN_CHARACTER_AGE_FOR_VISUAL,
    CONSENT_REQUIREMENTS,
    CONSENT_EMOTION_BLOCKLIST,
    PERSONALITY_CONSENT_MODIFIER,
)


class SafetyChecker:
    """边界安全检查器 — V3 的安全防线。

    所有图片生成请求必须通过三个检查：
    1. 年龄验证：角色必须是成年人
    2. 内容边界：生成的图片类型必须在允许范围内
    3. 意愿机制：角色当前状态愿意拍这种类型的照片

    TODO Phase 3: 完整实现检查逻辑和自定义规则
    """

    def __init__(self):
        self.min_age = MIN_CHARACTER_AGE_FOR_VISUAL
        self.consent_requirements = CONSENT_REQUIREMENTS
        self.emotion_blocklist = CONSENT_EMOTION_BLOCKLIST

    def check_all(self, character_id: str, visual_profile,
                  image_request: dict, emotion_state: dict,
                  relationship_state: dict, personality: dict) -> dict:
        """执行全部安全检查。

        Args:
            character_id: 角色 ID
            visual_profile: 角色视觉档案
            image_request: 图片生成请求
            emotion_state: 当前情绪状态
            relationship_state: 当前关系状态
            personality: 角色性格

        Returns:
            检查结果:
            - passed: 是否通过全部检查
            - failures: 未通过的检查项列表
            - refusal_message: 拒绝时给用户的回复文本

        TODO Phase 3: 完整实现
        """
        failures = []

        # 年龄检查
        age_check = self.check_age(visual_profile)
        if not age_check["passed"]:
            failures.append(age_check)

        # 内容边界检查
        content_check = self.check_content_boundary(image_request)
        if not content_check["passed"]:
            failures.append(content_check)

        # 意愿检查
        consent_check = self.check_consent(character_id, image_request,
                                            emotion_state, relationship_state, personality)
        if not consent_check["passed"]:
            failures.append(consent_check)

        return {
            "passed": len(failures) == 0,
            "failures": failures,
            "refusal_message": self._generate_refusal(failures) if failures else "",
        }

    def check_age(self, visual_profile) -> dict:
        """检查角色年龄是否满足图片生成要求。

        Args:
            visual_profile: 角色视觉档案

        Returns:
            检查结果
        """
        if not visual_profile.is_adult:
            return {
                "passed": False,
                "reason": "age_under_minimum",
                "message": "该角色年龄设定不满足视觉系统要求",
            }
        return {"passed": True, "reason": "", "message": ""}

    def check_content_boundary(self, image_request: dict) -> dict:
        """检查图片内容是否在允许边界内。

        Args:
            image_request: 图片生成请求

        Returns:
            检查结果

        TODO Phase 3: 完整实现内容类型白名单检查
        """
        return {"passed": True, "reason": "", "message": ""}

    def check_consent(self, character_id: str, image_request: dict,
                      emotion_state: dict, relationship_state: dict,
                      personality: dict) -> dict:
        """检查角色是否愿意生成此类型照片。

        基于三个维度：
        - 关系阶段和信任/安全感是否达标
        - 当前情绪是否在阻止列表中
        - 性格对阈值的修正

        Args:
            character_id: 角色 ID
            image_request: 图片请求
            emotion_state: 情绪状态
            relationship_state: 关系状态
            personality: 性格

        Returns:
            检查结果

        TODO Phase 3: 完整实现意愿计算
        """
        # 情绪阻止检查
        dominant_emotion = emotion_state.get("dominant_emotion", "neutral")
        if dominant_emotion in self.emotion_blocklist:
            return {
                "passed": False,
                "reason": "emotion_blocked",
                "message": f"角色当前情绪 ({dominant_emotion}) 不适合拍摄此类照片",
            }

        return {"passed": True, "reason": "", "message": ""}

    def _generate_refusal(self, failures: list) -> str:
        """生成拒绝回复文本。

        Args:
            failures: 未通过的检查项列表

        Returns:
            对用户的拒绝回复

        TODO Phase 3: 生成符合角色性格的自然语言拒绝
        """
        return "今天不想拍这个。"
