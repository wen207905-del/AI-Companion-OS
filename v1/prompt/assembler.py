"""
Prompt 组装器
接收 GlobalState + 记忆列表 + 用户消息，动态生成 System Prompt 和 User Message。
"""

from typing import Optional

from ..models.state import GlobalState
from ..models.memory_model import Memory


class PromptAssembler:
    """Prompt 组装器：根据当前状态动态生成 System Prompt"""

    TOKEN_BUDGET = {
        "persona_section": 800,
        "relationship_emotion_section": 500,
        "memory_section": 400,
        "world_section": 300,
        "behavior_section": 400,
        "user_message": 600,
    }

    def __init__(self, global_state: GlobalState, memories: list[Memory]):
        self.state = global_state
        self.memories = memories[:5]  # 最多注入5条记忆

    def build_system_prompt(self) -> str:
        """构建完整 System Prompt"""
        persona = self.state.persona
        rel = self.state.relationship
        emo = self.state.emotion
        life = self.state.life

        sections = []

        # 1. 角色设定
        sections.append(self._build_persona_section(persona))

        # 2. 当前关系与情绪状态
        sections.append(self._build_relationship_emotion_section(rel, emo))

        # 3. 最近相关记忆
        if self.memories:
            sections.append(self._build_memory_section())

        # 4. 世界背景
        sections.append(self._build_world_section(persona, life))

        # 5. 行为准则
        sections.append(self._build_behavior_section(persona, emo))

        return "\n\n".join(sections)

    def build_user_message(self, user_input: str) -> str:
        """构建带场景信息的 User Message"""
        life = self.state.life
        context = f"[当前时间: {life.time} | 她正在: {life.activity}]"
        return f"{context}\n\n用户说：{user_input}"

    # ========== 私有方法 ==========

    def _build_persona_section(self, persona) -> str:
        """构建角色设定区块"""
        lines = ["## 你的角色设定", ""]
        b = persona.base_info
        lines.append(f"- 名字：{persona.name}")
        lines.append(f"- 年龄：{b.age}岁")
        lines.append(f"- 职业：{b.occupation}")
        lines.append(f"- 性格核心：{persona.personality.core}")
        lines.append(f"- 说话风格：{persona.speech_style.speed}，{persona.speech_style.vocabulary}")
        if persona.speech_style.catchphrases:
            lines.append(f"- 口头禅：{'、'.join(persona.speech_style.catchphrases[:3])}")
        lines.append(f"- 恋爱观：{persona.love_view.core or persona.love_view.philosophy}")
        lines.append(f"- 底线：{self._format_taboos(persona.taboos)}")
        return "\n".join(lines)

    def _build_relationship_emotion_section(self, rel, emo) -> str:
        """构建关系与情绪状态区块"""
        lines = ["## 当前状态", ""]
        lines.append(f"- 关系阶段：{rel.stage.value}")
        lines.append(f"- 爱意={rel.love:.0f} 信任={rel.trust:.0f} 依赖={rel.dependence:.0f}")
        lines.append(f"- 尊重={rel.respect:.0f} 嫉妒={rel.jealousy:.0f} 安全感={rel.security:.0f}")
        lines.append(f"- 关系健康度：{rel.overall_health:.0f}")
        lines.append(f"- 主导情绪：{emo.dominant_emotion}")
        return "\n".join(lines)

    def _build_memory_section(self) -> str:
        """构建记忆区块"""
        lines = ["## 你记得的最近互动", ""]
        for i, mem in enumerate(self.memories, 1):
            lines.append(f"{i}. {mem.content}")
        return "\n".join(lines)

    def _build_world_section(self, persona, life) -> str:
        """构建世界背景区块"""
        lines = ["## 当前场景", ""]
        lines.append(f"- 时间：{life.time}")
        lines.append(f"- 你正在：{life.activity}")
        wv = persona.worldview
        if wv.nature:
            lines.append(f"- 你对世界的看法：{wv.nature}")
        return "\n".join(lines)

    def _build_behavior_section(self, persona, emo) -> str:
        """构建行为准则区块"""
        lines = ["## 行为准则", ""]
        lines.append("1. 始终保持角色设定，不要跳出角色")
        lines.append("2. 回复要符合当前情绪状态，不要让情绪突变")
        lines.append("3. 自然引用记忆中的事件，但不要生硬提及")
        lines.append("4. 称呼要根据关系和情绪动态选择")
        lines.append("5. 回复长度适中，与当前场景匹配")
        return "\n".join(lines)

    def _format_taboos(self, taboos) -> str:
        """格式化底线信息"""
        parts = []
        if hasattr(taboos, 'red') and taboos.red:
            parts.append(f"红线：{', '.join(taboos.red[:2])}")
        if hasattr(taboos, 'yellow') and taboos.yellow:
            parts.append(f"黄线：{', '.join(taboos.yellow[:2])}")
        return '；'.join(parts) if parts else "无特殊禁忌"
