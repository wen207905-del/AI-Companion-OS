"""User status bar block for status mod."""

from __future__ import annotations

from config import USER_NAME, USER_NICKNAME, load_user_profile
from mod.config_loader import load_manifest
from mod.status_reference import build_user_reference_block, reference_enabled


def build_user_status_block(
    character_id: str,
    *,
    user_message: str = "",
) -> str:
    cfg = load_manifest()
    user_cfg = cfg.get("user_status") or {}
    if not user_cfg.get("enabled", True):
        return ""

    profile = load_user_profile()
    if not profile:
        return ""

    lines = [f"【用户状态栏——{USER_NAME}（{USER_NICKNAME}）】"]

    base = profile.get("base_info") or {}
    if age := base.get("age"):
        lines.append(f"年龄 {age} · {base.get('occupation', '')[:40]}")

    appearance = profile.get("appearance") or {}
    if overall := appearance.get("overall"):
        lines.append(f"外貌：{str(overall)[:100]}")

    personality = profile.get("personality") or {}
    if core := personality.get("core"):
        lines.append(f"性格：{str(core)[:100]}")

    if user_cfg.get("include_body_intimate"):
        body = profile.get("body_intimate") or {}
        if summary := body.get("summary"):
            lines.append(f"私密：{str(summary)[:120]}")

    network = (profile.get("relationships") or {}).get("romance_network") or []
    for entry in network:
        if entry.get("id") == character_id:
            lines.append(f"与你关系：{entry.get('label', '')} — {entry.get('status', '')}")
            break

    if user_cfg.get("include_daily_routine"):
        routine = profile.get("daily_routine") or []
        if routine:
            lines.append("作息：" + "；".join(str(r) for r in routine[:3]))

    if user_cfg.get("include_assets_brief"):
        assets = profile.get("assets") or {}
        brief_parts = []
        if income := assets.get("monthly_income"):
            brief_parts.append(f"收入{income}")
        if savings := assets.get("savings"):
            brief_parts.append(f"存款{savings}")
        if prop := assets.get("property"):
            brief_parts.append(f"房产{str(prop)[:40]}")
        if brief_parts:
            lines.append("资产：" + " · ".join(brief_parts))

    if user_cfg.get("include_memo"):
        memos = _user_memo_items(profile, user_message)
        if memos:
            lines.append("杂项记忆：" + "；".join(memos[:5]))

    hidden = personality.get("hidden")
    if hidden and character_id in ("ye_ruxue", "bai_rou", "gu_wanqing"):
        lines.append(f"（未言明）{str(hidden)[:90]}")

    if reference_enabled():
        ref = build_user_reference_block(user_message)
        if ref:
            return ref

    return "\n".join(lines)


def _user_memo_items(profile: dict, user_message: str) -> list[str]:
    """Surface relevant user.yaml snippets as memo."""
    items: list[str] = []
    residence = profile.get("residence_detail") or {}
    if name := residence.get("name"):
        items.append(f"现居{name}")

    hobbies = profile.get("hobbies") or []
    if hobbies:
        items.append("爱好：" + "、".join(str(h) for h in hobbies[:3]))

    speech = profile.get("speech_style") or {}
    catch = speech.get("catchphrases") or []
    if catch:
        items.append("口头禅：" + catch[0])

    if user_message and len(user_message) < 80:
        items.append(f"本轮说：{user_message.strip()}")

    return items
