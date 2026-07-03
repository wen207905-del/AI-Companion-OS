"""Assemble V4/V5 comprehensive status blocks for LLM prompts."""

from __future__ import annotations

from typing import Any

from chat.stat_snapshot import EMO_NUMERIC_KEYS, REL_NUMERIC_KEYS
from config import USER_NAME
from engine.world_clock import LOCATION, snapshot
from mod.config_loader import load_manifest, mod_variant
from mod.outfit_state import infer_outfit, organ_status_text, _is_female
from mod.reproductive import cycle_state, pregnancy_probability
from mod.user_status import build_user_status_block
from personality.body_experience import build_body_experiences


def build_status_block(
    character_id: str,
    persona: dict,
    rel_summary: dict[str, Any],
    emo_summary: dict[str, Any],
    *,
    user_message: str = "",
    arousal_summary: dict | None = None,
    growth_summary: dict | None = None,
    scope: str = "private",
    group_name: str = "",
) -> str:
    variant = mod_variant()
    if variant not in ("v4", "v5"):
        return ""

    cfg = load_manifest()
    if variant == "v4":
        return _build_v4(
            character_id, persona, rel_summary, emo_summary,
            user_message=user_message,
            arousal_summary=arousal_summary,
            growth_summary=growth_summary,
            scope=scope,
            group_name=group_name,
            cfg=cfg,
        )
    return _build_v5(
        character_id, persona, rel_summary, emo_summary,
        user_message=user_message,
        arousal_summary=arousal_summary,
        growth_summary=growth_summary,
        scope=scope,
        group_name=group_name,
        cfg=cfg,
    )


def _top_emotions(emo_summary: dict, n: int = 4) -> str:
    scored = []
    for key in EMO_NUMERIC_KEYS:
        val = float(emo_summary.get(key, 0))
        if val >= 8 and key != "calm":
            scored.append((val, key))
    scored.sort(reverse=True)
    if not scored:
        mood = emo_summary.get("primary_mood", "平静")
        return str(mood)
    labels = {
        "happy": "开心", "stressed": "压力", "tired": "疲惫", "lonely": "孤独",
        "excited": "兴奋", "embarrassed": "尴尬", "shy": "害羞", "suspicious": "怀疑",
        "sad": "难过", "angry": "生气", "fearful": "害怕",
    }
    return " ".join(f"{labels.get(k, k)}{v:.0f}" for v, k in scored[:n])


def _rel_line(rel: dict) -> str:
    parts = []
    cn = {
        "love": "好感", "trust": "信任", "attachment": "依恋", "respect": "尊重",
        "security": "安全感", "possessiveness": "占有欲", "jealousy": "嫉妒",
        "intimacy_emotional": "情感亲密", "intimacy_physical": "身体亲密",
    }
    for key in REL_NUMERIC_KEYS:
        parts.append(f"{cn.get(key, key)}{float(rel.get(key, 0)):.0f}")
    return " ".join(parts)


def _scene_bar(scope: str, group_name: str, user_message: str) -> str:
    snap = snapshot()
    place = LOCATION
    if scope == "group" and group_name:
        place = f"{LOCATION} · 群聊「{group_name}」"
    mood = "私聊" if scope == "private" else "群聊"
    hint = ""
    if user_message:
        um = user_message.strip()[:40]
        hint = f" | 用户刚说：{um}"
    return (
        f"【场景状态栏】{snap['datetime']}（{snap['weekday']}）| 地点：{place} | "
        f"场合：{mood}{hint}"
    )


def _female_extra(
    character_id: str,
    persona: dict,
    rel_summary: dict,
    arousal_summary: dict | None,
    user_message: str,
    cfg: dict,
) -> list[str]:
    if not _is_female(persona):
        return []
    fem = cfg.get("female") or {}
    lines: list[str] = []

    if fem.get("outfit_catalog", True):
        outfit = infer_outfit(persona, user_message)
        oline = f"服饰：{outfit['label']} — {outfit['desc'][:80]}"
        if outfit.get("stockings"):
            oline += f"；丝袜：{outfit['stockings']}"
        if outfit.get("underwear"):
            oline += f"；内衣：{outfit['underwear']}"
        lines.append(oline)

    if fem.get("organ_detail", True):
        organ = organ_status_text(persona, rel_summary)
        if organ:
            lines.append(f"性器官/身体：{organ}")

    if fem.get("reproductive_state", True):
        cycle = cycle_state(character_id)
        preg = pregnancy_probability(
            character_id,
            rel_summary=rel_summary,
            arousal_summary=arousal_summary,
            user_message=user_message,
        )
        lines.append(
            f"生理周期：第{cycle['day_in_cycle']}/{cycle['cycle_length']}天 · {cycle['phase']} · "
            f"卵巢：{cycle['ovary'][:50]}"
        )
        lines.append(
            f"受孕参考：{preg['label']}（约{preg['probability']}%）· {cycle['symptom_hint'][:40]}"
        )
    return lines


