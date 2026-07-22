"""Detect characters mentioned in scene text."""

from __future__ import annotations

from mod.config_loader import load_scene_aliases


def detect_participants(text: str, persona_loader, *, active_character_id: str | None = None) -> list[str]:
    um = (text or "").strip()
    if not persona_loader:
        return []

    found: list[str] = []
    seen: set[str] = set()

    def _add(pid: str) -> None:
        if pid in persona_loader.personas and pid not in seen:
            seen.add(pid)
            found.append(pid)

    if active_character_id:
        _add(active_character_id)

    if not um:
        return found

    alias_cfg = load_scene_aliases()
    for pid, aliases in (alias_cfg.get("aliases") or {}).items():
        for alias in aliases or []:
            if alias and alias in um:
                _add(pid)
                break

    for hint, pid in (alias_cfg.get("location_hints") or {}).items():
        if hint in um:
            _add(str(pid))

    for pid in persona_loader.personas:
        name = persona_loader.get_display_name(pid)
        if not name or len(name) < 2:
            continue
        if name in um or f"@{name}" in um:
            _add(pid)
        ptype = str(persona_loader.get(pid).get("type") or "")
        if ptype and len(ptype) >= 2 and ptype in um:
            _add(pid)

    return found


def build_participant_labels(participant_ids: list[str], persona_loader) -> str:
    if not participant_ids:
        return "（未识别到具名角色；请根据场景合理推断，至少包含当前私聊对象）"
    parts = []
    for pid in participant_ids:
        name = persona_loader.get_display_name(pid)
        ptype = persona_loader.get(pid).get("type", "")
        parts.append(f"{pid}（{name}·{ptype}）" if ptype else f"{pid}（{name}）")
    return "、".join(parts)
