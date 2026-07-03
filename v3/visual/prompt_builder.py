"""
V4 Visual Prompt Builder — 生图提示词结构化构建

输入：identity_profile + emotion + scene + outfit + pose + camera
输出：完整 SD/百炼 prompt，包含 identity lock token。
"""

# ── 风格模板 ──
STYLE_TEMPLATES = {
    "selfie": {
        "prefix": "A realistic selfie photo of",
        "suffix": "high quality, natural lighting, smartphone camera, mirrorless DSLR, sharp focus, photorealistic, skin texture visible",
        "composition": "looking at camera, phone visible in hand, close-up portrait",
    },
    "candid": {
        "prefix": "A candid photograph of",
        "suffix": "natural moment, photojournalistic style, shallow depth of field, golden hour light, high resolution, organic emotion",
        "composition": "natural pose, unaware of camera, mid-action, environmental context visible",
    },
    "mirror": {
        "prefix": "A mirror reflection of",
        "suffix": "in a mirror, realistic reflection, indoor lighting, sharp details, modern interior",
        "composition": "standing in front of a large mirror, looking at own reflection, full body visible in mirror",
    },
    "portrait": {
        "prefix": "A professional portrait photograph of",
        "suffix": "studio lighting, 85mm lens, bokeh background, crisp details, elegant atmosphere",
        "composition": "shoulders and above, slight smile, elegant posture, well-lit face",
    },
    "full_body": {
        "prefix": "A full body shot of",
        "suffix": "editorial fashion photography, clean composition, natural light, sharp image, stylish setting",
        "composition": "standing naturally, full body in frame, relaxed posture",
    },
}

# ── 场景提示词 ──
SCENE_PROMPTS = {
    "bedroom": "in a cozy bedroom with soft morning light streaming through curtains, messy bed with white sheets",
    "living_room": "in a modern living room with a comfortable sofa and warm ambient lighting",
    "kitchen": "in a bright kitchen, natural sunlight, minimalist design",
    "cafe": "sitting in a charming cafe, warm ambiance, coffee on table, window light",
    "outdoor_park": "in a beautiful park, green grass, trees in background, soft afternoon sunlight",
    "outdoor_street": "walking on a city street, urban background, casual atmosphere",
    "beach": "on a sunny beach, blue ocean background, gentle waves, golden sand",
    "night_city": "in a city at night, neon lights reflecting, moody atmosphere",
    "rain_window": "sitting by a window, raindrops on glass, cozy indoor lighting, melancholic mood",
}


class PromptBuilder:
    """结构化生图 Prompt 构建器。"""

    def __init__(self, identity_lock=None):
        self.identity_lock = identity_lock

    def build(self, character_id: str,
              style: str = "selfie",
              scene: str = "bedroom",
              outfit: str = "",
              pose: str = "",
              emotion: str = "",
              camera: str = "",
              extra_tags: str = "",
              negative_prompt: str = "") -> dict:
        """构建完整生图 Prompt。

        Returns:
            {
                "prompt": str,
                "negative_prompt": str,
                "identity_token": str,
            }
        """
        style_config = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["selfie"])

        # Identity token
        identity_token = ""
        if self.identity_lock:
            identity_token = self.identity_lock.build_identity_token(character_id)

        # 组装 prompt
        parts = [
            style_config["prefix"],
            identity_token if identity_token else "a beautiful woman",
        ]

        # 服装
        if outfit:
            parts.append(f"wearing {outfit}")

        # 场景
        scene_text = SCENE_PROMPTS.get(scene, f"in a {scene.replace('_', ' ')} setting")
        parts.append(scene_text)

        # 姿势
        if pose:
            parts.append(pose)

        # 情绪
        if emotion:
            parts.append(f"expressing {emotion}")

        # 构图
        parts.append(style_config["composition"])

        # 后缀
        parts.append(style_config["suffix"])

        # 额外标签
        if extra_tags:
            parts.append(extra_tags)

        # 相机
        if camera:
            parts.append(camera)

        prompt = ", ".join(p for p in parts if p)

        # 负向提示词
        neg = (
            f"{negative_prompt}, "
            "different face, different person, ugly, deformed, distorted, "
            "bad anatomy, extra limbs, watermark, signature, text, "
            "low quality, blurry, sketch, painting, cartoon, drawing, "
            "multiple people, group photo, cropped head"
        ) if negative_prompt else (
            "different face, different person, ugly, deformed, distorted, "
            "bad anatomy, extra limbs, watermark, signature, text, "
            "low quality, blurry, sketch, painting, cartoon, drawing, "
            "multiple people, group photo, cropped head"
        )

        return {
            "prompt": prompt,
            "negative_prompt": neg,
            "identity_token": identity_token,
        }
