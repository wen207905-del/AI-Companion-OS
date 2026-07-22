"""Tests for V4.2 P0 group reply guards and orchestration helpers."""

from chat.group_reply_guard import sanitize_group_reply, wants_multi_responder
from chat.reply_service import _truncate_group_reply


def test_strip_own_name_prefix():
    result = sanitize_group_reply(
        "白柔：今天天气不错",
        own_name="白柔",
        other_member_names=["王大海"],
    )
    assert result.ok
    assert result.content == "今天天气不错"


def test_reject_other_member_prefix():
    result = sanitize_group_reply(
        "王大海：我来掷骰！",
        own_name="白柔",
        other_member_names=["王大海"],
    )
    assert not result.ok
    assert result.reason == "speaker_mismatch"


def test_same_turn_duplicate_blocked():
    first = "阳光洒在窗边，我把饮料推过去。"
    result = sanitize_group_reply(
        "阳光洒在窗边，我把饮料推了过去。",
        own_name="白柔",
        other_member_names=["王大海"],
        prior_reply_texts=[first],
        similarity_threshold=0.7,
    )
    assert not result.ok
    assert result.reason == "same_turn_duplicate"


def test_wants_multi_responder_broadcast():
    assert wants_multi_responder("大家都来说说看法")
    assert wants_multi_responder("@大家 今晚谁先来？")
    assert not wants_multi_responder("白柔你怎么看")


def test_wants_multi_responder_double_at():
    assert wants_multi_responder(
        "@白柔 @王大海 你们怎么看",
        member_names=["白柔", "王大海"],
    )


def test_truncate_group_reply_at_sentence():
    long = "第一句。" + ("很长的内容" * 80) + "。结尾了。"
    out = _truncate_group_reply(long, max_chars=80)
    assert len(out) <= 80
    assert out.endswith("。") or out.endswith("…")
