"""Detect characters mentioned in scene text."""

from __future__ import annotations


def detect_participants(text: str, persona_loader) -> list[str]:
    um = (text or "").strip()
    if not um or not persona_loader:
        return []

    found: list[str] = []
    for pid in persona_loader.personas:
        name = persona_loader.get_display_name(pid)
        if not name or len(name) < 2:
            continue
        if name in um or f"@{name}" in um:
            found.append(pid)
    return found


def build_participant_labels(participant_ids: list[str], persona_loader) -> str:
    if not participant_ids:
        return "（未识别到具名角色）"
    parts = []
    for pid in participant_ids:
        name = persona_loader.get_display_name(pid)
        parts.append(f"{pid}（{name}）")
    return "、".join(parts)
