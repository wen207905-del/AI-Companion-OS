"""Parse user intent for image generation from chat text."""

from __future__ import annotations

import re

SCENE_KEYWORDS = {
    "bedroom": ("卧室", "床上", "房间", "bedroom", "bed"),
    "bedroom_night": ("夜里", "夜晚", "关灯", "night"),
    "bathroom": ("浴室", "洗澡", "淋浴", "泡澡", "bath", "shower"),
    "kitchen": ("厨房", "做饭", "kitchen"),
    "cafe": ("咖啡", "cafe", "café"),
    "living_room": ("客厅", "沙发", "living room"),
    "outdoor": ("外面", "户外", "公园", "outdoor"),
}

EXPOSURE_KEYWORDS = {
    "towel": ("浴巾", "毛巾", "towel"),
    "sleepwear": ("睡衣", "睡裙", "sleepwear"),
    "partial": ("半裸", "敞开", "partial", "undress"),
    "nude": ("裸", "nude", "裸体"),
    "casual_home": ("居家", "T恤", "casual"),
}

STYLE_KEYWORDS = {
    "selfie": ("自拍", "selfie"),
    "full_body": ("全身", "full body"),
    "candid": ("抓拍", "candid"),
    "portrait": ("肖像", "portrait", "特写"),
}


def parse_image_intent(text: str) -> dict:
    """Extract scene/style/exposure hints from natural language."""
    lower = text.lower()
    result = {
        "scene": "bedroom",
        "style": "cinematic_portrait",
        "exposure": "full_clothed",
        "emotion": "",
        "pose": "",
        "extra": text.strip()[:200],
    }

    for scene, keys in SCENE_KEYWORDS.items():
        if any(k in text or k in lower for k in keys):
            result["scene"] = scene
            break

    for exposure, keys in EXPOSURE_KEYWORDS.items():
        if any(k in text or k in lower for k in keys):
            result["exposure"] = exposure
            break

    for style, keys in STYLE_KEYWORDS.items():
        if any(k in text or k in lower for k in keys):
            result["style"] = style
            break

    emo_match = re.search(r"(害羞|开心|生气|委屈|诱惑|慵懒|温柔|shy|smile|seductive)", text, re.I)
    if emo_match:
        result["emotion"] = emo_match.group(1)

    return result
