"""V4 prompt composer — identity + emotion + scene + action."""

from __future__ import annotations

from image.config import DEFAULT_NEGATIVE, IMAGE_DEFAULT_STYLE
from image.identity_loader import load_identity

SCENE_PROMPTS = {
    "bedroom": "cozy bedroom, soft warm lamp light, rumpled sheets, intimate atmosphere",
    "bedroom_night": "dim bedroom at night, warm bedside lamp, quiet intimate mood",
    "bathroom": "modern bathroom, steam from shower, foggy mirror, warm tiles",
    "kitchen": "bright home kitchen, natural daylight, lived-in warmth",
    "cafe": "charming cafe interior, window light, coffee on table",
    "living_room": "comfortable living room, ambient warm lighting",
    "outdoor": "outdoor natural light, soft background bokeh",
}

STYLE_SUFFIX = {
    "selfie": "smartphone selfie, close-up portrait, natural skin texture, sharp eyes",
    "portrait": "85mm portrait lens, shallow depth of field, cinematic lighting",
    "full_body": "full body in frame, editorial photography, clean composition",
    "candid": "candid moment, photojournalistic, authentic emotion",
    "cinematic_portrait": "cinematic anime realism, film grain subtle, 8k detail, soft shadows",
}


def compose_prompt(
    character_id: str,
    *,
    scene: str = "bedroom",
    style: str = "",
    outfit: str = "",
    pose: str = "",
    emotion: str = "",
    exposure: str = "full_clothed",
    extra: str = "",
    multi_characters: list[str] | None = None,
) -> dict:
    identity = load_identity(character_id) or {}
    style_key = style or IMAGE_DEFAULT_STYLE
    style_suffix = STYLE_SUFFIX.get(style_key, STYLE_SUFFIX["cinematic_portrait"])
    scene_text = SCENE_PROMPTS.get(scene, SCENE_PROMPTS.get("bedroom", scene))

    identity_block = ""
    if identity:
        identity_block = (
            f"Same consistent character: {identity.get('face_prompt_en', '')}. "
            f"{identity.get('body_prompt_en', '')}. "
            f"Hair: {identity.get('hair_default', '')}. "
            f"{identity.get('distinctive_marks', '')}. "
            f"Maintain exact face structure from reference image."
        )

    emotion_block = f"Expression and mood: {emotion or 'natural relaxed expression'}."
    outfit_block = outfit or _exposure_prompt(exposure)
    pose_block = f"Pose and action: {pose or 'natural relaxed pose, looking at viewer'}."
    scene_block = f"Scene: {scene_text}."

    if multi_characters and len(multi_characters) > 1:
        names = ", ".join(multi_characters)
        scene_block += f" Multiple characters in frame: {names}, balanced composition."

    prompt = " ".join(
        filter(
            None,
            [identity_block, emotion_block, scene_block, pose_block, outfit_block, style_suffix, extra],
        )
    )

    return {
        "prompt": prompt.strip(),
        "negative_prompt": DEFAULT_NEGATIVE,
        "identity_seed": identity.get("identity_seed"),
        "style": style_key,
        "scene": scene,
    }


def _exposure_prompt(exposure: str) -> str:
    mapping = {
        "full_clothed": "fully dressed, detailed outfit visible",
        "casual_home": "casual home clothes, relaxed domestic outfit",
        "sleepwear": "soft sleepwear, comfortable night clothes",
        "partial": "partially undressed, open clothing, sensual but artistic",
        "towel": "wrapped in bath towel after shower, damp hair",
        "nude": "nude artistic portrait, natural body, tasteful composition",
        "implied": "implied nudity with strategic lighting and shadows",
    }
    return mapping.get(exposure, mapping["full_clothed"])
