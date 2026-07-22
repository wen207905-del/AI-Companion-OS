"""Server-authoritative Fate Dice group game."""

from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any

from config import USER_NICKNAME

_GAME_LOCK = threading.RLock()


def _synchronized(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with _GAME_LOCK:
            return function(*args, **kwargs)
    return wrapped


CATALOG_ENTRY = {
    "id": "fate_dice",
    "title": "命运骰子",
    "icon": "🎲",
    "rules_version": "1.0",
    "status": "available",
    "summary": "按顺序掷 1～150 点，单轮最高者得 1 分，默认三轮后总分最高者获胜。",
    "rules": [
        "服务端生成点数，客户端不能指定结果",
        "严格按座位顺序行动，每人每轮只能掷一次",
        "每轮最高点获得 1 分；并列最高者各得 1 分",
        "默认进行 3 轮；最终同分时允许并列获胜",
        "重复点击使用幂等键，不会多掷一次",
    ],
    "settings": {
        "total_rounds": {"type": "integer", "min": 1, "max": 10, "default": 3},
    },
}


class GameError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _json_load(raw: str | None, default):
    try:
        return json.loads(raw) if raw else default
    except (TypeError, ValueError):
        return default


def _secure_randint(low: int, high: int) -> int:
    return secrets.randbelow(high - low + 1) + low


def _participants(db, session_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        """SELECT participant_type, participant_ref_id, display_name, seat_no, score, status
           FROM game_participants WHERE session_id = ? ORDER BY seat_no ASC""",
        (session_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _session_response(db, row, *, replayed: bool = False) -> dict[str, Any]:
    participants = _participants(db, row["id"])
    state = _json_load(row["public_state_json"], {})
    current = None
    index = int(row["current_turn_index"])
    if row["status"] == "running" and 0 <= index < len(participants):
        current = participants[index]

    return {
        "id": row["id"],
        "group_id": row["group_id"],
        "game_type": row["game_type"],
        "rules_version": row["rules_version"],
        "status": row["status"],
        "round_no": row["round_no"],
        "state_version": row["state_version"],
        "settings": _json_load(row["settings_json"], {}),
        "participants": participants,
        "current_turn": current,
        "round_rolls": state.get("round_rolls", {}),
        "round_history": state.get("round_history", []),
        "last_event": state.get("last_event"),
        "winners": _json_load(row["winner_json"], []),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "finished_at": row["finished_at"],
        "idempotent_replay": replayed,
    }


def get_session(db, session_id: str) -> dict[str, Any]:
    row = db.execute("SELECT * FROM game_sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise GameError("session_not_found", "游戏会话不存在", 404)
    return _session_response(db, row)


def get_current_session(db, group_id: str) -> dict[str, Any] | None:
    row = db.execute(
        """SELECT * FROM game_sessions
           WHERE group_id = ? AND status = 'running'
           ORDER BY updated_at DESC LIMIT 1""",
        (group_id,),
    ).fetchone()
    return _session_response(db, row) if row else None


def _default_participants(db, group_id: str, persona_loader) -> list[dict[str, str]]:
    rows = db.execute(
        """SELECT character_id FROM group_chat_members
           WHERE chat_id = ? ORDER BY joined_at ASC, character_id ASC""",
        (group_id,),
    ).fetchall()
    result = [{
        "participant_type": "user",
        "participant_ref_id": "user",
        "display_name": USER_NICKNAME or "我",
    }]
    for row in rows:
        char_id = row["character_id"]
        if persona_loader.get(char_id):
            result.append({
                "participant_type": "character",
                "participant_ref_id": char_id,
                "display_name": persona_loader.get_display_name(char_id),
            })
    return result


@_synchronized
def create_session(
    db,
    group_id: str,
    persona_loader,
    *,
    total_rounds: int = 3,
) -> dict[str, Any]:
    group = db.execute("SELECT id FROM group_chats WHERE id = ?", (group_id,)).fetchone()
    if not group:
        raise GameError("group_not_found", "群聊不存在", 404)
    if not 1 <= int(total_rounds) <= 10:
        raise GameError("invalid_rounds", "总轮数必须在 1～10 之间")
    if get_current_session(db, group_id):
        raise GameError("active_session_exists", "该群已有进行中的游戏", 409)

    participants = _default_participants(db, group_id, persona_loader)
    if len(participants) < 2:
        raise GameError("not_enough_participants", "至少需要用户和一名群成员")

    session_id = f"game_{uuid.uuid4().hex[:12]}"
    now = time.time()
    settings = {"total_rounds": int(total_rounds), "dice_min": 1, "dice_max": 150}
    public_state = {
        "round_rolls": {},
        "round_history": [],
        "last_event": {"type": "session_started", "text": "命运骰子开始了"},
    }
    try:
        db.execute(
            """INSERT INTO game_sessions
               (id, group_id, game_type, rules_version, status, round_no,
                current_turn_index, state_version, settings_json, public_state_json,
                created_at, updated_at)
               VALUES (?, ?, 'fate_dice', '1.0', 'running', 1, 0, 1, ?, ?, ?, ?)""",
            (session_id, group_id, json.dumps(settings), json.dumps(public_state, ensure_ascii=False), now, now),
        )
        for seat_no, participant in enumerate(participants):
            db.execute(
                """INSERT INTO game_participants
                   (id, session_id, participant_type, participant_ref_id, display_name, seat_no)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    f"gp_{uuid.uuid4().hex[:12]}", session_id,
                    participant["participant_type"], participant["participant_ref_id"],
                    participant["display_name"], seat_no,
                ),
            )
        db.execute(
            """INSERT INTO game_events
               (id, session_id, sequence_no, event_type, payload_json, state_version_after, created_at)
               VALUES (?, ?, 1, 'session_started', ?, 1, ?)""",
            (f"ge_{uuid.uuid4().hex[:12]}", session_id, json.dumps(settings), now),
        )
        db.commit()
    except sqlite3.IntegrityError as error:
        db.rollback()
        if "idx_one_running_game_per_group" in str(error) or "game_sessions.group_id" in str(error):
            raise GameError("active_session_exists", "该群已有进行中的游戏", 409) from error
        raise
    except Exception:
        db.rollback()
        raise
    return get_session(db, session_id)


def _persist_action(
    db,
    row,
    *,
    event_type: str,
    actor_ref_id: str | None,
    event_payload: dict[str, Any],
    public_state: dict[str, Any],
    status: str,
    round_no: int,
    turn_index: int,
    winner_ids: list[str],
    idempotency_key: str,
) -> None:
    now = time.time()
    new_version = int(row["state_version"]) + 1
    finished_at = now if status != "running" else None
    cursor = db.execute(
        """UPDATE game_sessions
           SET status = ?, round_no = ?, current_turn_index = ?, state_version = ?,
               public_state_json = ?, winner_json = ?, updated_at = ?, finished_at = ?
           WHERE id = ? AND state_version = ?""",
        (
            status, round_no, turn_index, new_version,
            json.dumps(public_state, ensure_ascii=False),
            json.dumps(winner_ids, ensure_ascii=False) if winner_ids else None,
            now, finished_at, row["id"], row["state_version"],
        ),
    )
    if cursor.rowcount != 1:
        raise GameError("version_conflict", "游戏状态已更新，请刷新后重试", 409)
    sequence = db.execute(
        "SELECT COALESCE(MAX(sequence_no), 0) + 1 FROM game_events WHERE session_id = ?",
        (row["id"],),
    ).fetchone()[0]
    db.execute(
        """INSERT INTO game_events
           (id, session_id, sequence_no, actor_ref_id, event_type, payload_json,
            state_version_after, idempotency_key, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            f"ge_{uuid.uuid4().hex[:12]}", row["id"], sequence, actor_ref_id,
            event_type, json.dumps(event_payload, ensure_ascii=False), new_version,
            idempotency_key, now,
        ),
    )


@_synchronized
def apply_action(
    db,
    session_id: str,
    *,
    action_type: str,
    actor_ref_id: str | None = None,
    expected_version: int | None = None,
    idempotency_key: str | None = None,
    randint_fn: Callable[[int, int], int] = _secure_randint,
) -> dict[str, Any]:
    action = (action_type or "").strip().lower()
    key = (idempotency_key or "").strip()
    if action not in {"roll", "end"}:
        raise GameError("invalid_action", "仅支持 roll 或 end")
    if not key:
        raise GameError("idempotency_key_required", "缺少幂等键")

    prior = db.execute(
        "SELECT id FROM game_events WHERE session_id = ? AND idempotency_key = ?",
        (session_id, key),
    ).fetchone()
    if prior:
        row = db.execute("SELECT * FROM game_sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            raise GameError("session_not_found", "游戏会话不存在", 404)
        return _session_response(db, row, replayed=True)

    row = db.execute("SELECT * FROM game_sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise GameError("session_not_found", "游戏会话不存在", 404)
    if row["status"] != "running":
        raise GameError("session_not_running", "游戏已经结束", 409)
    if expected_version is not None and int(expected_version) != int(row["state_version"]):
        raise GameError("version_conflict", "游戏状态已更新，请刷新后重试", 409)

    participants = _participants(db, session_id)
    state = _json_load(row["public_state_json"], {})
    rolls = dict(state.get("round_rolls") or {})
    history = list(state.get("round_history") or [])
    round_no = int(row["round_no"])
    turn_index = int(row["current_turn_index"])
    winner_ids: list[str] = []

    if action == "end":
        state["last_event"] = {"type": "session_ended", "text": "本局已手动结束"}
        try:
            _persist_action(
                db, row, event_type="session_ended", actor_ref_id=actor_ref_id or "user",
                event_payload=state["last_event"], public_state=state,
                status="cancelled", round_no=round_no, turn_index=turn_index,
                winner_ids=[], idempotency_key=key,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        return get_session(db, session_id)

    if not 0 <= turn_index < len(participants):
        raise GameError("invalid_turn", "当前回合状态异常", 409)
    current = participants[turn_index]
    actor = actor_ref_id or current["participant_ref_id"]
    if actor != current["participant_ref_id"]:
        raise GameError(
            "not_your_turn",
            f"现在轮到{current['display_name']}掷骰",
            409,
        )
    if actor in rolls:
        raise GameError("already_rolled", "本轮已经掷过骰子", 409)

    settings = _json_load(row["settings_json"], {})
    value = int(randint_fn(int(settings.get("dice_min", 1)), int(settings.get("dice_max", 150))))
    rolls[actor] = value
    event_payload: dict[str, Any] = {
        "type": "rolled",
        "actor_ref_id": actor,
        "display_name": current["display_name"],
        "value": value,
        "round_no": round_no,
        "text": f"{current['display_name']}掷出了 {value} 点",
    }
    status = "running"
    turn_index += 1

    if turn_index >= len(participants):
        high = max(rolls.values())
        round_winners = [pid for pid, rolled in rolls.items() if rolled == high]
        for winner_id in round_winners:
            db.execute(
                """UPDATE game_participants SET score = score + 1
                   WHERE session_id = ? AND participant_ref_id = ?""",
                (session_id, winner_id),
            )
        winner_names = [
            p["display_name"] for p in participants
            if p["participant_ref_id"] in round_winners
        ]
        history.append({
            "round_no": round_no,
            "rolls": rolls,
            "winner_ids": round_winners,
            "winner_names": winner_names,
            "high": high,
        })
        event_payload["round_result"] = history[-1]
        total_rounds = int(settings.get("total_rounds", 3))
        if round_no >= total_rounds:
            status = "finished"
            refreshed = _participants(db, session_id)
            top_score = max(p["score"] for p in refreshed)
            winner_ids = [
                p["participant_ref_id"] for p in refreshed if p["score"] == top_score
            ]
            final_names = [p["display_name"] for p in refreshed if p["score"] == top_score]
            event_payload["game_result"] = {
                "winner_ids": winner_ids,
                "winner_names": final_names,
                "score": top_score,
            }
            event_payload["text"] += f"；本局获胜：{'、'.join(final_names)}"
            turn_index = max(0, len(participants) - 1)
        else:
            round_no += 1
            turn_index = 0
            rolls = {}
            event_payload["text"] += f"；本轮获胜：{'、'.join(winner_names)}，进入第 {round_no} 轮"

    state["round_rolls"] = rolls
    state["round_history"] = history
    state["last_event"] = event_payload
    try:
        _persist_action(
            db, row, event_type="rolled", actor_ref_id=actor,
            event_payload=event_payload, public_state=state, status=status,
            round_no=round_no, turn_index=turn_index, winner_ids=winner_ids,
            idempotency_key=key,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_session(db, session_id)


def list_events(db, session_id: str) -> list[dict[str, Any]]:
    if not db.execute("SELECT id FROM game_sessions WHERE id = ?", (session_id,)).fetchone():
        raise GameError("session_not_found", "游戏会话不存在", 404)
    rows = db.execute(
        """SELECT sequence_no, actor_ref_id, event_type, payload_json,
                  state_version_after, created_at
           FROM game_events WHERE session_id = ? ORDER BY sequence_no ASC""",
        (session_id,),
    ).fetchall()
    return [{**dict(row), "payload": _json_load(row["payload_json"], {})} for row in rows]