def _character_memo(persona: dict, cfg: dict) -> str:
    memo_cfg = cfg.get("character_memo") or {}
    if not memo_cfg.get("enabled", True):
        return ""
    max_items = int(memo_cfg.get("max_items") or 6)
    items: list[str] = []
    history = persona.get("shared_history") or {}
    for m in (history.get("memorable_moments") or [])[:2]:
        items.append(str(m)[:60])
    for m in (history.get("milestones") or [])[:2]:
        items.append(str(m)[:60])
    intimate = persona.get("intimate_state") or {}
    for f in (intimate.get("fetishes") or [])[:2]:
        items.append(f"偏好：{f}")
    if not items:
        return ""
    return "角色杂项：" + "；".join(items[:max_items])


def _word_limit_suffix(cfg: dict) -> str:
    if not cfg.get("word_limit_hint"):
        return ""
    limit = int(cfg.get("word_limit_chars") or 800)
    return f"\n【字数参考】本轮回复建议 {limit} 字以内，口语化优先，勿为凑字数重复状态栏。"


def _build_v4(
    character_id: str,
    persona: dict,
    rel_summary: dict,
    emo_summary: dict,
    *,
    user_message: str,
    arousal_summary: dict | None,
    growth_summary: dict | None,
    scope: str,
    group_name: str,
    cfg: dict,
) -> str:
    name = persona.get("name", character_id)
    parts: list[str] = []

    if cfg.get("include_scene_bar", True):
        parts.append(_scene_bar(scope, group_name, user_message))

    parts.append(f"【角色状态栏——{name}】")
    parts.append(
        f"关系：{rel_summary.get('stage_name', '')}（阶段{rel_summary.get('stage', 1)}）| {_rel_line(rel_summary)}"
    )
    parts.append(f"情绪：{emo_summary.get('primary_mood', '平静')} | {_top_emotions(emo_summary)}")

    if arousal_summary:
        parts.append(
            f"发情：{arousal_summary.get('level', 0):.0f}/100（{arousal_summary.get('label', '')}）"
            f" · 易感度{arousal_summary.get('susceptibility', 0):.0f}"
        )

    if growth_summary:
        parts.append(
            f"成长：Lv{growth_summary.get('level', 1)} XP{growth_summary.get('xp', 0)}"
        )

    parts.extend(_female_extra(character_id, persona, rel_summary, arousal_summary, user_message, cfg))

    memo = _character_memo(persona, cfg)
    if memo:
        parts.append(memo)

    user_block = build_user_status_block(character_id, user_message=user_message)
    if user_block:
        parts.append(user_block)

    parts.append("（以上状态栏供你内化表现，勿逐条朗读或像报表一样复述。）")
    return "\n".join(parts) + _word_limit_suffix(cfg)


def _build_v5(
    character_id: str,
    persona: dict,
    rel_summary: dict,
    emo_summary: dict,
    *,
    user_message: str,
    arousal_summary: dict | None,
    growth_summary: dict | None,
    scope: str,
    group_name: str,
    cfg: dict,
) -> str:
    name = persona.get("name", character_id)
    lines = [f"【身心状态——{name}·按此写反应，勿逐条背诵】"]

    love = float(rel_summary.get("love", 0))
    stage = rel_summary.get("stage_name", "")
    mood = emo_summary.get("primary_mood", "平静")
    emo_extra = _top_emotions(emo_summary, 3)

    summary = (
        f"与{USER_NAME}：{stage}，好感{love:.0f}，此刻{mood}"
    )
    if emo_extra and emo_extra != mood:
        summary += f"，情绪里还有{emo_extra}"
    if arousal_summary:
        ar = float(arousal_summary.get("level", 0))
        if ar >= 25:
            summary += f"；身体发情度{ar:.0f}，呼吸与反应需同步"
    lines.append(summary)

    if _is_female(persona):
        outfit = infer_outfit(persona, user_message)
        lines.append(f"穿着：{outfit['label']}，{outfit['desc'][:70]}")

        experiences = build_body_experiences(persona, rel_summary)
        if experiences:
            exp_text = "；".join(
                f"{e['part']}（{e['experience'][:45]}）" for e in experiences[:4]
            )
            lines.append(f"身体记忆：{exp_text}")

        if (cfg.get("female") or {}).get("reproductive_state", True):
            cycle = cycle_state(character_id)
            preg = pregnancy_probability(
                character_id,
                rel_summary=rel_summary,
                arousal_summary=arousal_summary,
                user_message=user_message,
            )
            lines.append(
                f"生理：{cycle['phase']}第{cycle['day_in_cycle']}天，{cycle['symptom_hint'][:35]}；"
                f"受孕参考{preg['label']}"
            )

        organ = organ_status_text(persona, rel_summary)
        if organ and (cfg.get("female") or {}).get("organ_detail", True):
            lines.append(f"私密状态：{organ[:160]}")

    memo = _character_memo(persona, cfg)
    if memo:
        lines.append(memo)

    user_block = build_user_status_block(character_id, user_message=user_message)
    if user_block:
        lines.append(user_block.replace("【用户状态栏", "【对方"))

    if scope == "group" and group_name:
        lines.append(f"（当前在群聊「{group_name}」，尺度比私聊克制。）")

    return "\n".join(lines) + _word_limit_suffix(cfg)
