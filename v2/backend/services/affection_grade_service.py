"""好感度等级计算 — 情感热度，与社会关系标签分离。"""

from __future__ import annotations

from dataclasses import dataclass

ROMANCE_GRADES: list[tuple[float, str]] = [
    (100, "灵魂牵系"),
    (95, "羁绊"),
    (85, "深恋"),
    (75, "爱慕"),
    (65, "倾心"),
    (50, "在意"),
    (35, "亲近"),
    (20, "熟识"),
    (10, "点头之交"),
    (0, "陌生"),
]

FRIENDSHIP_GRADES: list[tuple[float, str]] = [
    (95, "过命兄弟"),
    (80, "铁哥们"),
    (60, "好兄弟"),
    (40, "朋友"),
    (20, "熟人"),
    (0, "不熟"),
]


@dataclass
class AffectionDisplay:
    affection_score: float
    affection_grade: str
    score_label: str  # e.g. "72 · 倾心" or "82 · 铁哥们"


def compute_affection_score(
    *,
    love: float,
    trust: float,
    attachment: float,
    security: float,
    respect: float,
    emotional_intimacy: float,
    conflict_penalty: float = 0.0,
) -> float:
    score = (
        love * 0.35
        + trust * 0.20
        + attachment * 0.15
        + security * 0.10
        + respect * 0.10
        + emotional_intimacy * 0.10
        - conflict_penalty
    )
    return max(0.0, min(100.0, round(score, 1)))


def score_to_grade(score: float, relationship_type: str = "romance") -> str:
    grades = FRIENDSHIP_GRADES if relationship_type == "brotherhood" else ROMANCE_GRADES
    for threshold, label in grades:
        if score >= threshold:
            return label
    return grades[-1][1]


def build_affection_display(
    *,
    love: float,
    trust: float,
    attachment: float,
    security: float,
    respect: float,
    emotional_intimacy: float,
    relationship_type: str = "romance",
    conflict_penalty: float = 0.0,
    preset_score: float | None = None,
    preset_grade: str | None = None,
) -> AffectionDisplay:
    score = preset_score if preset_score is not None else compute_affection_score(
        love=love,
        trust=trust,
        attachment=attachment,
        security=security,
        respect=respect,
        emotional_intimacy=emotional_intimacy,
        conflict_penalty=conflict_penalty,
    )
    grade = preset_grade or score_to_grade(score, relationship_type)
    prefix = "友情度" if relationship_type == "brotherhood" else "好感度"
    return AffectionDisplay(
        affection_score=score,
        affection_grade=grade,
        score_label=f"{prefix}：{int(round(score))} · {grade}",
    )
