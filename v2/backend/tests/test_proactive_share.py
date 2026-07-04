"""Tests for V4.1 proactive share scoring and hourly limits."""

import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import init_db
from services.proactive_share_service import (
    ProactiveCandidate,
    affection_weight_from_grade,
    compute_proactive_score,
    persona_initiative_for,
    select_candidates,
)
from engine import absence as absence_helpers


def _memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def test_compute_proactive_score_threshold():
    high = compute_proactive_score(
        activity_share_desire=78,
        emotion_intensity=70,
        affection_weight=85,
        persona_initiative=72,
        memory_trigger=50,
        world_bonus=60,
    )
    low = compute_proactive_score(
        activity_share_desire=40,
        emotion_intensity=20,
        affection_weight=15,
        persona_initiative=30,
        memory_trigger=0,
        world_bonus=50,
        cooldown_penalty=30,
    )
    assert high >= 55
    assert low < 55


def test_affection_grade_weights_differ():
    assert affection_weight_from_grade("深恋") > affection_weight_from_grade("在意")
    assert affection_weight_from_grade("铁哥们") > affection_weight_from_grade("陌生")


def test_persona_initiative_character_styles():
    assert persona_initiative_for("wang_dahai") > persona_initiative_for("ye_ruxue")
    assert persona_initiative_for("unknown_id") == persona_initiative_for("unknown_id", {"character_initiative": {"default": 50}})


def test_select_candidates_hourly_limit():
    candidates = [
        ProactiveCandidate("a", 80, "daily_share", "温汤", {}),
        ProactiveCandidate("b", 75, "mood_share", "做题", {}),
        ProactiveCandidate("c", 70, "daily_share", "吃烧烤", {}),
        ProactiveCandidate("d", 65, "care_check", "备餐", {}),
    ]
    picked = select_candidates(candidates, hourly_sent=0, hourly_limit=3, max_pick=3)
    assert len(picked) == 3
    assert picked[0].score >= picked[1].score >= picked[2].score

    none_left = select_candidates(candidates, hourly_sent=3, hourly_limit=3, max_pick=1)
    assert none_left == []

    one_slot = select_candidates(candidates, hourly_sent=2, hourly_limit=3, max_pick=2)
    assert len(one_slot) == 1


def test_count_proactive_in_last_hour():
    db = _memory_db()
    now = time.time()
    for i, cid in enumerate(["bai_rou", "liu_qingning", "wang_dahai"]):
        db.execute(
            """INSERT INTO private_messages
               (id, character_id, sender_type, content, timestamp)
               VALUES (?, ?, 'character', ?, ?)""",
            (f"pro_test{i}", cid, f"msg{i}", now - i * 10),
        )
    db.execute(
        """INSERT INTO private_messages
           (id, character_id, sender_type, content, timestamp)
           VALUES ('pro_old', 'ye_ruxue', 'character', 'old', ?)""",
        (now - 7200,),
    )
    db.commit()
    assert absence_helpers.count_proactive_in_last_hour(db) == 3


def test_has_unanswered_user_message():
    db = _memory_db()
    db.execute(
        """INSERT INTO private_messages
           (id, character_id, sender_type, content, timestamp)
           VALUES ('u1', 'bai_rou', 'user', '在吗', ?)""",
        (time.time(),),
    )
    db.commit()
    assert absence_helpers.has_unanswered_user_message(db, "bai_rou")


def test_build_proactive_prompt_styles_differ():
    from services.proactive_share_service import build_proactive_prompt

    base_kwargs = dict(
        candidate=ProactiveCandidate("x", 70, "daily_share", "温汤", {}),
        persona={"name": "测试"},
        rel={"affection_grade": "深恋", "social_relation_label": "伴侣"},
        emo={"primary_mood": "平静"},
        hours_since_user=6.0,
    )
    bai = build_proactive_prompt("bai_rou", **base_kwargs)[0]["content"]
    liu = build_proactive_prompt("liu_qingning", **{**base_kwargs, "candidate": ProactiveCandidate("liu_qingning", 70, "mood_share", "做题", {})})[0]["content"]
    wang = build_proactive_prompt("wang_dahai", **{**base_kwargs, "candidate": ProactiveCandidate("wang_dahai", 70, "daily_share", "吃烧烤", {})})[0]["content"]
    assert "温柔" in bai or "妻子" in bai
    assert "傲娇" in liu or "嘴硬" in liu
    assert "损友" in wang or "兄弟" in wang
    assert bai != liu != wang
