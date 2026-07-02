"""Group chat management — create groups, members, character chain replies."""

from __future__ import annotations

import time
import uuid
from typing import Any

from app_state import state
from api.ws_hub import hub
from chat import llm_prefs
from chat.context_builder import memory_block_for_group
from chat.history_loader import load_group_history_for_character
from chat.prompt_builder import PromptBuilder
from chat.reply_service import decide_character_chain
from chat.stream_delivery import deliver_character_reply
from llm import router as llm_router


def list_groups(db) -> list[dict[str, Any]]:
    cur = db.execute(
        """
        SELECT g.id, g.name, g.type, g.created_at, g.mode,
               COUNT(m.character_id) AS member_count
        FROM group_chats g
        LEFT JOIN group_chat_members m ON m.chat_id = g.id
        GROUP BY g.id
        ORDER BY g.created_at ASC
        """
    )
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "mode": row["mode"],
            "created_at": row["created_at"],
            "member_count": row["member_count"],
        }
        for row in cur.fetchall()
    ]


def get_group(db, group_id: str) -> dict[str, Any] | None:
    cur = db.execute(
        "SELECT id, name, type, created_at, mode FROM group_chats WHERE id = ?",
        (group_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    cur = db.execute(
        "SELECT character_id, joined_at FROM group_chat_members WHERE chat_id = ? ORDER BY joined_at",
        (group_id,),
    )
    members = [r["character_id"] for r in cur.fetchall()]
    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "mode": row["mode"],
        "created_at": row["created_at"],
        "members": members,
    }


def create_group(db, name: str, member_ids: list[str], persona_loader) -> dict[str, Any]:
    valid = [m for m in member_ids if persona_loader.get(m)]
    if not valid:
        raise ValueError("至少选择一名角色")
    group_id = f"grp_{uuid.uuid4().hex[:10]}"
    now = time.time()
    db.execute(
        "INSERT INTO group_chats (id, name, type, created_at, mode) VALUES (?, ?, ?, ?, ?)",
        (group_id, name.strip() or "新群聊", "custom", now, "free"),
    )
    valid = [m for m in member_ids if persona_loader.get(m)]
    for pid in valid:
        db.execute(
            "INSERT OR IGNORE INTO group_chat_members (chat_id, character_id, joined_at) VALUES (?, ?, ?)",
            (group_id, pid, now),
        )
    db.commit()
    state.group_members[group_id] = set(valid)
    return get_group(db, group_id) or {"id": group_id, "name": name, "members": valid}


def add_member(db, group_id: str, character_id: str) -> bool:
    if not state.persona_loader.get(character_id):
        return False
    cur = db.execute("SELECT id FROM group_chats WHERE id = ?", (group_id,))
    if cur.fetchone() is None:
        return False
    db.execute(
        "INSERT OR IGNORE INTO group_chat_members (chat_id, character_id, joined_at) VALUES (?, ?, ?)",
        (group_id, character_id, time.time()),
    )
    db.commit()
    members = state.group_members.get(group_id, set())
    members.add(character_id)
    state.group_members[group_id] = members
    return True


def remove_member(db, group_id: str, character_id: str) -> bool:
    db.execute(
        "DELETE FROM group_chat_members WHERE chat_id = ? AND character_id = ?",
        (group_id, character_id),
    )
    db.commit()
    members = state.group_members.get(group_id, set())
    members.discard(character_id)
    state.group_members[group_id] = members
    return True


def delete_group(db, group_id: str) -> bool:
    cur = db.execute("SELECT type FROM group_chats WHERE id = ?", (group_id,))
    row = cur.fetchone()
    if not row:
        return False
    llm_prefs.ensure_table(db)
    db.execute("DELETE FROM group_chat_members WHERE chat_id = ?", (group_id,))
    db.execute("DELETE FROM group_messages WHERE chat_id = ?", (group_id,))
    db.execute(
        "DELETE FROM chat_llm_prefs WHERE scope_type = 'group' AND scope_id = ?",
        (group_id,),
    )
    db.execute(
        "DELETE FROM character_memories WHERE scope = 'group' AND scope_id = ?",
        (group_id,),
    )
    db.execute("DELETE FROM group_chats WHERE id = ?", (group_id,))
    db.commit()
    state.group_members.pop(group_id, None)
    return True


async def maybe_run_character_chain(
    room: str,
    *,
    group_id: str,
    group_name: str,
    members: set[str],
    user_message: str,
    recent_replies: list[tuple[str, str, str]],
    llm_choice: dict | None,
) -> None:
    """One optional character responds to another character's message."""
    if len(recent_replies) < 1:
        return

    chain_char = await decide_character_chain(
        user_message,
        recent_replies,
        list(members),
        state.persona_loader,
        state.emo_engine,
    )
    if not chain_char:
        return

    target_id, target_name, target_content = recent_replies[-1]
    if chain_char == target_id:
        if len(recent_replies) >= 2:
            target_id, target_name, target_content = recent_replies[-2]
        else:
            return

    persona = state.persona_loader.get(chain_char)
    if not persona:
        return

    await hub.send_room(room, {
        "type": "typing",
        "group_id": group_id,
        "character_id": chain_char,
        "character_name": persona.get("name", chain_char),
    })

    group_rel = state.rel_engine.get_summary(chain_char)
    group_emo = state.emo_engine.get_summary(chain_char)
    other_names = [
        state.persona_loader.get_display_name(m)
        for m in members if m != chain_char
    ]
    group_hist = load_group_history_for_character(
        state.db, group_id, state.persona_loader, chain_char,
        list(members), limit=20,
    )
    builder = PromptBuilder(persona)
    memory_text = memory_block_for_group(chain_char, user_message, group_id)
    llm_messages = builder.build_group_chain_messages(
        group_emo,
        group_rel,
        group_name,
        other_names,
        user_message,
        target_name,
        target_content,
        history=group_hist,
        memory_text=memory_text,
        member_ids=list(members),
        character_id=chain_char,
        persona_loader=state.persona_loader,
    )

    reply_id = f"msg_{uuid.uuid4().hex[:12]}"

    def _save(rid, content, action, inner_thought, ts):
        import json as _json
        state.db.execute(
            """INSERT INTO group_messages
               (id, chat_id, sender_type, sender_id, content, action, inner_thought, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (rid, group_id, "character", chain_char,
             content,
             _json.dumps(action, ensure_ascii=False) if action else None,
             inner_thought, ts),
        )
        state.db.commit()

    await deliver_character_reply(
        room,
        reply_id=reply_id,
        llm_messages=llm_messages,
        persona=persona,
        rel_summary=group_rel,
        llm_choice=llm_choice,
        ws_meta={
            "group_id": group_id,
            "character_id": chain_char,
            "sender_type": "character",
            "sender_id": chain_char,
        },
        save_to_db=_save,
        memory_scope="group",
        memory_scope_id=group_id,
        present_members=list(members),
        group_name=group_name,
    )

    await hub.send_room(room, {
        "type": "typing_end",
        "group_id": group_id,
        "character_id": chain_char,
    })
