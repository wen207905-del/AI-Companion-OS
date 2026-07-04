"""V4.1 scene mode — multi-character narrative with JSON fallback."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app_state import state
from config import CONFIG_DIR, USER_NAME
from engine.world_clock import world_rules_block
from llm import router as llm_router
from services.speaker_resolver import build_participant_labels, detect_participants
from services.social_relation_service import enrich_relationship_summary, get_relation_meta

logger = logging.getLogger("companion.scene_mode")

_SCENE_TEMPLATE_PATH = CONFIG_DIR / "prompts" / "scene_mode.txt"


def _load_template() -> str:
    if _SCENE_TEMPLATE_PATH.exists():
        return _SCENE_TEMPLATE_PATH.read_text(encoding="utf-8")
    return ""


def _character_state_block(character_id: str) -> str:
    if not state.rel_engine or not state.emo_engine:
        return f"{character_id}: 状态未知"
    rel = enrich_relationship_summary(
        state.db,
        character_id,
        state.rel_engine.get_summary(character_id),
    )
    emo = state.emo_engine.get_summary(character_id)
    meta = get_relation_meta(state.db, character_id) if state.db else {}
    name = state.persona_loader.get_display_name(character_id)
    activity = meta.get("current_activity", "日常")
    social = meta.get("social_relation_label", "")
    grade = rel.get("affection_grade", "")
    mood = emo.get("primary_mood", "平静")
    return (
        f"- {character_id}（{name}）社会关系={social} "
        f"好感={rel.get('affection_score', rel.get('love', 0))}·{grade} "
        f"心情={mood} 活动={activity}"
    )


def _relation_network(participant_ids: list[str]) -> str:
    lines = []
    for pid in participant_ids:
        persona = state.persona_loader.get(pid)
        if not persona:
            continue
        rels = persona.get("relationships", {})
        if isinstance(rels, dict):
            bits = [f"{k}:{v}" for k, v in list(rels.items())[:4]]
            if bits:
                lines.append(f"{pid}: " + "；".join(bits))
    return "\n".join(lines) if lines else "（按 persona 默认关系）"


def build_scene_messages(scene_text: str, participant_ids: list[str] | None = None) -> list[dict[str, str]]:
    participants = participant_ids or detect_participants(scene_text, state.persona_loader)
    template = _load_template()
    system = template.format(
        scene_text=scene_text.strip(),
        participants=build_participant_labels(participants, state.persona_loader),
        character_relations=_relation_network(participants),
        character_states="\n".join(_character_state_block(pid) for pid in participants)
        or "（未识别在场角色，请根据场景合理推断）",
    )
    rules = world_rules_block()
    if rules:
        system += "\n\n" + rules
    user = f"{USER_NAME}描述的场景：\n{scene_text.strip()}\n\n请输出 JSON。"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _extract_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _validate_scene_payload(data: dict[str, Any]) -> dict[str, Any]:
    narration = str(data.get("narration") or "").strip()
    participants = data.get("participants")
    events = data.get("events")
    if not isinstance(participants, list):
        participants = []
    if not isinstance(events, list):
        events = []
    clean_events = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        cid = ev.get("character_id")
        if not cid:
            continue
        emo_delta = ev.get("emotion_delta")
        if not isinstance(emo_delta, dict):
            emo_delta = {}
        clean_events.append({
            "character_id": cid,
            "action": str(ev.get("action") or "").strip(),
            "dialogue": str(ev.get("dialogue") or "").strip(),
            "emotion_delta": emo_delta,
        })
    return {
        "mode": "scene",
        "narration": narration,
        "participants": participants,
        "events": clean_events,
    }


def parse_scene_response(raw: str, *, retry_once: bool = False) -> dict[str, Any]:
    try:
        data = _extract_json(raw)
        return _validate_scene_payload(data)
    except (json.JSONDecodeError, TypeError, ValueError) as first_err:
        logger.warning("scene JSON parse failed: %s", first_err)
        if retry_once:
            raise
        return {
            "mode": "scene",
            "narration": (raw or "").strip(),
            "participants": [],
            "events": [],
            "parse_fallback": True,
        }


async def generate_scene_response(
    scene_text: str,
    llm_choice: dict | None = None,
    participant_ids: list[str] | None = None,
) -> dict[str, Any]:
    messages = build_scene_messages(scene_text, participant_ids)
    raw = await llm_router.chat_completion(
        messages=messages,
        choice=llm_choice,
        temperature=0.85,
        max_tokens=2048,
    )
    parsed = parse_scene_response(raw or "")
    if parsed.get("parse_fallback"):
        try:
            raw2 = await llm_router.chat_completion(
                messages=messages + [{
                    "role": "user",
                    "content": "上一回复不是合法 JSON。请只输出符合 schema 的 JSON，不要 markdown。",
                }],
                choice=llm_choice,
                temperature=0.4,
                max_tokens=2048,
            )
            parsed = parse_scene_response(raw2 or "", retry_once=True)
        except Exception as retry_err:
            logger.warning("scene JSON retry failed: %s", retry_err)
            parsed = {
                "mode": "scene",
                "narration": (raw or "").strip(),
                "participants": participant_ids or [],
                "events": [],
                "parse_fallback": True,
            }
    if not parsed.get("participants"):
        parsed["participants"] = participant_ids or detect_participants(scene_text, state.persona_loader)
    return parsed
