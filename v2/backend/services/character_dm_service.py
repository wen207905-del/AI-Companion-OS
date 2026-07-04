"""V4.1 角色私聊 — 触发评分、频率限制、LLM 生成、只读旁观。"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from api.ws_hub import hub
from app_state import state
from config import USER_NAME
from llm import router as llm_router
from services.character_relation_service import get_relation, relation_prompt_line, touch_dm
from services.emotion_tick import apply_scene_event_emotions, commit_emotion_delta, push_emotion_update

logger = logging.getLogger("companion.character_dm")

MAX_INITIATIONS_PER_DAY = 2
MAX_ACTIVE_CONVERSATIONS = 3

TRIGGER_META = {
    "jealousy_conflict": {"priority": 100, "cooldown_h": 4, "label": "嫉妒冲突"},
    "jealousy_probe": {"priority": 90, "cooldown_h": 3, "label": "试探吃醋"},
    "shared_scene": {"priority": 60, "cooldown_h": 6, "label": "同场后续"},
    "care_check": {"priority": 50, "cooldown_h": 8, "label": "关心打听"},
    "daily_chat": {"priority": 30, "cooldown_h": 12, "label": "日常闲聊"},
    "world_event": {"priority": 20, "cooldown_h": 24, "label": "世界事件"},
}

_recent_scenes: list[dict[str, Any]] = []
_recent_proactive: list[dict[str, Any]] = []


def record_scene_participants(participant_ids: list[str], *, source_character_id: str = "") -> None:
    if len(participant_ids) < 2:
        return
    _recent_scenes.append({
        "participants": list(participant_ids),
        "source": source_character_id,
        "ts": time.time(),
    })
    if len(_recent_scenes) > 20:
        del _recent_scenes[:-20]


def record_proactive_message(character_id: str) -> None:
    _recent_proactive.append({"character_id": character_id, "ts": time.time()})
    if len(_recent_proactive) > 30:
        del _recent_proactive[:-30]


def count_initiations_today(db, character_id: str) -> int:
    cutoff = time.time() - 86400.0
    row = db.execute(
        """
        SELECT COUNT(*) AS cnt FROM character_dm_conversation
        WHERE initiator_id = ? AND created_at >= ?
        """,
        (character_id, cutoff),
    ).fetchone()
    return int(row["cnt"] or 0) if row else 0


def count_active_conversations(db) -> int:
    row = db.execute(
        "SELECT COUNT(*) AS cnt FROM character_dm_conversation WHERE status = 'active'",
    ).fetchone()
    return int(row["cnt"] or 0) if row else 0


def hours_since_pair_dm(db, a: str, b: str) -> float:
    row = db.execute(
        """
        SELECT MAX(last_message_at) AS ts FROM character_dm_conversation
        WHERE status IN ('active', 'closed')
          AND ((character_a = ? AND character_b = ?) OR (character_a = ? AND character_b = ?))
        """,
        (a, b, b, a),
    ).fetchone()
    if not row or not row["ts"]:
        return 9999.0
    return max(0.0, (time.time() - float(row["ts"])) / 3600.0)


def can_initiate(db, initiator_id: str) -> bool:
    return count_initiations_today(db, initiator_id) < MAX_INITIATIONS_PER_DAY


def can_open_new_conversation(db) -> bool:
    return count_active_conversations(db) < MAX_ACTIVE_CONVERSATIONS


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


@dataclass
class DmCandidate:
    initiator_id: str
    target_id: str
    trigger_type: str
    score: float
    reason: str


def _cooldown_ok(db, initiator: str, target: str, trigger_type: str) -> bool:
    meta = TRIGGER_META.get(trigger_type, TRIGGER_META["daily_chat"])
    hours = hours_since_pair_dm(db, initiator, target)
    return hours >= float(meta["cooldown_h"])


def evaluate_candidates(db) -> list[DmCandidate]:
    if not state.persona_loader or not state.rel_engine or not state.emo_engine:
        return []

    candidates: list[DmCandidate] = []
    persona_ids = list(state.persona_loader.personas.keys())
    now = time.time()

    for initiator in persona_ids:
        rel_summary = state.rel_engine.get_summary(initiator)
        emo = state.emo_engine.get_summary(initiator)
        user_jealousy = float(rel_summary.get("jealousy") or 0)
        emo_jealous = float(emo.get("jealous") or 0)

        if user_jealousy >= 60 or emo_jealous >= 45:
            for target in persona_ids:
                if target == initiator:
                    continue
                pair_rel = get_relation(db, initiator, target)
                rivalry = float(pair_rel.get("rivalry") or 0)
                score = TRIGGER_META["jealousy_conflict"]["priority"] + user_jealousy * 0.3 + rivalry * 0.2
                candidates.append(DmCandidate(
                    initiator_id=initiator,
                    target_id=target,
                    trigger_type="jealousy_conflict",
                    score=score,
                    reason=f"对用户互动嫉妒({user_jealousy:.0f})，与{target}关系紧张",
                ))

        for item in _recent_proactive:
            if now - item["ts"] > 3600:
                continue
            other = item["character_id"]
            if other == initiator:
                continue
            if user_jealousy >= 40 or emo_jealous >= 30:
                candidates.append(DmCandidate(
                    initiator_id=initiator,
                    target_id=other,
                    trigger_type="jealousy_probe",
                    score=TRIGGER_META["jealousy_probe"]["priority"] + user_jealousy * 0.25,
                    reason=f"看到{other}主动找{USER_NAME}后试探",
                ))

        for scene in _recent_scenes:
            if now - scene["ts"] > 7200:
                continue
            parts = scene.get("participants") or []
            if initiator not in parts:
                continue
            for target in parts:
                if target == initiator:
                    continue
                candidates.append(DmCandidate(
                    initiator_id=initiator,
                    target_id=target,
                    trigger_type="shared_scene",
                    score=TRIGGER_META["shared_scene"]["priority"],
                    reason="刚在同一场景里碰面",
                ))

        if user_jealousy < 35 and emo_jealous < 25:
            for target in persona_ids:
                if target == initiator:
                    continue
                pair_rel = get_relation(db, initiator, target)
                if float(pair_rel.get("familiarity") or 0) >= 45:
                    candidates.append(DmCandidate(
                        initiator_id=initiator,
                        target_id=target,
                        trigger_type="daily_chat",
                        score=TRIGGER_META["daily_chat"]["priority"] + float(pair_rel.get("affinity") or 0) * 0.1,
                        reason="日常闲聊",
                    ))

    deduped: dict[tuple[str, str, str], DmCandidate] = {}
    for c in candidates:
        key = (c.initiator_id, c.target_id, c.trigger_type)
        if key not in deduped or c.score > deduped[key].score:
            deduped[key] = c
    ordered = sorted(deduped.values(), key=lambda x: x.score, reverse=True)
    return ordered


def select_candidate(db, candidates: list[DmCandidate]) -> DmCandidate | None:
    if not can_open_new_conversation(db):
        return None
    for c in candidates:
        if not can_initiate(db, c.initiator_id):
            continue
        if not _cooldown_ok(db, c.initiator_id, c.target_id, c.trigger_type):
            continue
        return c
    return None


def _build_dm_prompt(candidate: DmCandidate) -> list[dict[str, str]]:
    loader = state.persona_loader
    a = loader.get(candidate.initiator_id) or {}
    b = loader.get(candidate.target_id) or {}
    a_name = a.get("name", candidate.initiator_id)
    b_name = b.get("name", candidate.target_id)
    rel_ab = relation_prompt_line(state.db, candidate.initiator_id, candidate.target_id, loader)
    rel_ba = relation_prompt_line(state.db, candidate.target_id, candidate.initiator_id, loader)
    trigger_label = TRIGGER_META.get(candidate.trigger_type, {}).get("label", candidate.trigger_type)

    system = (
        f"你在写两个 AI 角色之间的私聊记录，用户{USER_NAME}只能旁观。\n"
        f"角色A：{a_name}（{candidate.initiator_id}）\n"
        f"角色B：{b_name}（{candidate.target_id}）\n"
        f"关系：{rel_ab}；{rel_ba}\n"
        f"触发：{trigger_label} — {candidate.reason}\n"
        "要求：\n"
        "- 输出 JSON 数组，4-6 条，交替发言\n"
        '- 每项 {"speaker_id":"角色id","content":"台词"}\n'
        "- 符合各自人设，围绕用户/最近事件，有张力但不过界\n"
        "- 不要出现用户发言，不要 markdown"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "生成角色私聊 JSON 数组。"},
    ]


def _parse_dm_messages(raw: str, initiator: str, target: str) -> list[dict[str, str]]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("expected list")
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        sid = item.get("speaker_id") or item.get("speaker")
        content = str(item.get("content") or "").strip()
        if sid not in (initiator, target) or not content:
            continue
        out.append({"speaker_id": sid, "content": content})
    if len(out) < 2:
        raise ValueError("too few messages")
    return out[:8]


def _fallback_messages(candidate: DmCandidate) -> list[dict[str, str]]:
    loader = state.persona_loader
    a_name = loader.get_display_name(candidate.initiator_id)
    b_name = loader.get_display_name(candidate.target_id)
    if candidate.trigger_type == "jealousy_conflict":
        return [
            {"speaker_id": candidate.initiator_id, "content": f"你刚才那句话是什么意思？你很了解{USER_NAME}？"},
            {"speaker_id": candidate.target_id, "content": "至少比你想象的了解。"},
            {"speaker_id": candidate.initiator_id, "content": "装什么成熟。"},
        ]
    return [
        {"speaker_id": candidate.initiator_id, "content": f"你看到{USER_NAME}今天来找你了？"},
        {"speaker_id": candidate.target_id, "content": f"嗯，{a_name}，有事？"},
        {"speaker_id": candidate.initiator_id, "content": "随便问问。"},
    ]


async def generate_messages(candidate: DmCandidate, llm_choice: dict | None = None) -> list[dict[str, str]]:
    try:
        raw = await llm_router.chat_completion(
            messages=_build_dm_prompt(candidate),
            choice=llm_choice,
            channel="aux",
            temperature=0.88,
            max_tokens=900,
        )
        return _parse_dm_messages(raw or "", candidate.initiator_id, candidate.target_id)
    except Exception as err:
        logger.warning("character DM LLM failed, fallback: %s", err)
        return _fallback_messages(candidate)


def save_conversation(
    candidate: DmCandidate,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    conv_id = f"cdm_{uuid.uuid4().hex[:12]}"
    now = time.time()
    ca, cb = _pair_key(candidate.initiator_id, candidate.target_id)

    state.db.execute(
        """
        INSERT INTO character_dm_conversation
        (id, character_a, character_b, initiator_id, trigger_type, trigger_reason,
         status, created_at, updated_at, last_message_at)
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
        """,
        (
            conv_id, ca, cb, candidate.initiator_id,
            candidate.trigger_type, candidate.reason,
            now, now, now,
        ),
    )

    ts = now
    for i, msg in enumerate(messages):
        msg_id = f"cdmm_{uuid.uuid4().hex[:10]}"
        ts = now + i * 0.01
        state.db.execute(
            """
            INSERT INTO character_dm_messages (id, conversation_id, speaker_id, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (msg_id, conv_id, msg["speaker_id"], msg["content"], ts),
        )
    state.db.execute(
        "UPDATE character_dm_conversation SET last_message_at = ? WHERE id = ?",
        (ts, conv_id),
    )
    state.db.commit()
    touch_dm(state.db, candidate.initiator_id, candidate.target_id)

    return {
        "id": conv_id,
        "character_a": ca,
        "character_b": cb,
        "initiator_id": candidate.initiator_id,
        "trigger_type": candidate.trigger_type,
        "trigger_reason": candidate.reason,
        "status": "active",
        "created_at": now,
        "last_message_at": ts,
        "message_count": len(messages),
    }


