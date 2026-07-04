"""V4.1 proactive share — activity-driven scoring and content generation."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable
from zoneinfo import ZoneInfo

from api.ws_hub import hub
from app_state import state
from config import USER_NAME
from engine.world_clock import TIMEZONE, now as world_now
from llm import router as llm_router
from services.anti_repeat_service import contains_forbidden, is_too_similar
from services.daily_life_service import (
    get_activity_share_desire,
    get_current_activity,
    get_preferred_intents,
    load_proactive_config,
    maybe_refresh_activity,
)
from services.social_relation_service import enrich_relationship_summary, get_relation_meta
from engine import absence as absence_helpers

logger = logging.getLogger("companion.proactive_share")

EmitFn = Callable[[dict], Awaitable[None]]


@dataclass
class ProactiveCandidate:
    character_id: str
    score: float
    intent: str
    activity: str
    breakdown: dict[str, float]


def compute_proactive_score(
    *,
    activity_share_desire: float,
    emotion_intensity: float,
    affection_weight: float,
    persona_initiative: float,
    memory_trigger: float,
    world_bonus: float,
    cooldown_penalty: float = 0.0,
    repeat_penalty: float = 0.0,
) -> float:
    base = (
        activity_share_desire * 0.25
        + emotion_intensity * 0.20
        + affection_weight * 0.20
        + persona_initiative * 0.15
        + memory_trigger * 0.10
        + world_bonus * 0.10
    )
    return round(base - cooldown_penalty - repeat_penalty, 2)


def affection_weight_from_grade(grade: str, config: dict[str, Any] | None = None) -> float:
    cfg = config or load_proactive_config()
    weights = cfg.get("grade_weights") or {}
    return float(weights.get(grade or "陌生", 5))


def persona_initiative_for(character_id: str, config: dict[str, Any] | None = None) -> float:
    cfg = config or load_proactive_config()
    mapping = cfg.get("character_initiative") or {}
    return float(mapping.get(character_id, mapping.get("default", 50)))


def emotion_intensity(
    *,
    hours_since_user: float,
    lonely: float,
    jealousy: float,
) -> float:
    miss_user = min(100.0, hours_since_user * 4.0)
    return min(100.0, miss_user * 0.35 + lonely * 0.35 + jealousy * 0.30)


def memory_trigger_score(
    *,
    has_recent_memory: bool,
    has_unanswered_user: bool,
) -> float:
    raw = (15.0 if has_recent_memory else 0.0) + (25.0 if has_unanswered_user else 0.0)
    return min(100.0, raw * 2.5)


def world_bonus_score(ts: float | None = None) -> float:
    hour = datetime.now(tz=ZoneInfo(TIMEZONE)).hour
    bonus = 50.0
    if hour >= 22 or hour < 6:
        bonus += 10.0
    return min(100.0, bonus)


def cooldown_penalty(hours_since_proactive: float) -> float:
    if hours_since_proactive < 2.0:
        return 30.0
    if hours_since_proactive < 6.0:
        return 15.0
    return 0.0


def choose_intent(
    character_id: str,
    activity: str,
    *,
    last_intent: str | None = None,
    last_intent_age_hours: float = 9999.0,
    config: dict[str, Any] | None = None,
) -> str:
    preferred = get_preferred_intents(activity, config)
    if last_intent and last_intent in preferred and last_intent_age_hours < 48.0:
        alt = [i for i in preferred if i != last_intent]
        if alt:
            idx = sum(ord(c) for c in character_id) % len(alt)
            return alt[idx]
    idx = sum(ord(c) for c in character_id) % len(preferred)
    return preferred[idx]


def score_character(
    character_id: str,
    *,
    config: dict[str, Any] | None = None,
) -> ProactiveCandidate | None:
    if not state.db or not state.rel_engine or not state.emo_engine:
        return None

    cfg = config or load_proactive_config()
    threshold = float(cfg.get("score_threshold", 55))
    min_hours = float(cfg.get("min_hours_since_user", 2.0))

    hours_user = absence_helpers.hours_since_last_user_message(state.db, character_id)
    if hours_user < min_hours:
        return None

    activity = maybe_refresh_activity(state.db, character_id)
    rel = enrich_relationship_summary(
        state.db,
        character_id,
        state.rel_engine.get_summary(character_id),
    )
    meta = get_relation_meta(state.db, character_id)
    grade = meta.get("affection_grade") or rel.get("affection_grade", "陌生")
    affection_w = affection_weight_from_grade(grade, cfg)
    if affection_w < 10:
        return None

    emo = state.emo_engine.get_summary(character_id)
    lonely = float(emo.get("lonely") or 0)
    jealousy = float(rel.get("jealousy") or 0)

    hours_proactive = absence_helpers.hours_since_last_proactive(state.db, character_id)
    last_intent, last_intent_age = absence_helpers.last_proactive_intent(state.db, character_id)
    recent_texts = absence_helpers.recent_proactive_texts(state.db, hours=24.0)

    repeat_pen = 20.0 if hours_proactive < 24.0 else 0.0

    breakdown = {
        "activity_share_desire": get_activity_share_desire(activity, cfg),
        "emotion_intensity": emotion_intensity(
            hours_since_user=hours_user,
            lonely=lonely,
            jealousy=jealousy,
        ),
        "affection_weight": affection_w,
        "persona_initiative": persona_initiative_for(character_id, cfg),
        "memory_trigger": memory_trigger_score(
            has_recent_memory=absence_helpers.has_recent_user_memory(
                state.db, character_id, hours=2.0,
            ),
            has_unanswered_user=absence_helpers.has_unanswered_user_message(
                state.db, character_id,
            ),
        ),
        "world_bonus": world_bonus_score(),
        "cooldown_penalty": cooldown_penalty(hours_proactive),
        "repeat_penalty": repeat_pen,
    }

    score = compute_proactive_score(
        activity_share_desire=breakdown["activity_share_desire"],
        emotion_intensity=breakdown["emotion_intensity"],
        affection_weight=breakdown["affection_weight"],
        persona_initiative=breakdown["persona_initiative"],
        memory_trigger=breakdown["memory_trigger"],
        world_bonus=breakdown["world_bonus"],
        cooldown_penalty=breakdown["cooldown_penalty"],
        repeat_penalty=breakdown["repeat_penalty"],
    )

    if score < threshold:
        return None

    intent = choose_intent(
        character_id,
        activity,
        last_intent=last_intent,
        last_intent_age_hours=last_intent_age,
        config=cfg,
    )
    return ProactiveCandidate(
        character_id=character_id,
        score=score,
        intent=intent,
        activity=activity,
        breakdown=breakdown,
    )


def select_candidates(
    candidates: list[ProactiveCandidate],
    *,
    hourly_sent: int,
    hourly_limit: int = 3,
    max_pick: int = 1,
) -> list[ProactiveCandidate]:
    if hourly_sent >= hourly_limit:
        return []
    remaining = hourly_limit - hourly_sent
    pick = min(max_pick, remaining)
    ordered = sorted(candidates, key=lambda c: c.score, reverse=True)
    return ordered[:pick]


def build_proactive_prompt(
    character_id: str,
    candidate: ProactiveCandidate,
    *,
    persona: dict,
    rel: dict,
    emo: dict,
    hours_since_user: float,
    config: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    cfg = config or load_proactive_config()
    intents = cfg.get("intents") or {}
    intent_cfg = intents.get(candidate.intent) or {}
    styles = cfg.get("character_styles") or {}
    style = styles.get(character_id) or styles.get("default", "")
    forbidden = cfg.get("forbidden_phrases") or []

    name = persona.get("name", character_id)
    rel_type = rel.get("social_relation_label") or rel.get("stage_name", "")
    grade = rel.get("affection_grade") or rel.get("stage_name", "")
    mood = emo.get("primary_mood", "平静")

    system = (
        f"你是{name}，正在给{USER_NAME}发一条私聊主动消息。\n"
        f"当前活动：{candidate.activity}。分享类型：{intent_cfg.get('label', candidate.intent)}。\n"
        f"社会关系：{rel_type}。好感：{grade}。心情：{mood}。\n"
        f"已约{hours_since_user:.0f}小时没聊。\n"
        f"写作要求：{intent_cfg.get('prompt', '分享当前具体活动，1-2句口语。')}\n"
        f"人设风格：{style}\n"
        f"禁止用语：{'、'.join(forbidden[:6])}。\n"
        "不要加角色名前缀，不要像AI，不要批量问候套话。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"（根据你正在「{candidate.activity}」，发一条{intent_cfg.get('label', '分享')}）"},
    ]


async def generate_proactive_content(
    character_id: str,
    candidate: ProactiveCandidate,
    *,
    persona: dict,
    rel: dict,
    emo: dict,
    hours_since_user: float,
) -> str | None:
    cfg = load_proactive_config()
    forbidden = list(cfg.get("forbidden_phrases") or [])
    recent_texts = absence_helpers.recent_proactive_texts(state.db, hours=24.0)
    threshold = float(cfg.get("similarity_threshold", 0.7))

    messages = build_proactive_prompt(
        character_id,
        candidate,
        persona=persona,
        rel=rel,
        emo=emo,
        hours_since_user=hours_since_user,
        config=cfg,
    )

    for attempt in range(2):
        try:
            reply = await llm_router.chat_completion(
                messages=messages,
                channel="aux",
                max_tokens=140,
                temperature=0.9 if attempt == 0 else 0.75,
            )
        except Exception:
            logger.exception("Proactive LLM failed for %s", character_id)
            return None

        content = (reply or "").strip()
        if not content or len(content) < 4:
            continue
        if contains_forbidden(content, forbidden):
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": "含有模板问候，请重写：结合当前活动具体细节，禁止「想你了」类套话。",
            })
            continue
        if is_too_similar(content, recent_texts, threshold=threshold):
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": "与近期消息太像，请换一种说法和句式。",
            })
            continue
        return content
    return None


async def send_proactive_message(
    candidate: ProactiveCandidate,
    content: str,
    *,
    emit: EmitFn | None = None,
) -> bool:
    if not state.db:
        return False

    persona = state.persona_loader.get(candidate.character_id) if state.persona_loader else {}
    name = (persona or {}).get("name", candidate.character_id)
    msg_id = f"pro_{uuid.uuid4().hex[:12]}"
    ts = world_now()
    meta = {
        "intent": candidate.intent,
        "score": candidate.score,
        "activity": candidate.activity,
        "proactive": True,
    }

    state.db.execute(
        """INSERT INTO private_messages
           (id, character_id, sender_type, content, action, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            msg_id,
            candidate.character_id,
            "character",
            content,
            json.dumps(meta, ensure_ascii=False),
            ts,
        ),
    )
    state.db.commit()

    if state.memory_manager:
        state.memory_manager.store(
            candidate.character_id,
            content,
            role="character",
            scope="private",
            event_id=msg_id,
            intensity=65.0,
            memory_type="proactive",
        )

    payload = {
        "type": "message",
        "id": msg_id,
        "content": content,
        "sender_type": "character",
        "sender_id": candidate.character_id,
        "character_name": name,
        "timestamp": ts,
        "proactive": True,
        "intent": candidate.intent,
        "activity": candidate.activity,
        "score": candidate.score,
    }

    room = f"private:{candidate.character_id}"
    if emit:
        await emit(payload)
    else:
        await hub.send_room(room, payload)

    logger.info(
        "Proactive share sent: %s intent=%s score=%.1f activity=%s",
        candidate.character_id,
        candidate.intent,
        candidate.score,
        candidate.activity,
    )

    if state.emo_engine:
        from services.emotion_tick import commit_emotion_delta, push_emotion_update
        emo_delta = commit_emotion_delta(
            candidate.character_id,
            {"happy": 1.5, "miss_user": -2.0},
            "proactive_share",
            activity=candidate.activity,
        )
        if emo_delta:
            emo = state.emo_engine.get_summary(candidate.character_id)
            await push_emotion_update(
                candidate.character_id,
                emo_delta,
                emo,
                room=f"private:{candidate.character_id}",
            )
    return True


