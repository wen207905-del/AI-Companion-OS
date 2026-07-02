"""Boundary engine tests."""

from engine.boundary_engine import BoundaryEngine


def test_boundary_red_trigger():
    engine = BoundaryEngine()
    persona = {
        "taboos": {
            "red": ["绝对无法接受出轨"],
            "yellow": ["不喜欢冷战"],
        },
    }
    result = engine.evaluate(persona, "你是不是出轨了")
    assert result["level"] == "red"
    assert result["prompt_hint"]


def test_boundary_ok():
    engine = BoundaryEngine()
    persona = {"taboos": {"red": ["家暴"], "yellow": []}}
    result = engine.evaluate(persona, "今天天气不错")
    assert result["level"] == "ok"
