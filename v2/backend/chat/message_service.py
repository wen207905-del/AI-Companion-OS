"""Edit and delete chat messages (private + group)."""

from __future__ import annotations

import sqlite3


class MessageError(ValueError):
    """Raised when a message operation is invalid."""


def ensure_message_schema(db: sqlite3.Connection) -> None:
    """Add edited flag column to message tables if missing."""
    for table in ("private_messages", "group_messages"):
        cols = {row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        if "edited" not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN edited INTEGER DEFAULT 0")
    db.commit()


def _normalize_content(content: str) -> str:
    text = (content or "").strip()
    if not text:
        raise MessageError("消息内容不能为空")
    if len(text) > 4000:
        raise MessageError("消息过长（最多 4000 字）")
    return text


def edit_private_message(
    db: sqlite3.Connection,
    character_id: str,
    message_id: str,
    content: str,
) -> dict:
    ensure_message_schema(db)
    text = _normalize_content(content)
    row = db.execute(
        "SELECT sender_type FROM private_messages WHERE id = ? AND character_id = ?",
        (message_id, character_id),
    ).fetchone()
    if row is None:
        raise MessageError("消息不存在")
    if row["sender_type"] != "user":
        raise MessageError("只能编辑你发送的消息")

    db.execute(
        "UPDATE private_messages SET content = ?, edited = 1 WHERE id = ?",
        (text, message_id),
    )
    db.execute(
        "UPDATE event_log SET raw_input = ? WHERE event_id = ?",
        (text, message_id),
    )
    db.execute(
        """
        UPDATE character_memories
        SET content = ?
        WHERE event_id = ? AND role = 'user'
        """,
        (text, message_id),
    )
    db.commit()
    return {"id": message_id, "content": text, "edited": True}


def delete_private_message(
    db: sqlite3.Connection,
    character_id: str,
    message_id: str,
) -> bool:
    ensure_message_schema(db)
    row = db.execute(
        "SELECT id FROM private_messages WHERE id = ? AND character_id = ?",
        (message_id, character_id),
    ).fetchone()
    if row is None:
        return False

    db.execute(
        "DELETE FROM private_messages WHERE id = ? AND character_id = ?",
        (message_id, character_id),
    )
    db.execute("DELETE FROM character_memories WHERE event_id = ?", (message_id,))
    db.execute("DELETE FROM event_log WHERE event_id = ?", (message_id,))
    db.commit()
    return True


def edit_group_message(
    db: sqlite3.Connection,
    group_id: str,
    message_id: str,
    content: str,
) -> dict:
    ensure_message_schema(db)
    text = _normalize_content(content)
    row = db.execute(
        "SELECT sender_type FROM group_messages WHERE id = ? AND chat_id = ?",
        (message_id, group_id),
    ).fetchone()
    if row is None:
        raise MessageError("消息不存在")
    if row["sender_type"] != "user":
        raise MessageError("只能编辑你发送的消息")

    db.execute(
        "UPDATE group_messages SET content = ?, edited = 1 WHERE id = ?",
        (text, message_id),
    )
    db.commit()
    return {"id": message_id, "content": text, "edited": True}


def delete_group_message(
    db: sqlite3.Connection,
    group_id: str,
    message_id: str,
) -> bool:
    ensure_message_schema(db)
    row = db.execute(
        "SELECT id FROM group_messages WHERE id = ? AND chat_id = ?",
        (message_id, group_id),
    ).fetchone()
    if row is None:
        return False

    db.execute(
        "DELETE FROM group_messages WHERE id = ? AND chat_id = ?",
        (message_id, group_id),
    )
    db.execute("DELETE FROM character_memories WHERE event_id = ?", (message_id,))
    db.commit()
    return True
