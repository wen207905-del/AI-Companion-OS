"""Female reproductive / menstrual cycle simulation for status mod."""

from __future__ import annotations

import hashlib
from datetime import datetime

from engine.world_clock import _tz

CYCLE_DEFAULT = 28
MENSES_DAYS = 5
OVULATION_WINDOW = (13, 16)


def _cycle_offset(character_id: str) -> int:
    h = int(hashlib.md5(character_id.encode()).hexdigest()[:6], 16)
    return h % CYCLE_DEFAULT


def cycle_state(character_id: str, ts: float | None = None) -> dict:
    """Deterministic cycle from character id + world date."""
    from engine.world_clock import now

    dt = datetime.fromtimestamp(ts if ts is not None else now(), tz=_tz())
    day_of_year = dt.timetuple().tm_yday
    offset = _cycle_offset(character_id)
    day_in_cycle = ((day_of_year + offset) % CYCLE_DEFAULT) + 1

    if day_in_cycle <= MENSES_DAYS:
        phase = "月经期"
        phase_en = "menstrual"
        ovary = "卵泡尚未成熟，子宫内膜脱落中"
        fertility = "极低"
        fertility_score = 0.05
        mood_hint = "可能腰酸、情绪敏感，腹部偶有坠胀"
    elif day_in_cycle < OVULATION_WINDOW[0]:
        phase = "卵泡期"
        phase_en = "follicular"
        ovary = "卵泡发育中，雌激素上升，内膜增厚"
        fertility = "低"
        fertility_score = 0.15
        mood_hint = "精力回升，皮肤状态较好"
    elif day_in_cycle <= OVULATION_WINDOW[1]:
        phase = "排卵期"
        phase_en = "ovulation"
        ovary = "成熟卵泡待排或刚排，宫颈黏液清亮，受孕窗口"
        fertility = "高"
        fertility_score = 0.72
        mood_hint = "性欲与敏感度可能升高，身体更渴望亲密"
    else:
        phase = "黄体期"
        phase_en = "luteal"
        ovary = "黄体分泌孕酮，若未受孕则准备退行"
        fertility = "低"
        fertility_score = 0.12
        mood_hint = "可能乳房胀感、轻微水肿或 PMS 前兆"

    return {
        "day_in_cycle": day_in_cycle,
        "cycle_length": CYCLE_DEFAULT,
        "phase": phase,
        "phase_en": phase_en,
        "ovary": ovary,
        "fertility_label": fertility,
        "fertility_base": fertility_score,
        "symptom_hint": mood_hint,
        "next_menses_in_days": CYCLE_DEFAULT - day_in_cycle + 1 if day_in_cycle > MENSES_DAYS else 0,
    }


def pregnancy_probability(
    character_id: str,
    *,
    rel_summary: dict | None = None,
    arousal_summary: dict | None = None,
    user_message: str = "",
) -> dict:
    """Estimate pregnancy chance this turn (narrative aid, not simulation engine)."""
    cycle = cycle_state(character_id)
    rel = rel_summary or {}
    arousal = arousal_summary or {}

    base = float(cycle["fertility_base"])
    intimacy = float(rel.get("intimacy_physical", 0)) / 100.0
    love = float(rel.get("love", 0)) / 100.0
    arousal_lv = float(arousal.get("level", 0)) / 100.0

    internal_keywords = ("内射", "射里", "里面", "不戴套", "危险期", "备孕", "受精")
    msg = user_message or ""
    internal = any(k in msg for k in internal_keywords)

    score = base * 0.55 + intimacy * 0.2 + arousal_lv * 0.15 + love * 0.05
    if internal and cycle["phase_en"] == "ovulation":
        score = min(0.92, score + 0.35)
    elif internal:
        score = min(0.55, score + 0.12)
    elif cycle["phase_en"] == "menstrual":
        score = min(score, 0.08)

    if score >= 0.65:
        label = "较高（排卵期+亲密行为）"
    elif score >= 0.35:
        label = "中等"
    elif score >= 0.15:
        label = "偏低"
    else:
        label = "极低"

    return {
        "probability": round(score * 100, 1),
        "label": label,
        "note": "仅作角色扮演参考，非医学计算",
        "cycle_phase": cycle["phase"],
    }
