"""Record group chat events as group-scoped memories for present members."""

from __future__ import annotations

from typing import Iterable

from app_state import state
from chat.group_context import visible_user_message_for_character
from config import USER_NAME


def _snapshot(group_name: str, speaker_name: str, content: str) -> str:
    text = (content or "").strip()
    if not text:
        return ""
    name = speaker_name or "?"
    return f"[群聊·{group_name or '群聊'}] {name}：{text[:200]}"


def record_group_message_for_present(
    present_member_ids: Iterable[str],
    *,
    group_id: str,
    group_name: str,
    sender_type: str,
    sender_id: str,
    sender_name: str,
    content: str,
    event_id: str | None = None,
    intensity: float = 55.0,
) -> None:
    """Write the same group scene into every on-site character's group memory."""
    mm = state.memory_manager
    if not mm or not group_id:
        return

    role = "user" if sender_type == "user" else "character"
    members = [m for m in present_member_ids if m and m != "user"]
    pl = state.persona_loader

    for char_id in members:
        store_text = content
        if sender_type == "user" and pl:
            store_text = visible_user_message_for_character(
                content, char_id, members, pl,
            )
        snap = _snapshot(group_name, sender_name, store_text)
        if not snap:
            continue
        mm.store(
            char_id,
            snap,
            role=role,
            scope="group",
            scope_id=group_id,
            event_id=event_id,
            intensity=intensity,
        )


def record_group_user_message(
    present_member_ids: Iterable[str],
    *,
    group_id: str,
    group_name: str,
    content: str,
    event_id: str | None = None,
) -> None:
    record_group_message_for_present(
        present_member_ids,
        group_id=group_id,
        group_name=group_name,
        sender_type="user",
        sender_id="user",
        sender_name=USER_NAME,
        content=content,
        event_id=event_id,
        intensity=55.0,
    )


def record_group_character_message(
    present_member_ids: Iterable[str],
    *,
    group_id: str,
    group_name: str,
    speaker_id: str,
    speaker_name: str,
    content: str,
    event_id: str | None = None,
) -> None:
    record_group_message_for_present(
        present_member_ids,
        group_id=group_id,
        group_name=group_name,
        sender_type="character",
        sender_id=speaker_id,
        sender_name=speaker_name,
        content=content,
        event_id=event_id,
        intensity=60.0,
    )
