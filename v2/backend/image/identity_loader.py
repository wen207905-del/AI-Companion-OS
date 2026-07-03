"""Load visual identity from config/visual/{char}/identity.yaml."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import yaml

from config import CONFIG_DIR
from personality.photo_templates import get_photo_url, template_dir

VISUAL_DIR = CONFIG_DIR / "visual"


def _flatten_identity(data: dict) -> dict:
    face = data.get("face") or {}
    body = data.get("body") or {}
    hair = data.get("hair") or {}
    aura = data.get("aura") or {}
    style = data.get("style") or {}

    marks = face.get("distinctive_marks") or body.get("distinctive_marks") or []
    marks_en = ", ".join(_mark_to_en(str(m)) for m in marks[:4])

    face_prompt = ", ".join(
        filter(
            None,
            [
                _token(face.get("face_shape"), "oval face"),
                _token(face.get("eye_shape"), "expressive eyes"),
                _token(face.get("eye_color"), "brown eyes"),
                _token(face.get("skin"), "natural skin"),
                _token(face.get("mouth"), "natural lips"),
                marks_en,
            ],
        )
    )

    body_prompt = ", ".join(
        filter(
            None,
            [
                _token(body.get("build"), "slender build"),
                f"height around {body.get('height_cm')}cm" if body.get("height_cm") else "",
            ],
        )
    )

    hair_prompt = " ".join(
        filter(
            None,
            [
                _token(hair.get("base_color"), "brown hair"),
                _token(hair.get("base_style"), "long hair"),
            ],
        )
    )

    visual_hash = data.get("visual_hash") or data.get("character_id", "unknown")
    seed = int(hashlib.md5(visual_hash.encode()).hexdigest()[:8], 16) % 999_999

    return {
        "character_id": data.get("character_id", ""),
        "visual_hash": visual_hash,
        "identity_seed": seed,
        "face_prompt_en": face_prompt,
        "body_prompt_en": body_prompt,
        "hair_default": hair_prompt,
        "aura_primary": _token(aura.get("primary"), "warm presence"),
        "gaze": _token(aura.get("gaze"), "natural gaze"),
        "style": style.get("render_style") or style.get("aesthetic") or "cinematic anime realism",
        "distinctive_marks": marks_en,
    }


def _token(value: str | None, fallback: str = "") -> str:
    if not value:
        return fallback
    return str(value).replace("_", " ")


def _mark_to_en(mark: str) -> str:
    """Keep short distinctive marks as descriptive English fragments."""
    mapping = {
        "眼线": "signature cat-eye eyeliner",
        "耳洞": "multiple ear piercings",
        "唇": "glossy lips",
        "痣": "beauty mark",
        "疤": "subtle scar",
        "酒窝": "dimples",
    }
    for key, en in mapping.items():
        if key in mark:
            return en
    return mark[:40]


@lru_cache(maxsize=32)
def load_identity(character_id: str) -> dict | None:
    path = VISUAL_DIR / character_id / "identity.yaml"
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    flat = _flatten_identity(data)
    flat["reference_image_path"] = _reference_file_path(character_id)
    flat["reference_image_url"] = get_photo_url(character_id)
    return flat


def _reference_file_path(character_id: str) -> str | None:
    from personality.photo_templates import _load_templates_config

    cfg = _load_templates_config()
    entry = (cfg.get("characters") or {}).get(character_id) or {}
    filename = entry.get("template")
    if not filename:
        return None
    path = template_dir() / filename
    return str(path) if path.is_file() else None
