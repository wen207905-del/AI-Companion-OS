"""Tests for reference-style status mod."""

import yaml
from pathlib import Path

from config import load_all_personas
from mod.status_reference import (
    build_character_reference_block,
    build_meter_bars,
    build_speech_style_prompt,
    build_user_reference_block,
    reference_enabled,
    resolve_speech_style_key,
)

_REL_INIT = Path(__file__).resolve().parents[3] / "config" / "relationship_init.yaml"
FEMALE_IDS = {
    "ye_ruxue", "bai_rou", "liu_qingning", "mo_xiaoran", "gu_wanqing",
    "xiao_ying", "xingye_liuli", "su_nian", "lin_tangtang", "hua_li", "shen_man",
}


def _rel_init() -> dict:
    data = yaml.safe_load(_REL_INIT.read_text(encoding="utf-8")) or {}
    return data.get("characters") or {}


def test_reference_enabled():
    assert reference_enabled() is True


def test_meter_bars():
    rel = {"trust": 80, "intimacy_physical": 55, "attachment": 70, "security": 60, "jealousy": 20}
    emo = {"primary_mood": "平静"}
    text = build_meter_bars(rel, emo)
    assert "信任80" in text
    assert "警戒" in text


def test_ye_ruxue_reference_block():
    persona = load_all_personas()["ye_ruxue"]
    rel = {
        "trust": 85, "intimacy_physical": 50, "attachment": 88, "security": 70,
        "jealousy": 30, "current_activity": "整理资料",
        "social_relation_label": "继母·恋子", "affection_grade": "深恋",
    }
    emo = {"primary_mood": "温柔"}
    block = build_character_reference_block("ye_ruxue", persona, rel, emo, user_message="妈妈我在茶亭")
    assert "夜如雪" in block
    assert "穿搭" in block
    assert "性器官" in block or "嘴" in block
    assert "信任" in block


def test_all_female_organ_detail():
    personas = load_all_personas()
    rel_init = _rel_init()
    for cid in FEMALE_IDS:
        persona = personas[cid]
        meta = rel_init[cid]
        rel = {
            "trust": 70, "intimacy_physical": 50, "attachment": 60, "security": 65,
            "jealousy": 10, "current_activity": meta.get("current_activity", "日常"),
        }
        emo = {"primary_mood": "平静"}
        block = build_character_reference_block(cid, persona, rel, emo)
        assert persona["name"] in block
        assert "性器官" in block or "嘴" in block, f"missing organ block for {cid}"


def test_speech_style_stepmother():
    persona = load_all_personas()["ye_ruxue"]
    block = build_speech_style_prompt("stepmother", persona, character_id="ye_ruxue")
    assert "『" in block
    assert "妈妈" in block


def test_speech_style_brother():
    persona = load_all_personas()["wang_dahai"]
    block = build_speech_style_prompt("brother", persona, character_id="wang_dahai")
    assert "兄弟" in block
    assert "禁止" in block


def test_speech_style_aunt_not_stepmother():
    persona = load_all_personas()["shen_man"]
    block = build_speech_style_prompt("aunt_like", persona, character_id="shen_man")
    assert "妈妈" not in block or "禁止" in block
    assert "明星" in block or "汉文" in block


def test_character_overrides():
    assert resolve_speech_style_key("maid", {"id": "gu_wanqing"}, "gu_wanqing") == "childhood_friend"
    assert resolve_speech_style_key("childhood_friend", {"id": "mo_xiaoran"}, "mo_xiaoran") == "yandere"


def test_all_characters_have_speech_style():
    personas = load_all_personas()
    rel_init = _rel_init()
    for cid, meta in rel_init.items():
        block = build_speech_style_prompt(
            meta["social_relation_type"],
            personas[cid],
            character_id=cid,
        )
        assert "对白格式" in block, f"missing speech for {cid}"


def test_user_reference_block():
    block = build_user_reference_block("我回家了")
    assert "许汉文" in block
    assert "云栖里" in block or "住所" in block
