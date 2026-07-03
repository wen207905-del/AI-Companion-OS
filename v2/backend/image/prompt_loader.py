"""Load per-character image prompts from config/visual/character_image_prompts.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from config import CONFIG_DIR

_PROMPTS_YAML = CONFIG_DIR / "visual" / "character_image_prompts.yaml"


@lru_cache(maxsize=1)
def _load_config() -> dict:
    if not _PROMPTS_YAML.is_file():
        return {}
    with open(_PROMPTS_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def get_character_base_prompt(character_id: str) -> str:
    cfg = _load_config()
    entry = (cfg.get("characters") or {}).get(character_id) or {}
    return str(entry.get("base") or "").strip()


def get_default_exposure(character_id: str) -> str:
    cfg = _load_config()
    entry = (cfg.get("characters") or {}).get(character_id) or {}
    return str(entry.get("default_exposure") or "full_clothed").strip()


def get_global_style_suffix() -> str:
    cfg = _load_config()
    return str(cfg.get("style_suffix") or "").strip()
