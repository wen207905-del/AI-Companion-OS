"""Load status mod YAML configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from config import CONFIG_DIR

_MANIFEST = CONFIG_DIR / "status_mod" / "manifest.yaml"
_OUTFITS = CONFIG_DIR / "status_mod" / "outfits.yaml"
_ALIASES = CONFIG_DIR / "status_mod" / "scene_aliases.yaml"


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    if not _MANIFEST.is_file():
        return {"enabled": False, "variant": "off"}
    with open(_MANIFEST, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def load_outfits_config() -> dict:
    if not _OUTFITS.is_file():
        return {}
    with open(_OUTFITS, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def load_scene_aliases() -> dict:
    if not _ALIASES.is_file():
        return {}
    with open(_ALIASES, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def mod_variant() -> str:
    import os

    env = os.getenv("STATUS_MOD_VARIANT", "").strip().lower()
    if env in ("off", "v4", "v5"):
        return env
    cfg = load_manifest()
    if not cfg.get("enabled", False):
        return "off"
    return str(cfg.get("variant") or "off").lower()


def is_mod_enabled() -> bool:
    return mod_variant() in ("v4", "v5")
