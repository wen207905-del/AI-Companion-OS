"""Tests for event analyzer baseline stat growth."""

from event.event_analyzer import event_analyzer
from event.event_bus import EventBus


def test_conversation_baseline_always_adds_relationship_effects():
    bus = EventBus()
    event = bus.create_event(
        event_type="conversation",
        participants=["user", "mo_xiaoran"],
        raw_input="今天天气不错",
    )
    result = event_analyzer.analyze(event)
    rel_effects = [e for e in result.effects if e["engine"] == "relationship"]
    assert len(rel_effects) >= 4
    fields = {e["field"] for e in rel_effects}
    assert "love" in fields
    assert "attachment" in fields


def test_intimate_message_adds_physical_intimacy():
    bus = EventBus()
    event = bus.create_event(
        event_type="conversation",
        participants=["user", "mo_xiaoran"],
        raw_input="抱着她轻轻亲吻",
    )
    result = event_analyzer.analyze(event)
    physical = [
        e for e in result.effects
        if e["engine"] == "relationship" and e["field"] == "intimacy_physical"
    ]
    assert physical
    assert sum(e["delta"] for e in physical) >= 1.0
