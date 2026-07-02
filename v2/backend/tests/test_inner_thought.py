"""Inner thought sanitization tests."""

from chat.reply_service import (
    _build_inner_thought_prompt,
    _sanitize_inner_thought,
    _strip_leaked_inner_blocks,
)


def test_strip_leaked_inner_blocks():
    raw = "*她笑了笑。*\n【内心】其实很想他。\n「嗯。」"
    cleaned = _strip_leaked_inner_blocks(raw)
    assert "【内心】" not in cleaned
    assert "她笑了笑" in cleaned


def test_sanitize_rejects_system_errors():
    assert _sanitize_inner_thought(
        "LLM 未配置：请在 .env 中设置 DEEPSEEK_API_KEY",
        character_name="白柔",
        user_name="许汉文",
    ) == ""


def test_sanitize_rejects_user_pov():
    assert _sanitize_inner_thought(
        "许汉文心里有点乱，不知道该怎么办",
        character_name="白柔",
        user_name="许汉文",
    ) == ""


def test_sanitize_keeps_character_pov():
    text = _sanitize_inner_thought(
        "其实……被他这样看着，腿都软了。",
        character_name="白柔",
        user_name="许汉文",
    )
    assert "腿都软了" in text


def test_inner_thought_prompt_clarifies_roles():
    prompt = _build_inner_thought_prompt(
        name="白柔",
        content="「过来。」",
        chat_mode="private",
        user_message="我回来了",
        group_name="",
    )
    assert "白柔" in prompt
    assert "许汉文" in prompt
    assert "不是用户" in prompt

    group_prompt = _build_inner_thought_prompt(
        name="王大海",
        content="「哈哈。」",
        chat_mode="group",
        user_message="大家好",
        group_name="测试群",
    )
    assert "群聊" in group_prompt
    assert "王大海本人" in group_prompt
