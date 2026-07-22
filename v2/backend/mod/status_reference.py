"""Reference-document style status blocks (骚妈升级APP / CG 状态栏)."""

from __future__ import annotations

from typing import Any

from config import USER_NAME
from mod.config_loader import load_manifest, load_organ_detail, load_speech_styles
from mod.outfit_state import infer_outfit, _is_female


def _ref_cfg() -> dict:
    return (load_manifest().get("reference_style") or {})


def reference_enabled() -> bool:
    return bool(_ref_cfg().get("enabled", False))


def build_meter_bars(rel_summary: dict[str, Any], emo_summary: dict[str, Any]) -> str:
    if not _ref_cfg().get("meter_bars", True):
        return ""
    trust = min(100, max(0, float(rel_summary.get("trust", 0))))
    intimacy = min(100, max(0, float(rel_summary.get("intimacy_physical", 0))))
    attach = min(100, max(0, float(rel_summary.get("attachment", 0))))
    alert = min(100, max(0, 100 - float(rel_summary.get("security", 50)) + float(rel_summary.get("jealousy", 0)) * 0.3))
    return (
        "【关系指标】"
        f"信任{trust:.0f}% | 亲密{intimacy:.0f}% | 依赖{attach:.0f}% | 警戒{alert:.0f}%"
    )


def _infer_pose(user_message: str, activity: str) -> str:
    text = f"{user_message} {activity}"
    if any(k in text for k in ("躺", "床", "睡")):
        return "躺/倚靠姿态"
    if any(k in text for k in ("坐", "沙发", "茶亭")):
        return "端坐或交叠双腿"
    if any(k in text for k in ("站", "门", "走", "进")):
        return "站立或走动中"
    if any(k in text for k in ("厨房", "做饭", "炖")):
        return "在厨房台前忙碌"
    return f"进行「{activity or '日常'}」相关动作"


def build_outfit_breakdown(persona: dict, user_message: str = "", scene_hint: str = "") -> str:
    if not _ref_cfg().get("outfit_breakdown", True):
        return ""
    outfit = infer_outfit(persona, user_message, scene_hint=scene_hint)
    appearance = persona.get("appearance") or {}
    acc = appearance.get("accessories") or appearance.get("accessory") or ""
    style = appearance.get("style") or ""
    lines = [
        f"上装/整体：{outfit['label']} — {outfit['desc'][:90]}",
    ]
    if style:
        lines.append(f"人设风格：{str(style)[:80]}")
    lines.append(f"内衣：{outfit.get('underwear', '无日常内衣（世界常态）')}")
    if outfit.get("stockings"):
        lines.append(f"袜：{outfit['stockings']}")
    else:
        lines.append("鞋袜：居家多赤足或棉拖，外出按场景")
    if acc:
        lines.append(f"饰品：{str(acc)[:60]}")
    return "穿搭｜" + "；".join(lines)


def build_organ_by_part(character_id: str, persona: dict, rel_summary: dict | None = None) -> str:
    if not _ref_cfg().get("organ_by_part", True) or not _is_female(persona):
        return ""
    parts: dict[str, str] = {}

    body = persona.get("body_intimate") or {}
    if isinstance(body.get("parts"), dict):
        parts.update({str(k): str(v) for k, v in body["parts"].items()})

    templates = load_organ_detail().get(character_id) or {}
    if isinstance(templates.get("parts"), dict):
        for k, v in templates["parts"].items():
            parts.setdefault(str(k), str(v))

    intimate = persona.get("intimate_state") or {}
    for part, exp in (intimate.get("body_experiences") or {}).items():
        if part not in parts and exp:
            parts[str(part)] = f"与{USER_NAME}相关记忆：{str(exp)[:70]}"

    if not parts:
        return ""

    order = ("嘴", "胸部", "小穴", "腹部", "子宫", "臀部", "菊穴", "腿足")
    lines = []
    for key in order:
        if key in parts:
            lines.append(f"{key}：{parts[key][:120]}")
    for key, val in parts.items():
        if key not in order:
            lines.append(f"{key}：{val[:120]}")
    return "性器官与敏感度｜" + " ".join(lines[:8])


def build_psychology_block(persona: dict, emo_summary: dict[str, Any]) -> str:
    if not _ref_cfg().get("psychology_block", True):
        return ""
    intimate = persona.get("intimate_state") or {}
    fetishes = intimate.get("fetishes") or []
    covert = persona.get("personality", {}).get("covert") or {}
    overt = persona.get("personality", {}).get("overt") or {}
    mood = emo_summary.get("primary_mood", "平静")

    bits = []
    if summary := covert.get("summary") or overt.get("summary"):
        bits.append(f"深层：{str(summary)[:100]}")
    if fetishes:
        bits.append("性癖/倾向：" + "；".join(str(f) for f in fetishes[:4]))
    bits.append(
        f"内心戏提示：此刻{mood}，回复时可嵌入（……）式内心，写对用户行为的解读与恋子/占有念头，勿贴「内心OS」标签"
    )
    return "心理｜" + " ".join(bits)


