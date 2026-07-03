"""
V4 Visual Identity Lock — 角色视觉身份锁定

每个角色有固定的视觉档案，确保生图时外观一致。
"""

import json
import os
from typing import Optional

# ── 默认 Identity Profile ──
DEFAULT_PROFILE = {
    "face_shape": "oval",
    "eyes": "almond-shaped brown eyes",
    "nose": "straight",
    "mouth": "medium lips with slight smile",
    "skin_tone": "fair with warm undertone",
    "height": "165cm",
    "body_ratio": "slim hourglass",
    "hair_color": "dark brown",
    "hair_length": "shoulder-length",
    "hair_style": "soft waves",
    "distinguishing_features": "small mole below left eye",
    "age_appearance": "mid-20s",
    "overall_vibe": "gentle, elegant, approachable",
}

# ── Identity Token 模板 ──
IDENTITY_TOKEN_TEMPLATE = (
    "Same person with {face_shape} face, {eyes}, {nose}, {mouth}, "
    "{skin_tone} skin, {height} height, {body_ratio} body, "
    "{hair_color} {hair_length} hair in {hair_style}, "
    "{distinguishing_features}. Appears {age_appearance}, {overall_vibe}."
)


class IdentityLock:
    """角色视觉身份锁定。

    每个角色独立的 identity profile（YAML/JSON），
    生成图片时注入 identity token 确保一致性。
    """

    def __init__(self, profiles_dir: str = None, db=None):
        self.db = db
        self.profiles_dir = profiles_dir or os.path.join(
            os.path.dirname(__file__), "profiles"
        )
        self._profiles: dict = {}  # char_id → profile dict

    def create_profile(self, character_id: str, profile: dict = None) -> dict:
        """创建/覆盖角色视觉档案。"""
        data = dict(DEFAULT_PROFILE)
        if profile:
            data.update(profile)
        self._profiles[character_id] = data

        # 持久化到 JSON
        os.makedirs(self.profiles_dir, exist_ok=True)
        filepath = os.path.join(self.profiles_dir, f"{character_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 数据库
        if self.db:
            try:
                self.db.upsert_visual_profile(character_id, json.dumps(data))
            except Exception:
                pass

        return data

    def get_profile(self, character_id: str) -> dict:
        """获取角色视觉档案。"""
        if character_id in self._profiles:
            return dict(self._profiles[character_id])

        # 从文件加载
        filepath = os.path.join(self.profiles_dir, f"{character_id}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._profiles[character_id] = data
            return dict(data)

        # 数据库
        if self.db:
            try:
                row = self.db.get_visual_profile(character_id)
                if row:
                    if isinstance(row, dict):
                        data = row.get("profile_data")
                        if isinstance(data, str):
                            data = json.loads(data)
                    else:
                        data = row
                    self._profiles[character_id] = data
                    return dict(data)
            except Exception:
                pass

        return dict(DEFAULT_PROFILE)

    def build_identity_token(self, character_id: str) -> str:
        """构建 identity token（注入生图 prompt）。"""
        p = self.get_profile(character_id)
        return IDENTITY_TOKEN_TEMPLATE.format(
            face_shape=p.get("face_shape", ""),
            eyes=p.get("eyes", ""),
            nose=p.get("nose", ""),
            mouth=p.get("mouth", ""),
            skin_tone=p.get("skin_tone", ""),
            height=p.get("height", ""),
            body_ratio=p.get("body_ratio", ""),
            hair_color=p.get("hair_color", ""),
            hair_length=p.get("hair_length", ""),
            hair_style=p.get("hair_style", ""),
            distinguishing_features=p.get("distinguishing_features", ""),
            age_appearance=p.get("age_appearance", ""),
            overall_vibe=p.get("overall_vibe", ""),
        )
