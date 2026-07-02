"""Tests for reply_service helpers."""

from chat.reply_service import infer_action


def test_infer_action_smile():
    assert infer_action("哈哈，太开心了")["type"] == "smile"


def test_infer_action_pout():
    assert infer_action("你讨厌！")["type"] == "pout"


def test_infer_action_sleep():
    assert infer_action("晚安，睡了")["type"] == "sleep"


def test_infer_action_default_talk():
    assert infer_action("今天天气不错")["type"] == "talk"
