"""
图片请求构建器（骨架）

根据世界状态、角色状态和行为意图，
组装完整的图片生成请求结构。
"""


class ImageRequestBuilder:
    """图片请求构建器 — 组装结构化的图片生成请求。

    根据场景、角色身份、当前活动和意愿检查结果，
    构建一个包含所有必要参数的 image_request 字典。

    TODO Phase 3: 完整实现所有维度的参数组装
    """

    def __init__(self):
        pass

    def build_request(self, character_id: str, trigger_type: str,
                      world_state, visual_profile,
                      scene_context: dict = None) -> dict:
        """构建一个完整的图片生成请求。

        Args:
            character_id: 角色 ID
            trigger_type: 触发类型（"user_request" / "character_initiative" / "world_event"）
            world_state: 当前世界状态
            visual_profile: 角色视觉档案
            scene_context: 场景上下文（可选，包含 activity / emotion 等）

        Returns:
            标准化的图片请求字典（image_request 结构）

        TODO Phase 3: 完整实现
        """
        request = {
            "character_id": character_id,
            "trigger_type": trigger_type,
            "identity_lock": self._build_identity_lock(visual_profile),
            "scene": self._build_scene_params(world_state, scene_context),
            "appearance": self._build_appearance_params(scene_context),
            "camera": self._build_camera_params(trigger_type),
            "safety": {
                "character_age_verified_adult": visual_profile.is_adult,
                "explicit_content_allowed": False,
                "privacy_level": "intimate_but_safe",
            },
        }
        return request

    def _build_identity_lock(self, visual_profile) -> dict:
        """构建角色样貌锁定参数。"""
        return {
            "face_id": f"{visual_profile.character_id}_face_v1",
            "body_id": f"{visual_profile.character_id}_body_v1",
            "style_id": visual_profile.style_id,
        }

    def _build_scene_params(self, world_state, scene_context: dict) -> dict:
        """构建场景参数（位置、活动、时间、天气）。"""
        ctx = scene_context or {}
        return {
            "location": ctx.get("location", "bedroom"),
            "activity": ctx.get("activity", "idle"),
            "time_period": world_state.time_period,
            "weather": world_state.weather.type,
        }

    def _build_appearance_params(self, scene_context: dict) -> dict:
        """构建外观参数（服装、发型、表情、姿势）。"""
        ctx = scene_context or {}
        return {
            "outfit": ctx.get("outfit", "casual"),
            "hairstyle": ctx.get("hairstyle", "default"),
            "expression": ctx.get("expression", "neutral"),
            "pose": ctx.get("pose", "standing"),
        }

    def _build_camera_params(self, trigger_type: str) -> dict:
        """构建相机参数（镜头类型、角度、光线）。"""
        if trigger_type in ("character_initiative", "user_request"):
            return {
                "shot_type": "selfie",
                "angle": "eye_level",
                "lighting": "natural",
            }
        return {
            "shot_type": "casual_shot",
            "angle": "eye_level",
            "lighting": "natural",
        }
