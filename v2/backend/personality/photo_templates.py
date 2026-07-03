"""角色照片模版路径解析。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from config import CONFIG_DIR, PROJECT_ROOT

_TEMPLATES_YAML = CONFIG_DIR / "visual" / "character_photo_templates.yaml"
_DEFAULT_PARTS = (
    "neck", "ears", "lips", "chest", "waist", "back", "hips", "thighs", "inner_thigh"
)
_DEFAULT_SENSITIVITY = {
    "neck": 5,
    "ears": 5,
    "lips": 5,
    "chest": 5,
    "waist": 6,
    "back": 4,
    "hips": 5,
    "thighs": 6,
    "inner_thigh": 6,
}


@lru_cache(maxsize=1)
def _load_templates_config() -> dict:
    if not _TEMPLATES_YAML.exists():
        return {}
    with open(_TEMPLATES_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def template_dir() -> Path:
    cfg = _load_templates_config()
    rel = cfg.get("template_dir") or "character_templates"
    return PROJECT_ROOT / "config" / rel


def get_photo_url(character_id: str) -> str | None:
    """返回角色参考照片 URL（/static/character_templates/xxx.jpg）。"""
    cfg = _load_templates_config()
    entry = (cfg.get("characters") or {}).get(character_id) or {}
    filename = entry.get("template")
    if not filename:
        return None
    path = template_dir() / filename
    if not path.is_file():
        return None
    return f"/static/character_templates/{filename}"


def get_photo_template_meta(character_id: str) -> dict:
    cfg = _load_templates_config()
    entry = (cfg.get("characters") or {}).get(character_id) or {}
    return {
        "template": entry.get("template"),
        "note": entry.get("note"),
        "photo_url": get_photo_url(character_id),
    }


def default_sensitivity() -> dict[str, int]:
    return dict(_DEFAULT_SENSITIVITY)


def default_body_parts() -> tuple[str, ...]:
    return _DEFAULT_PARTS
