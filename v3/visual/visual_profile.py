"""
角色视觉档案（骨架）

定义角色的不可变视觉特征：面孔、身材、发型。
这些特征在角色生命周期内保持不变，保证图片一致性。
"""


class VisualProfile:
    """角色视觉档案 — 定义角色的不可变外观特征。

    每个角色拥有唯一的 VisualProfile，包含：
    - face: 面部特征（脸型、眼型、鼻型、嘴型、肤色）
    - body: 身材特征（身高、体型、肩宽、比例）
    - hair: 发型特征（颜色、长度、质地）

    TODO Phase 3: 完整实现特征定义和生成提示词模板
    """

    def __init__(self, character_id: str):
        """
        Args:
            character_id: 角色唯一标识
        """
        self.character_id = character_id
        self.face = self._default_face()
        self.body = self._default_body()
        self.hair = self._default_hair()
        self.style_id = "semi_realistic_v1"
        self.is_adult = True

    def to_image_prompt_part(self) -> str:
        """将视觉档案转换为图片生成提示词的面部/身材部分。

        Returns:
            Stable Diffusion / ComfyUI 格式的外貌描述文本

        TODO Phase 3: 实现
        """
        return ""

    def to_dict(self) -> dict:
        """序列化为字典，用于数据库存储。"""
        return {
            "character_id": self.character_id,
            "face": self.face,
            "body": self.body,
            "hair": self.hair,
            "style_id": self.style_id,
            "is_adult": self.is_adult,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VisualProfile":
        """从字典恢复 VisualProfile 实例。"""
        profile = cls(data["character_id"])
        profile.face = data.get("face", profile._default_face())
        profile.body = data.get("body", profile._default_body())
        profile.hair = data.get("hair", profile._default_hair())
        profile.style_id = data.get("style_id", "semi_realistic_v1")
        profile.is_adult = data.get("is_adult", True)
        return profile

    @staticmethod
    def _default_face() -> dict:
        return {
            "face_shape": "oval",
            "eye_shape": "almond",
            "nose_shape": "straight",
            "mouth_shape": "medium",
            "skin_tone": "fair",
        }

    @staticmethod
    def _default_body() -> dict:
        return {
            "height": 165,
            "body_type": "slim",
            "shoulder_width": "medium",
            "waist_ratio": "standard",
            "leg_ratio": "standard",
        }

    @staticmethod
    def _default_hair() -> dict:
        return {
            "base_color": "black",
            "base_length": "long",
            "base_texture": "straight",
        }
