"""Tests for reply_service helpers."""

from chat.reply_service import infer_action, parse_chat_structured


def test_infer_action_smile():
    assert infer_action("哈哈，太开心了")["type"] == "smile"


def test_infer_action_pout():
    assert infer_action("你讨厌！")["type"] == "pout"


def test_infer_action_sleep():
    assert infer_action("晚安，睡了")["type"] == "sleep"


def test_infer_action_default_talk():
    assert infer_action("今天天气不错")["type"] == "talk"


def test_parse_chat_structured_action_and_dialogue():
    raw = "【动作】微微挑眉，语气平静\n叶如雪：「你怎么来了？」"
    content, action = parse_chat_structured(raw, "叶如雪")
    assert content == "你怎么来了？"
    assert action["type"] == "action"
    assert "挑眉" in action["text"]


def test_parse_chat_structured_dialogue_only():
    content, action = parse_chat_structured("「在的，怎么了？」", "王大海")
    assert content == "在的，怎么了？"
    assert action["type"] == "talk"
