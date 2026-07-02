"""Tests for group prompt building."""

from chat.prompt_builder import PromptBuilder


def test_build_group_messages_includes_relationship_and_history():
    persona = {
        "name": "白柔",
        "type": "老婆",
        "base_info": {"occupation": "全职主妇"},
        "personality": {"core": "温柔给予型"},
        "hobbies": ["烹饪", "烘焙"],
        "love_view": {"core": "爱是日常陪伴"},
        "chat_behavior": {"group_tendency": "关心大家吃没吃饭"},
    }
    builder = PromptBuilder(persona)
    rel = {"stage": 6, "stage_name": "恋人", "love": 90, "trust": 88}
    emo = {"primary_mood": "开心"}
    history = [
        {"role": "user", "content": "今晚吃什么"},
        {"role": "assistant", "content": "白柔：我做了红烧肉"},
    ]
    messages = builder.build_group_messages(
        emo, rel, "全体成员", ["柳青柠"], "好吃吗？",
        history=history,
    )

    system = messages[0]["content"]
    assert "恋人" in system
    assert "烹饪" in system or "烘焙" in system
    assert "许汉文" in messages[-1]["content"]
    assert "好吃吗" in messages[-1]["content"]
    assert len(messages) >= 4  # system + history + user
