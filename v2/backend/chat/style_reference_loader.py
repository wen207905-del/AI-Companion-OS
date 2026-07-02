"""Load scoped style reference guides for private vs group chat prompts."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from config import PROJECT_ROOT, STYLE_REFERENCE_ENABLED

_STYLE_DIR = PROJECT_ROOT / "config" / "style_references"
_MANIFEST_PATH = _STYLE_DIR / "manifest.yaml"

_DEFAULT_MANIFEST: dict[str, Any] = {
    "scopes": {
        "private": {
            "title": "私聊",
            "max_chars": 12000,
            "guides": ["private/cg_novel_style_guide.md"],
            "extras_dir": "private/extras",
        },
        "group": {
            "title": "群聊",
            "max_chars": 6000,
            "guides": ["group/group_chat_style_guide.md"],
            "extras_dir": "group/extras",
        },
    }
}


def _load_manifest() -> dict[str, Any]:
    if not _MANIFEST_PATH.is_file():
        return _DEFAULT_MANIFEST
    try:
        data = yaml.safe_load(_MANIFEST_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("scopes"):
            return data
    except Exception:
        pass
    return _DEFAULT_MANIFEST


def _read_guide_file(rel_path: str) -> str:
    path = _STYLE_DIR / rel_path
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _collect_extras(extras_rel: str) -> list[str]:
    extras_dir = _STYLE_DIR / extras_rel
    if not extras_dir.is_dir():
        return []
    parts: list[str] = []
    for fp in sorted(extras_dir.iterdir()):
        if not fp.is_file():
            continue
        if fp.suffix.lower() not in (".md", ".txt"):
            continue
        if fp.name.startswith("."):
            continue
        text = fp.read_text(encoding="utf-8").strip()
        if text:
            parts.append(f"\n\n---\n\n## 追加参考：{fp.name}\n\n{text}")
    return parts


@lru_cache(maxsize=8)
def load_style_guides(scope: str = "private") -> str:
    """Load merged guide text for scope: private | group."""
    if not STYLE_REFERENCE_ENABLED:
        return ""

    manifest = _load_manifest()
    scope_cfg = manifest.get("scopes", {}).get(scope)
    if not scope_cfg:
        return ""

    chunks: list[str] = []
    for rel in scope_cfg.get("guides") or []:
        text = _read_guide_file(str(rel))
        if text:
            chunks.append(text)

    extras_dir = scope_cfg.get("extras_dir")
    if extras_dir:
        chunks.extend(_collect_extras(str(extras_dir)))

    if not chunks:
        return ""

    merged = "\n\n---\n\n".join(chunks)
    max_chars = int(scope_cfg.get("max_chars") or 8000)
    if len(merged) > max_chars:
        merged = (
            merged[:max_chars]
            + f"\n\n（{scope} 参考文档已截断，完整版见 config/style_references/）"
        )
    return merged


def style_reference_block(scope: str = "private") -> str:
    guide = load_style_guides(scope)
    if not guide:
        return ""

    from config import USER_NAME, USER_NICKNAME

    guide = guide.replace("{USER_NAME}", USER_NAME).replace("{USER_NICKNAME}", USER_NICKNAME)

    manifest = _load_manifest()
    title = manifest.get("scopes", {}).get(scope, {}).get("title") or scope
    return (
        f"\n\n【写作风格参考 · {title}——每轮回复必须对齐，优先级仅次于角色人设】\n"
        + guide
    )


def clear_style_cache() -> None:
    load_style_guides.cache_clear()


# 兼容旧接口
def load_style_guide() -> str:
    return load_style_guides("private")