async def run_proactive_tick(*, emit: EmitFn | None = None) -> list[str]:
    """Score all characters, send up to remaining hourly quota."""
    if not state.persona_loader or not state.db:
        return []

    cfg = load_proactive_config()
    hourly_limit = int(cfg.get("hourly_limit", 3))
    hourly_sent = absence_helpers.count_proactive_in_last_hour(state.db)

    if hourly_sent >= hourly_limit:
        return []

    candidates: list[ProactiveCandidate] = []
    for character_id in state.persona_loader.personas:
        scored = score_character(character_id, config=cfg)
        if scored:
            candidates.append(scored)

    selected = select_candidates(
        candidates,
        hourly_sent=hourly_sent,
        hourly_limit=hourly_limit,
        max_pick=1,
    )

    sent_ids: list[str] = []
    for candidate in selected:
        persona = state.persona_loader.get(candidate.character_id) or {}
        rel = enrich_relationship_summary(
            state.db,
            candidate.character_id,
            state.rel_engine.get_summary(candidate.character_id),
        )
        emo = state.emo_engine.get_summary(candidate.character_id)
        hours = absence_helpers.hours_since_last_user_message(state.db, candidate.character_id)

        content = await generate_proactive_content(
            candidate.character_id,
            candidate,
            persona=persona,
            rel=rel,
            emo=emo,
            hours_since_user=hours,
        )
        if not content:
            continue
        ok = await send_proactive_message(candidate, content, emit=emit)
        if ok:
            sent_ids.append(candidate.character_id)
    return sent_ids
