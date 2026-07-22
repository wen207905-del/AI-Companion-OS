"""Route between chat mode and scene mode."""

from __future__ import annotations

import re

_SCENE_MARKERS = (
    "推开门", "走进", "看见", "都在", "客厅里", "房间里", "场景", "同时",
    "一起", "几个人", "在场", "此时", "这时", "突然", "旁边", "身后",
)
_SCENE_PATTERN = re.compile(
    r"(我|你)?(推|走|进|看|见|来到|进入).{0,12}(看见|看到|发现|注意到)",
)


def is_scene_input(text: str, participant_count: int = 0) -> bool:
    um = (text or "").strip()
    if not um:
        return False
    # 仅提到多名角色不足以进入长篇场景（V4.2）；需明确场景线索
    if _SCENE_PATTERN.search(um):
        return True
    hits = sum(1 for m in _SCENE_MARKERS if m in um)
    return hits >= 2


def resolve_mode(
    user_message: str,
    explicit_mode: str | None = None,
    *,
    participant_count: int = 0,
    default: str = "chat",
) -> str:
    if explicit_mode in ("chat", "scene"):
        return explicit_mode
    if is_scene_input(user_message, participant_count):
        return "scene"
    return default if default in ("chat", "scene") else "chat"
