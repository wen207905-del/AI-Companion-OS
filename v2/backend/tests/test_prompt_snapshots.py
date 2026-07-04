"""Prompt builder regression tests — key sections must appear."""

from chat.prompt_builder import PromptBuilder
from memory.memory_manager import format_memories_block


def _sample_persona():
    return {
        "name": "白柔",
        "type": "老婆",
        "base_info": {"occupation": "全职主妇"},
        "personality": {"core": "温柔给予型"},
        "hobbies": ["烹饪", "烘焙"],
        "love_view": {"core": "陪伴是最长情的告白"},
        "chat_behavior": {"group_tendency": "关心大家吃没吃饭"},
        "shared_history": {
            "relationship_status": "妻子",
            "memorable_moments": ["雷雨夜留灯"],
        },
        "speech_style": {"catchphrases": ["回来啦？辛苦了。"]},
        "taboos": {"red": ["出轨"], "yellow": ["冷战"]},
    }


def test_private_prompt_includes_depth_and_history():
    builder = PromptBuilder(_sample_persona())
    system = builder.build_private_system(
        {"stage": 6, "stage_name": "恋人", "love": 90, "trust": 88},
        {"primary_mood": "开心"},
        {"private_tone": "柔软", "habits": []},
    )
    assert "白柔" in system
    assert "许汉文" in system
    assert "烹饪" in system or "烘焙" in system
    assert "妻子" in system or "雷雨夜" in system


def test_private_messages_with_memory_and_boundary():
    builder = PromptBuilder(_sample_persona())
    memory_text = format_memories_block(["用户：今晚吃什么", "我：做了红烧肉"])
    boundary_hint = "【底线触发——用户刚才的话严重触碰了你的绝对禁忌"
    messages = builder.build_private_messages(
        {"stage": 5, "stage_name": "暧昧", "love": 70, "trust": 60},
        {"primary_mood": "生气"},
        {"private_tone": "冷", "habits": []},
        [{"role": "user", "content": "你是不是不爱我了"}],
        memory_text=memory_text,
        boundary_hint=boundary_hint,
        user_message="那你现在还想我吗",
    )
    system = messages[0]["content"]
    assert "相关记忆" in system
    assert "底线触发" in system
    assert "那你现在还想我吗" in system
    assert "对话连贯性" in system
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "那你现在还想我吗"


def test_group_messages_structure():
    builder = PromptBuilder(_sample_persona())
    messages = builder.build_group_messages(
        {"primary_mood": "平静"},
        {"stage": 4, "stage_name": "朋友", "love": 50},
        "全体成员",
        ["柳青柠"],
        "大家晚上吃什么？",
        history=[{"role": "user", "content": "大家好"}],
    )
    assert messages[0]["role"] == "system"
    assert "大家晚上吃什么？" in messages[-1]["content"]
    assert "群聊" in messages[0]["content"]


def test_group_chain_messages():
    builder = PromptBuilder(_sample_persona())
    messages = builder.build_group_chain_messages(
        {"primary_mood": "开心"},
        {"stage": 4, "stage_name": "朋友", "love": 50},
        "全体成员",
        ["柳青柠"],
        "今天好累",
        "柳青柠",
        "哼，谁要你管。",
    )
    assert "接话" in messages[0]["content"]
    assert "柳青柠" in messages[-1]["content"]
