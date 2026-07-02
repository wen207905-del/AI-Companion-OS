"""
样貌锁定系统（骨架）

确保同一角色在不同场景、服装、姿势下生成的图片
保持相同的面孔和身材特征。

核心原则：
- 脸不变
- 身材不变
- 角色气质不变
- 允许变化：衣服、姿势、表情、场景、光线、角度
"""


class IdentityLock:
    """样貌锁定系统 — 保证角色图片视觉一致性。

    通过固定种子 ID、固定的外貌描述嵌入等方式，
    确保每次生成图片时角色看起来是同一个人。

    TODO Phase 3: 完整实现 identity embedding 和提示词注入逻辑
    """

    def __init__(self):
        self._locked_profiles: dict = {}  # character_id → VisualProfile

    def register_profile(self, profile) -> None:
        """注册角色的视觉档案。

        Args:
            profile: VisualProfile 实例
        """
        from .visual_profile import VisualProfile
        if isinstance(profile, VisualProfile):
            self._locked_profiles[profile.character_id] = profile

    def get_identity_prompt(self, character_id: str) -> str:
        """获取角色的样貌锁定提示词片段。

        这段提示词会注入到每次图片生成的 prompt 中，
        确保生成的角色外貌一致。

        Args:
            character_id: 角色 ID

        Returns:
            样貌固定提示词文本

        TODO Phase 3: 从 VisualProfile 生成精确的面部/身材描述
        """
        profile = self._locked_profiles.get(character_id)
        if profile is None:
            return ""
        return profile.to_image_prompt_part()

    def get_forbidden_changes(self, character_id: str) -> list:
        """获取角色的禁止修改特征列表。

        Args:
            character_id: 角色 ID

        Returns:
            不可变的特征名称列表

        TODO Phase 3: 实现
        """
        return [
            "face_shape",
            "eye_shape",
            "body_ratio",
            "skin_tone",
            "base_identity",
        ]