async def _apply_dm_emotions(candidate: DmCandidate) -> None:
    if not state.emo_engine:
        return
    deltas_map = {
        candidate.initiator_id: {"jealous": -3.0, "stressed": 2.0},
        candidate.target_id: {"calm": 1.0, "suspicious": 1.5},
    }
    if candidate.trigger_type == "jealousy_conflict":
        deltas_map[candidate.initiator_id]["angry"] = 2.0
        deltas_map[candidate.target_id]["calm"] = 2.0

    for cid, deltas in deltas_map.items():
        applied = commit_emotion_delta(cid, deltas, "character_dm")
        if applied:
            emo = state.emo_engine.get_summary(cid)
            await push_emotion_update(cid, applied, emo)


async def create_character_dm(
    candidate: DmCandidate,
    *,
    llm_choice: dict | None = None,
) -> dict[str, Any] | None:
    messages = await generate_messages(candidate, llm_choice)
    conv = save_conversation(candidate, messages)
    await _apply_dm_emotions(candidate)

    loader = state.persona_loader
    payload = {
        "type": "character_dm_created",
        "conversation": {
            **conv,
            "participants": [
                {
                    "id": candidate.initiator_id,
                    "name": loader.get_display_name(candidate.initiator_id),
                },
                {
                    "id": candidate.target_id,
                    "name": loader.get_display_name(candidate.target_id),
                },
            ],
            "preview": messages[0]["content"] if messages else "",
        },
    }
    await hub.send_rooms(["global"], payload)
    logger.info(
        "Character DM created: %s ↔ %s trigger=%s",
        candidate.initiator_id,
        candidate.target_id,
        candidate.trigger_type,
    )
    return conv


