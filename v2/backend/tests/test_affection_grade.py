"""Tests for V4.1 affection grade service."""

from services.affection_grade_service import (
    build_affection_display,
    compute_affection_score,
    score_to_grade,
)


def test_compute_affection_score():
    score = compute_affection_score(
        love=80,
        trust=90,
        attachment=88,
        security=85,
        respect=80,
        emotional_intimacy=88,
    )
    assert 75 <= score <= 90


def test_score_to_grade_romance():
    assert score_to_grade(86, "romance") == "深恋"
    assert score_to_grade(52, "romance") == "在意"
    assert score_to_grade(72, "romance") == "倾心"


def test_score_to_grade_friendship():
    assert score_to_grade(82, "brotherhood") == "铁哥们"
    assert score_to_grade(45, "brotherhood") == "朋友"


def test_build_affection_display_friendship():
    display = build_affection_display(
        love=82,
        trust=90,
        attachment=80,
        security=85,
        respect=85,
        emotional_intimacy=44,
        relationship_type="brotherhood",
        preset_score=82,
        preset_grade="铁哥们",
    )
    assert display.affection_grade == "铁哥们"
    assert "友情度" in display.score_label
