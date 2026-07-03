"""Load conversation history from SQLite for LLM context."""

from __future__ import annotations

import time

from chat.group_context import (
    visible_user_message_for_character,
)
from config import USER_NAME

PRIVATE_BRIDGE_MAX_AGE_SECONDS = 3 * 3600
PRIVATE_BRIDGE_MESSAGE_LIMIT = 8
PRIVATE_BRIDGE_SNIPPET_CHARS = 180


def load_private_history(db_conn, character_id: str, limit: int = 20) -> list[dict[str, str]]:
    """Return recent private messages as OpenAI-style role/content pairs (chronological)."""
    cur = db_conn.execute(
        """
        SELECT sender_type, content, content_type
        FROM private_messages
        WHERE character_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (character_id, limit),
    )
    rows = cur.fetchall()
    history: list[dict[str, str]] = []
    for row in reversed(rows):
        if (row["content_type"] or "text") == "image":
            continue
        role = "user" if row["sender_type"] == "user" else "assistant"
        content = (row["content"] or "").strip()
        if content:
            history.append({"role": role, "content": content})
    return history


def load_private_history_for_api(db_conn, character_id: str, limit: int = 50) -> list[dict]:
    """Return message records for REST API (chronological)."""
    cur = db_conn.execute(
        """
        SELECT id, sender_type, content, action, inner_thought, content_type, timestamp, edited
        FROM private_messages
        WHERE character_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (character_id, limit),
    )
    rows = cur.fetchall()
    messages = []
    for row in reversed(rows):
        messages.append({
            "id": row["id"],
            "sender_type": row["sender_type"],
            "content": row["content"],
            "content_type": row["content_type"] or "text",
            "action": row["action"],
            "inner_thought": row["inner_thought"],
            "timestamp": row["timestamp"],
            "edited": bool(row["edited"]) if "edited" in row.keys() else False,
        })
    return messages


def load_group_history_for_api(db_conn, group_id: str, limit: int = 100) -> list[dict]:
    """Return group message records for REST API (chronological)."""
    cur = db_conn.execute(
        """
        SELECT id, sender_type, sender_id, content, action, inner_thought, timestamp, edited
        FROM group_messages
        WHERE chat_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (group_id, limit),
    )
    rows = cur.fetchall()
    messages = []
    for row in reversed(rows):
        messages.append({
            "id": row["id"],
            "sender_type": row["sender_type"],
            "sender_id": row["sender_id"],
            "content": row["content"],
            "action": row["action"],
            "inner_thought": row["inner_thought"],
            "timestamp": row["timestamp"],
            "edited": bool(row["edited"]) if "edited" in row.keys() else False,
        })
    return messages


def load_group_history(
    db_conn,
    group_id: str,
    persona_loader,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Return recent group messages as OpenAI-style pairs for LLM context."""
    cur = db_conn.execute(
        """
        SELECT sender_type, sender_id, content
        FROM group_messages
        WHERE chat_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (group_id, limit),
    )
    rows = cur.fetchall()
    history: list[dict[str, str]] = []
    for row in reversed(rows):
        content = (row["content"] or "").strip()
        if not content:
            continue
        if row["sender_type"] == "user":
            history.append({"role": "user", "content": f"{USER_NAME}：{content}"})
        else:
            name = persona_loader.get_display_name(row["sender_id"])
            history.append({"role": "assistant", "content": f"{name}：{content}"})
    return history


def load_group_history_for_character(
    db_conn,
    group_id: str,
    persona_loader,
    character_id: str,
    member_ids: list[str] | None = None,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Group history with per-character visibility for private scene messages."""
    cur = db_conn.execute(
        """
        SELECT sender_type, sender_id, content
        FROM group_messages
        WHERE chat_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (group_id, limit),
    )
    rows = cur.fetchall()
    history: list[dict[str, str]] = []
    for row in reversed(rows):
        content = (row["content"] or "").strip()
        if not content:
            continue
        if row["sender_type"] == "user":
            visible = visible_user_message_for_character(
                content, character_id, member_ids, persona_loader,
            )
            history.append({"role": "user", "content": f"{USER_NAME}：{visible}"})
        else:
            name = persona_loader.get_display_name(row["sender_id"])
            history.append({"role": "assistant", "content": f"{name}：{content}"})
    return history


def load_recent_private_bridge(
    db_conn,
    character_id: str,
    character_name: str,
    *,
    limit: int = PRIVATE_BRIDGE_MESSAGE_LIMIT,
    max_age_seconds: int = PRIVATE_BRIDGE_MAX_AGE_SECONDS,
) -> str:
    """
    Format very recent private chat as continuity block for group prompts.
    Returns empty if no recent private messages or last message is too old.
    """
    cur = db_conn.execute(
        """
        SELECT sender_type, content, timestamp
        FROM private_messages
        WHERE character_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (character_id, limit),
    )
    rows = list(cur.fetchall())
    if not rows:
        return ""

    newest_ts = float(rows[0]["timestamp"])
    if time.time() - newest_ts > max_age_seconds:
        return ""

    lines = [
        f"【私聊延续——必读】你与{USER_NAME}刚才还在私聊，以下内容真实发生过：",
    ]
    for row in reversed(rows):
        content = (row["content"] or "").strip()
        if not content:
            continue
        if len(content) > PRIVATE_BRIDGE_SNIPPET_CHARS:
            content = content[:PRIVATE_BRIDGE_SNIPPET_CHARS].rstrip() + "…"
        if row["sender_type"] == "user":
            lines.append(f"- {USER_NAME}：{content}")
        else:
            lines.append(f"- {character_name}（你）：{content}")

    lines.extend([
        "",
        "进入群聊后：",
        f"1. 自然延续上述私聊话题，可带过「刚才私聊里说的…」",
        f"2. 禁止完全无视私聊、突然换到无关话题",
        f"3. 群内其他人默认不知道私聊细节，除非你主动提起或剧情上他们已在场",
    ])
    return "\n".join(lines)
