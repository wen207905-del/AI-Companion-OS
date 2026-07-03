"""Tests for comprehensive status mod."""

from config import load_all_personas
from mod.config_loader import mod_variant
from mod.reproductive import cycle_state, pregnancy_probability
from mod.status_block import build_status_block


def test_mod_v5_block_contains_female_fields(memory_db):
    personas = load_all_personas()
    persona = personas["bai_rou"]
    rel = {"love": 80, "trust": 90, "stage": 6, "stage_name": "恋人", "intimacy_physical": 70}
    emo = {"primary_mood": "害羞", "shy": 55, "happy": 40}
    block = build_status_block(
        "bai_rou", persona, rel, emo, user_message="今天穿女仆装", arousal_summary={"level": 30, "label": "微热"},
    )
    assert "【身心状态" in block
    assert "女仆" in block or "穿着" in block
    assert "生理" in block or "卵泡" in block or "月经" in block


def test_mod_skipped_for_male():
    personas = load_all_personas()
    persona = personas["wang_dahai"]
    rel = {"love": 70, "stage_name": "兄弟", "stage": 3}
    emo = {"primary_mood": "平静"}
    block = build_status_block("wang_dahai", persona, rel, emo)
    assert "卵巢" not in block
    assert "性器官" not in block


def test_cycle_state_deterministic():
    a = cycle_state("bai_rou")
    b = cycle_state("bai_rou")
    assert a["day_in_cycle"] == b["day_in_cycle"]
    assert a["phase"] in ("月经期", "卵泡期", "排卵期", "黄体期")


def test_pregnancy_higher_on_ovulation():
    low = pregnancy_probability(
        "bai_rou",
        rel_summary={"intimacy_physical": 80, "love": 80},
        arousal_summary={"level": 60},
        user_message="",
    )
    assert "probability" in low


def test_mod_variant_enabled():
    assert mod_variant() in ("v4", "v5", "off")