def build_character_reference_block(
    character_id: str,
    persona: dict,
    rel_summary: dict[str, Any],
    emo_summary: dict[str, Any],
    *,
    user_message: str = "",
    scene_hint: str = "",
) -> str:
    if not reference_enabled():
        return ""

    base = persona.get("base_info") or {}
    appearance = persona.get("appearance") or {}
    name = persona.get("name", character_id)
    activity = rel_summary.get("current_activity", "日常")
    sections: list[str] = [f"══ 【互动角色状态栏：{name}】 ══"]

    face = appearance.get("face") or appearance.get("overall") or ""
    body = appearance.get("body") or ""
    meas = base.get("measurements") or {}
    meas_str = ""
    if meas:
        meas_str = f"{meas.get('bust_cm', '?')}{meas.get('cup', '')}-{meas.get('waist_cm', '?')}-{meas.get('hip_cm', '?')}"

    sections.append(
        f"基础｜{base.get('occupation', '')} · {base.get('height_cm', '?')}cm"
        f" · 三维约{meas_str} · 面容：{str(face)[:80]}"
    )
    if body:
        sections.append(f"身材：{str(body)[:100]}")

    if _ref_cfg().get("pose_hint", True):
        sections.append(f"当前姿势（推断）：{_infer_pose(user_message or scene_hint, activity)}")

    outfit = build_outfit_breakdown(persona, user_message, scene_hint)
    if outfit:
        sections.append(outfit)

    organ = build_organ_by_part(character_id, persona, rel_summary)
    if organ:
        sections.append(organ)

    psych = build_psychology_block(persona, emo_summary)
    if psych:
        sections.append(psych)

    meters = build_meter_bars(rel_summary, emo_summary)
    if meters:
        sections.append(meters)

    sections.append("（以上供内化表现，勿逐条朗读或像报表复述。）")
    return "\n".join(sections)


def build_user_reference_block(user_message: str = "") -> str:
    if not reference_enabled():
        return ""

    from config import load_user_profile

    profile = load_user_profile()
    if not profile:
        return ""

    base = profile.get("base_info") or {}
    appearance = profile.get("appearance") or {}
    personality = profile.get("personality") or {}
    body = profile.get("body_intimate") or {}
    residence = profile.get("residence_detail") or {}

    lines = [f"══ 【玩家角色状态栏：{USER_NAME}】 ══"]
    lines.append(
        f"基础｜{base.get('age', '?')}岁 · {base.get('occupation', '')[:50]} · "
        f"性格：{str(personality.get('core', ''))[:80]}"
    )
    if style := appearance.get("style"):
        lines.append(f"穿着：{str(style)[:100]}")
    if overall := appearance.get("overall"):
        lines.append(f"外貌：{str(overall)[:80]}")

    if _ref_cfg().get("pose_hint", True) and user_message:
        lines.append(f"本轮姿态（推断）：面对场景「{user_message.strip()[:50]}」")

    if summary := body.get("summary"):
        lines.append(f"性能力：{str(summary)[:100]}")
    penis = body.get("penis") or {}
    if erect := penis.get("erect_length_cm"):
        lines.append(f"尺寸参考：勃起约{erect}cm")

    if name := residence.get("name"):
        lines.append(f"住所：{name} — {str(residence.get('description') or residence.get('layout', ''))[:80]}")

    assets = profile.get("assets") or {}
    if prop := assets.get("property"):
        lines.append(f"资产：{str(prop)[:60]}")

    hidden = personality.get("hidden")
    if hidden:
        lines.append(f"（未言明心理）{str(hidden)[:90]}")

    lines.append("（用户状态供角色反应参考，勿替用户写内心。）")
    return "\n".join(lines)


_RELATION_STYLE_MAP = {
    "brotherhood": "brotherhood",
    "brother": "brotherhood",
    "stepmother": "stepmother",
    "mentor": "stepmother",
    "aunt_like": "aunt_like",
    "wife_like": "wife_like",
    "girlfriend": "girlfriend",
    "rival": "rival",
    "childhood_friend": "childhood_friend",
    "maid": "maid",
    "sister_like": "sister_like",
}


def resolve_speech_style_key(
    social_relation_type: str,
    persona: dict | None = None,
    character_id: str = "",
) -> str:
    styles = load_speech_styles()
    overrides = styles.get("by_character") or {}
    cid = character_id or (persona or {}).get("id") or ""
    if cid and cid in overrides:
        return str(overrides[cid])
    rel_type = social_relation_type or "romance_default"
    return _RELATION_STYLE_MAP.get(rel_type, "romance_default")


def build_speech_style_prompt(
    social_relation_type: str,
    persona: dict,
    *,
    character_id: str = "",
) -> str:
    if not _ref_cfg().get("speech_styles", True):
        return ""

    styles = load_speech_styles()
    key = resolve_speech_style_key(social_relation_type, persona, character_id)

    cfg = styles.get(key) or styles.get("default") or {}
    default = styles.get("default") or {}
    lines = ["【对白与叙述风格——严格遵守】"]

    if voice := cfg.get("voice"):
        lines.append(f"声线：{voice}")
    elif speech := persona.get("speech_style"):
        if default_tone := speech.get("default") or speech.get("private"):
            lines.append(f"声线：{default_tone}")

    fmt = cfg.get("dialogue_format") or default.get("dialogue_format", "「{text}」")
    lines.append(f"对白格式：{fmt.replace('{text}', '……')}（不要用「角色名：」前缀）")

    if narr := cfg.get("narration_style") or default.get("narration_style"):
        lines.append(f"旁白：{narr}")

    for habit in (cfg.get("habits") or [])[:5]:
        lines.append(f"- {habit}")
    for avoid in (cfg.get("avoid") or [])[:3]:
        lines.append(f"- 禁止：{avoid}")

    if inner := cfg.get("inner_thought"):
        lines.append(f"内心：{inner}")

    catch = persona.get("speech_style", {}).get("catchphrases") or []
    if catch:
        lines.append("口癖参考：" + "、".join(str(c) for c in catch[:4]))

    return "\n".join(lines)
