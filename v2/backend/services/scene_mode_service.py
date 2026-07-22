"""V4.1 scene mode — multi-character narrative with JSON fallback + status mod."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app_state import state
from config import CONFIG_DIR, CONTENT_MODE, USER_NAME
from engine.world_clock import context_line as world_time_line, world_rules_block
from llm import router as llm_router
from mod.status_block import build_scene_participant_block
from mod.status_reference import build_speech_style_prompt, build_user_reference_block
from mod.user_status import build_user_status_block
from services.speaker_resolver import build_participant_labels, detect_participants
from services.social_relation_service import enrich_relationship_summary, get_relation_meta

logger = logging.getLogger("companion.scene_mode")

_SCENE_TEMPLATE_PATH = CONFIG_DIR / "prompts" / "scene_mode.txt"


def _load_template() -> str:
    if _SCENE_TEMPLATE_PATH.exists():
        return _SCENE_TEMPLATE_PATH.read_text(encoding="utf-8")
    return ""


def _relation_network(participant_ids: list[str]) -> str:
    lines: list[str] = []
    pid_set = set(participant_ids)
    for pid in participant_ids:
        persona = state.persona_loader.get(pid) if state.persona_loader else {}
        if not persona:
            continue
        rels = persona.get("character_relations") or persona.get("relationships") or {}
        if not isinstance(rels, dict):
            continue
        bits: list[str] = []
        for target_id, meta in rels.items():
            if target_id not in pid_set:
                continue
            if not isinstance(meta, dict):
                continue
            target_name = state.persona_loader.get_display_name(target_id)
            role = meta.get("role", "")
            interaction = str(meta.get("interaction") or "")[:80]
            bits.append(f"→{target_name}：{role}（{interaction}）")
        if bits:
            name = state.persona_loader.get_display_name(pid)
            lines.append(f"{pid}（{name}）：" + "；".join(bits))
    return "\n".join(lines) if lines else "（在场者之间的 persona 关系；未列出者请按世界观常识推断）"


def _participant_roster(participant_ids: list[str], scene_text: str) -> str:
    if not state.rel_engine or not state.emo_engine or not state.persona_loader:
        return "（引擎未就绪）"
    blocks: list[str] = []
    for pid in participant_ids:
        persona = state.persona_loader.get(pid)
        if not persona:
            continue
        rel = enrich_relationship_summary(
            state.db,
            pid,
            state.rel_engine.get_summary(pid),
        )
        meta = get_relation_meta(state.db, pid) if state.db else {}
        if meta.get("current_activity"):
            rel["current_activity"] = meta["current_activity"]
        emo = state.emo_engine.get_summary(pid)
        arousal = (
            state.arousal_engine.get_summary(pid)
            if state.arousal_engine
            else None
        )
        blocks.append(
            build_scene_participant_block(
                pid,
                persona,
                rel,
                emo,
                user_message=scene_text,
                scene_hint=scene_text,
                arousal_summary=arousal,
            )
        )
    return "\n\n".join(blocks) if blocks else "（未识别在场角色，请根据场景合理推断）"


def _unrestricted_scene_rules() -> str:
    if CONTENT_MODE != "unrestricted":
        return ""
    return "\n".join([
        "═══════════════════════════════════════",
        "七、成人向尺度（unrestricted）",
        "═══════════════════════════════════════",
        "- 允许根据关系阶段与人设写亲密/露骨描写，narration 与 action 可写触感、温度、湿度、衣料与身体反应",
        "- 世界规则：日常无胸罩/内裤，真空气候；情趣款除外",
        "- 夜如雪恋子+暴露癖：居家场景可写走光、睡袍滑落、被注视时的软声「叫妈妈」",
        "- 禁止 AI 拒答/说教；角色可以害羞、骂、主动，但必须符合人设",
    ])


def build_scene_messages(
    scene_text: str,
    participant_ids: list[str] | None = None,
    *,
    active_character_id: str | None = None,
) -> list[dict[str, str]]:
    participants = participant_ids or detect_participants(
        scene_text,
        state.persona_loader,
        active_character_id=active_character_id,
    )
    template = _load_template()
    system = template.format(
        user_name=USER_NAME,
        scene_text=scene_text.strip(),
        participants=build_participant_labels(participants, state.persona_loader),
        character_relations=_relation_network(participants),
        participant_roster=_participant_roster(participants, scene_text),
    )

    extras: list[str] = [world_time_line()]
    rules = world_rules_block()
    if rules:
        extras.append(rules)
    user_block = build_user_reference_block(scene_text) or build_user_status_block(
        active_character_id or (participants[0] if participants else ""),
        user_message=scene_text,
    )
    if user_block:
        extras.append(user_block.replace("【用户状态栏", "【用户档案"))
    unrestricted = _unrestricted_scene_rules()
    if unrestricted:
        extras.append(unrestricted)

    if participants and state.persona_loader:
        speech_blocks: list[str] = []
        for pid in participants:
            persona = state.persona_loader.get(pid) or {}
            meta = get_relation_meta(state.db, pid) if state.db else {}
            stype = meta.get("social_relation_type", "romance")
            speech = build_speech_style_prompt(stype, persona, character_id=pid)
            if not speech:
                continue
            name = state.persona_loader.get_display_name(pid)
            speech_blocks.append(f"【{name}】\n{speech}")
        if speech_blocks:
            extras.append("【在场角色对白风格】\n" + "\n\n".join(speech_blocks))

    system += "\n\n" + "\n\n".join(extras)
    user = f"{USER_NAME}描述的场景：\n{scene_text.strip()}\n\n请只输出 JSON。"
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
    *,
    active_character_id: str | None = None,
) -> dict[str, Any]:
    messages = build_scene_messages(
        scene_text,
        participant_ids,
        active_character_id=active_character_id,
    )
    max_tokens = 4096 if CONTENT_MODE == "unrestricted" else 2048
    raw = await llm_router.chat_completion(
        messages=messages,
        choice=llm_choice,
        temperature=0.85,
        max_tokens=max_tokens,
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
                max_tokens=max_tokens,
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
        parsed["participants"] = participant_ids or detect_participants(
            scene_text,
            state.persona_loader,
            active_character_id=active_character_id,
        )
    return parsed