async def run_character_dm_tick(*, llm_choice: dict | None = None) -> str | None:
    if not state.db:
        return None
    candidates = evaluate_candidates(state.db)
    picked = select_candidate(state.db, candidates)
    if not picked:
        return None
    conv = await create_character_dm(picked, llm_choice=llm_choice)
    return conv["id"] if conv else None


def list_conversations(db, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = db.execute(
        """
        SELECT * FROM character_dm_conversation
        ORDER BY last_message_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    out = []
    loader = state.persona_loader
    for row in rows:
        ca, cb = row["character_a"], row["character_b"]
        preview_row = db.execute(
            """
            SELECT content FROM character_dm_messages
            WHERE conversation_id = ?
            ORDER BY timestamp DESC LIMIT 1
            """,
            (row["id"],),
        ).fetchone()
        out.append({
            "id": row["id"],
            "character_a": ca,
            "character_b": cb,
            "character_a_name": loader.get_display_name(ca) if loader else ca,
            "character_b_name": loader.get_display_name(cb) if loader else cb,
            "initiator_id": row["initiator_id"],
            "trigger_type": row["trigger_type"],
            "trigger_reason": row["trigger_reason"],
            "status": row["status"],
            "created_at": row["created_at"],
            "last_message_at": row["last_message_at"],
            "preview": preview_row["content"] if preview_row else "",
        })
    return out


def get_conversation_detail(db, conversation_id: str) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT * FROM character_dm_conversation WHERE id = ?",
        (conversation_id,),
    ).fetchone()
    if not row:
        return None
    msgs = db.execute(
        """
        SELECT id, speaker_id, content, timestamp
        FROM character_dm_messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
        """,
        (conversation_id,),
    ).fetchall()
    loader = state.persona_loader
    ca, cb = row["character_a"], row["character_b"]
    return {
        "conversation": {
            "id": row["id"],
            "character_a": ca,
            "character_b": cb,
            "character_a_name": loader.get_display_name(ca) if loader else ca,
            "character_b_name": loader.get_display_name(cb) if loader else cb,
            "initiator_id": row["initiator_id"],
            "trigger_type": row["trigger_type"],
            "trigger_reason": row["trigger_reason"],
            "status": row["status"],
            "created_at": row["created_at"],
            "last_message_at": row["last_message_at"],
        },
        "messages": [
            {
                "id": m["id"],
                "speaker_id": m["speaker_id"],
                "speaker_name": loader.get_display_name(m["speaker_id"]) if loader else m["speaker_id"],
                "content": m["content"],
                "timestamp": m["timestamp"],
            }
            for m in msgs
        ],
    }
