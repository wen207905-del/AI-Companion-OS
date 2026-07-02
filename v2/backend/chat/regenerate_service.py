"""Regenerate the latest character reply (private + group)."""

from __future__ import annotations

import sqlite3

from chat.message_service import MessageError


def prepare_private_regenerate(
    db: sqlite3.Connection,
    character_id: str,
    message_id: str,
) -> str:
    """Delete character reply and return the user message it was responding to."""
    row = db.execute(
        """
        SELECT sender_type, timestamp
        FROM private_messages
        WHERE id = ? AND character_id = ?
        """,
        (message_id, character_id),
    ).fetchone()
    if row is None:
        raise MessageError("消息不存在")
    if row["sender_type"] != "character":
        raise MessageError("只能重新生成角色的回复")

    latest = db.execute(
        """
        SELECT id FROM private_messages
        WHERE character_id = ? AND sender_type = 'character'
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (character_id,),
    ).fetchone()
    if not latest or latest["id"] != message_id:
        raise MessageError("只能重新生成最近一条角色回复")

    ts = row["timestamp"]
    user_row = db.execute(
        """
        SELECT content FROM private_messages
        WHERE character_id = ? AND sender_type = 'user' AND timestamp < ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (character_id, ts),
    ).fetchone()
    if not user_row or not (user_row["content"] or "").strip():
        raise MessageError("找不到对应的用户消息，无法重新生成")

    user_content = user_row["content"].strip()
    db.execute("DELETE FROM private_messages WHERE id = ?", (message_id,))
    db.execute("DELETE FROM character_memories WHERE event_id = ?", (message_id,))
    db.commit()
    return user_content


def prepare_group_regenerate(
    db: sqlite3.Connection,
    group_id: str,
    message_id: str,
) -> tuple[str, str]:
    """Delete group character reply; return (character_id, preceding user message)."""
    row = db.execute(
        """
        SELECT sender_type, sender_id, timestamp
        FROM group_messages
        WHERE id = ? AND chat_id = ?
        """,
        (message_id, group_id),
    ).fetchone()
    if row is None:
        raise MessageError("消息不存在")
    if row["sender_type"] != "character":
        raise MessageError("只能重新生成角色的回复")

    char_id = row["sender_id"]
    latest = db.execute(
        """
        SELECT id FROM group_messages
        WHERE chat_id = ? AND sender_type = 'character' AND sender_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (group_id, char_id),
    ).fetchone()
    if not latest or latest["id"] != message_id:
        raise MessageError("只能重新生成该角色最近一条回复")

    ts = row["timestamp"]
    user_row = db.execute(
        """
        SELECT content FROM group_messages
        WHERE chat_id = ? AND sender_type = 'user' AND timestamp < ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (group_id, ts),
    ).fetchone()
    if not user_row or not (user_row["content"] or "").strip():
        raise MessageError("找不到对应的用户消息，无法重新生成")

    user_content = user_row["content"].strip()
    db.execute("DELETE FROM group_messages WHERE id = ?", (message_id,))
    db.execute("DELETE FROM character_memories WHERE event_id = ?", (message_id,))
    db.commit()
    return char_id, user_content
