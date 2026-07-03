"""Outfit inference from keywords + persona defaults."""

from __future__ import annotations

import re

from mod.config_loader import load_outfits_config


def _is_female(persona: dict) -> bool:
    if persona.get("gender") == "male":
        return False
    if persona.get("relationship_type") == "brotherhood":
        return False
    return True


def infer_outfit(persona: dict, user_message: str = "", scene_hint: str = "") -> dict:
    """Return {label, desc, stockings, underwear_hint}."""
    cfg = load_outfits_config()
    categories = cfg.get("categories") or {}
    stockings_list = cfg.get("stockings") or []
    text = f"{user_message} {scene_hint}".lower()

    matched = categories.get("default") or {}
    for key, entry in categories.items():
        if key == "default":
            continue
        keywords = entry.get("keywords") or []
        if any(k.lower() in text for k in keywords):
            matched = entry
            break

    if matched.get("label") == "日常" or not matched.get("keywords"):
        appearance = persona.get("appearance") or {}
        style = str(appearance.get("style") or "")
        if "睡" in text or "bedroom" in text or "卧室" in text:
            matched = categories.get("lingerie_sleep") or matched
        elif style:
            matched = {"label": "人设日常", "desc": style[:120]}

    stockings = ""
    for s in stockings_list:
        if any(k in text for k in (s[:2], s)):
            stockings = s
            break
    if not stockings and any(k in text for k in ("丝袜", "袜", "stocking")):
        stockings = stockings_list[0] if stockings_list else "肉色丝袜"

    intimate = persona.get("intimate_state") or {}
    lewd = float(intimate.get("lewdness") or 30)
    if lewd >= 60:
        underwear = "情趣蕾丝内衣（可能未穿齐）"
    elif lewd >= 35:
        underwear = "舒适蕾丝内衣"
    else:
        underwear = "日常内衣"

    return {
        "label": matched.get("label", "日常"),
        "desc": matched.get("desc", ""),
        "stockings": stockings,
        "underwear": underwear,
    }


def organ_status_text(persona: dict, rel_summary: dict | None = None) -> str:
    """Brief organ / intimate body state for female characters."""
    if not _is_female(persona):
        return ""

    rel = rel_summary or {}
    love = float(rel.get("love", 0))
    intimate = persona.get("intimate_state") or {}
    body = persona.get("body_intimate") or {}
    sensitivity = intimate.get("sensitivity") or {}

    chest_sens = float(sensitivity.get("chest") or sensitivity.get("breast") or 5)
    if love >= 80:
        chest = f"胸部：饱满敏感（{chest_sens:.0f}/10），与你亲密后易挺立、留吻痕"
        lower = "私处：已熟悉你的形状与节奏，湿润反应快，内壁会不自觉绞紧"
    elif love >= 50:
        chest = f"胸部：形状柔软（敏感度 {chest_sens:.0f}/10），触碰时会轻颤"
        lower = "私处：有过亲密，仍会因你的靠近而湿润"
    else:
        chest = f"胸部：尚未完全交付（敏感度 {chest_sens:.0f}/10）"
        lower = "私处：仅允许暧昧边缘，内里仍有些紧张"

    if summary := body.get("summary"):
        extra = str(summary)[:80]
    else:
        extra = ""

    parts = [chest, lower]
    if extra:
        parts.append(f"备注：{extra}")
    return "；".join(parts)
