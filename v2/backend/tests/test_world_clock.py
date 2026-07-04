"""Tests for shared world clock."""

from engine.world_clock import (
    LOCATION,
    TIMEZONE,
    format_clock,
    snapshot,
    world_rules_block,
)


def test_world_clock_timezone():
    assert TIMEZONE == "Asia/Shanghai"
    assert "云栖" in LOCATION


def test_world_clock_snapshot():
    s = snapshot(1719567890.0)
    assert s["timezone"] == TIMEZONE
    assert s["location"] == LOCATION
    assert len(s["clock"]) == 5  # HH:mm
    assert s["clock"][2] == ":"
    assert s["weekday"] in ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def test_format_clock_24h():
    # 2024-06-28 14:30:00 CST ≈ 1719562200 (approximate - use fixed ts from snapshot)
    s = snapshot(1719562200.0)
    assert format_clock(1719562200.0) == s["clock"]


def test_world_rules_block_includes_no_underwear_rule():
    block = world_rules_block()
    assert "无日常内衣" in block
    assert "胸罩" in block
    assert "情趣" in block
