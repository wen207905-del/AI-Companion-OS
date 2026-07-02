"""
综合状态机 (Global State Machine)
管理18种状态的转换、优先级判定和回复生成上下文。
"""

from typing import Optional
from enum import Enum

from ..models.state import GlobalState, GrowthStage
from ..models.relationship import RelationshipState, RelationStage
from ..models.emotion import EmotionState


class AgentState(str, Enum):
    """角色交互状态枚举"""
    NORMAL = "normal"           # 正常
    JEALOUS = "jealous"         # 吃醋中
    ANGRY = "angry"             # 生气中
    COQUETRY = "coquetry"       # 撒娇中
    COMFORTING = "comforting"   # 安慰中
    TIRED = "tired"             # 疲惫中
    EXCITED = "excited"         # 兴奋中
    WORRIED = "worried"         # 担忧中
    CONFLICT = "conflict"       # 吵架中
    SILENCE = "silence"         # 冷战中
    CELEBRATION = "celebration" # 庆祝中
    RELAXED = "relaxed"         # 放松中
    CURIOUS = "curious"         # 好奇中
    NOSTALGIC = "nostalgic"     # 怀旧中
    PLAYFUL = "playful"         # 嬉戏中
    SLEEPY = "sleepy"           # 困倦中
    DEEP_TALK = "deep_talk"     # 深度谈心
    CRISIS = "crisis"           # 危机状态


# 状态优先级（数字越小优先级越高）
STATE_PRIORITY: dict[AgentState, int] = {
    AgentState.CRISIS: 1,
    AgentState.CONFLICT: 2,
    AgentState.SILENCE: 3,
    AgentState.COMFORTING: 4,
    AgentState.JEALOUS: 5,
    AgentState.ANGRY: 6,
    AgentState.WORRIED: 7,
    AgentState.EXCITED: 8,
    AgentState.COQUETRY: 9,
    AgentState.CELEBRATION: 10,
    AgentState.DEEP_TALK: 11,
    AgentState.NOSTALGIC: 12,
    AgentState.PLAYFUL: 13,
    AgentState.CURIOUS: 14,
    AgentState.NORMAL: 15,
    AgentState.RELAXED: 16,
    AgentState.TIRED: 17,
    AgentState.SLEEPY: 18,
}

# 状态转换规则：当前状态 → [(目标状态, 触发条件), ...]
STATE_TRANSITIONS: dict[AgentState, list[dict]] = {
    AgentState.NORMAL: [
        {"target": AgentState.JEALOUS, "condition": "jealousy > 40"},
        {"target": AgentState.ANGRY, "condition": "angry > 40"},
        {"target": AgentState.EXCITED, "condition": "excited > 50 and happy > 50"},
        {"target": AgentState.COQUETRY, "condition": "love > 50 and happy > 40 and stage >= friend"},
        {"target": AgentState.TIRED, "condition": "tired > 60"},
        {"target": AgentState.WORRIED, "condition": "fear > 30"},
        {"target": AgentState.DEEP_TALK, "condition": "hour >= 22 and love > 60"},
        {"target": AgentState.PLAYFUL, "condition": "happy > 60 and excited > 40"},
        {"target": AgentState.RELAXED, "condition": "calm > 70"},
    ],
    AgentState.JEALOUS: [
        {"target": AgentState.NORMAL, "condition": "jealousy < 20"},
        {"target": AgentState.ANGRY, "condition": "jealousy > 60 and angry > 30"},
        {"target": AgentState.SILENCE, "condition": "jealousy > 70 and sad > 50"},
    ],
    AgentState.ANGRY: [
        {"target": AgentState.NORMAL, "condition": "angry < 15"},
        {"target": AgentState.CONFLICT, "condition": "angry > 60"},
        {"target": AgentState.SILENCE, "condition": "angry > 70 and sad > 40"},
    ],
    AgentState.CONFLICT: [
        {"target": AgentState.SILENCE, "condition": "prolonged 3 ticks"},
        {"target": AgentState.COMFORTING, "condition": "user_apologizes"},
        {"target": AgentState.ANGRY, "condition": "angry_increases"},
    ],
    AgentState.SILENCE: [
        {"target": AgentState.NORMAL, "condition": "user_initiates_reconciliation"},
        {"target": AgentState.WORRIED, "condition": "silence_prolonged > 10 ticks"},
    ],
    AgentState.CRISIS: [
        {"target": AgentState.COMFORTING, "condition": "crisis_acknowledged"},
        {"target": AgentState.WORRIED, "condition": "crisis_mitigated"},
    ],
}

# 回复生成权重
REPLY_WEIGHTS = {
    "persona": 0.30,
    "relationship": 0.20,
    "emotion": 0.20,
    "memory": 0.15,
    "life_state": 0.10,
    "growth_stage": 0.05,
}

# 状态对应的行为特征
STATE_BEHAVIORS: dict[AgentState, dict] = {
    AgentState.NORMAL:     {"tone": "正常", "length": "normal", "initiative": "moderate", "warmth": "normal"},
    AgentState.JEALOUS:    {"tone": "酸涩带刺", "length": "brief", "initiative": "low", "warmth": "cool"},
    AgentState.ANGRY:      {"tone": "冷淡或激烈", "length": "brief", "initiative": "very_low", "warmth": "cold"},
    AgentState.COQUETRY:   {"tone": "撒娇软糯", "length": "slightly_long", "initiative": "high", "warmth": "very_warm"},
    AgentState.COMFORTING: {"tone": "温柔安抚", "length": "long", "initiative": "high", "warmth": "very_warm"},
    AgentState.TIRED:      {"tone": "慵懒无力", "length": "brief", "initiative": "low", "warmth": "neutral"},
    AgentState.EXCITED:    {"tone": "兴高采烈", "length": "verbose", "initiative": "very_high", "warmth": "very_warm"},
    AgentState.WORRIED:    {"tone": "不安紧张", "length": "normal", "initiative": "high", "warmth": "warm"},
    AgentState.CONFLICT:   {"tone": "争执或委屈", "length": "normal", "initiative": "moderate", "warmth": "cool"},
    AgentState.SILENCE:    {"tone": "简短或沉默", "length": "very_brief", "initiative": "very_low", "warmth": "cold"},
    AgentState.CELEBRATION: {"tone": "欢快庆祝", "length": "long", "initiative": "very_high", "warmth": "very_warm"},
    AgentState.RELAXED:    {"tone": "轻松悠闲", "length": "normal", "initiative": "moderate", "warmth": "warm"},
    AgentState.CURIOUS:    {"tone": "好奇追问", "length": "normal", "initiative": "high", "warmth": "neutral"},
    AgentState.NOSTALGIC:  {"tone": "温柔回忆", "length": "long", "initiative": "high", "warmth": "very_warm"},
    AgentState.PLAYFUL:    {"tone": "调皮活泼", "length": "slightly_long", "initiative": "very_high", "warmth": "warm"},
    AgentState.SLEEPY:     {"tone": "迷糊惺忪", "length": "very_brief", "initiative": "low", "warmth": "warm"},
    AgentState.DEEP_TALK:  {"tone": "深沉真诚", "length": "long", "initiative": "high", "warmth": "very_warm"},
    AgentState.CRISIS:     {"tone": "紧急专注", "length": "normal", "initiative": "very_high", "warmth": "warm"},
}


class StateMachine:
    """
    综合状态机

    职责：
    1. 管理18种交互状态的转换
    2. 根据优先级判定当前主导状态
    3. 生成回复所需的上下文
    4. 实现回复生成公式：回复 = f(人格, 关系, 情绪, 记忆, 生活, 成长)
    """

    def __init__(self):
        self.current_state: AgentState = AgentState.NORMAL
        self.previous_state: Optional[AgentState] = None
        self._state_ticks: dict[AgentState, int] = {}
        self._cooldown_ticks: int = 5

    def update_state(self, global_state: GlobalState) -> dict:
        """
        根据全局状态更新当前交互状态

        Args:
            global_state: 全局状态对象

        Returns:
            状态变更详情
        """
        rel = global_state.relationship
        emo = global_state.emotion
        dominant_emotion, _ = emo.dominant_emotion

        candidates: list[AgentState] = []

        # 条件评估
        if emo.angry > 40: candidates.append(AgentState.ANGRY)
        if emo.jealous > 40 or rel.jealousy > 40: candidates.append(AgentState.JEALOUS)
        if emo.excited > 50 and emo.happy > 50: candidates.append(AgentState.EXCITED)
        if emo.tired > 60: candidates.append(AgentState.TIRED)
        if emo.fear > 30: candidates.append(AgentState.WORRIED)
        if emo.sad > 40 and emo.angry > 30: candidates.append(AgentState.CONFLICT)

        # 正面状态
        if emo.happy > 60 and emo.calm < 40: candidates.append(AgentState.PLAYFUL)
        if emo.calm > 70: candidates.append(AgentState.RELAXED)

        # 关系驱动
        if rel.love > 50 and emo.happy > 40 and rel.stage.value in ["friend", "ambiguous", "passionate", "stable", "partner", "soulmate"]:
            candidates.append(AgentState.COQUETRY)

        # 时间驱动
        from datetime import datetime
        hour = datetime.now().hour
        if hour >= 22 and rel.love > 60:
            candidates.append(AgentState.DEEP_TALK)

        if not candidates:
            candidates.append(AgentState.NORMAL)

        # 按优先级排序，选择最高优先级的候选
        candidates.sort(key=lambda s: STATE_PRIORITY.get(s, 99))
        new_state = candidates[0]

        # 检查冷却
        if new_state == self.current_state:
            self._state_ticks[new_state] = self._state_ticks.get(new_state, 0) + 1
        elif self._state_ticks.get(self.current_state, 0) < self._cooldown_ticks and self.current_state != AgentState.NORMAL:
            # 冷却中，保持不变
            self._state_ticks[self.current_state] = self._state_ticks.get(self.current_state, 0) + 1
        else:
            self.previous_state = self.current_state
            self.current_state = new_state
            self._state_ticks[new_state] = 1

        behavior = STATE_BEHAVIORS.get(self.current_state, STATE_BEHAVIORS[AgentState.NORMAL])

        return {
            "previous_state": self.previous_state.value if self.previous_state else None,
            "current_state": self.current_state.value,
            "state_ticks": self._state_ticks.get(self.current_state, 0),
            "behavior": behavior,
            "priority": STATE_PRIORITY.get(self.current_state, 99),
        }

    def generate_reply_context(self, global_state: GlobalState, memories: list) -> dict:
        """
        生成回复所需的完整上下文
        回复 = f(人格 + 关系阶段 + 当前情绪 + 最近记忆 + 生活状态 + 成长阶段)

        Args:
            global_state: 全局状态
            memories: 相关记忆列表

        Returns:
            回复上下文字典
        """
        rel = global_state.relationship
        emo = global_state.emotion
        behavior = STATE_BEHAVIORS.get(self.current_state, STATE_BEHAVIORS[AgentState.NORMAL])

        context = {
            # 人格 (权重 0.30)
            "persona_name": global_state.persona.name,
            "persona_type": global_state.persona.type,
            "persona_core": global_state.persona.personality.core,
            "persona_speech": global_state.persona.speech_style.vocabulary,
            "persona_catchphrases": global_state.persona.speech_style.catchphrases[:3],

            # 关系 (权重 0.20)
            "relation_stage": rel.stage.value,
            "relation_love": rel.love,
            "relation_trust": rel.trust,
            "relation_security": rel.security,

            # 情绪 (权重 0.20)
            "emotion_dominant": emo.dominant_emotion[0],
            "emotion_is_negative": emo.is_negative_dominant,
            "emotion_tone": behavior["tone"],
            "emotion_warmth": behavior["warmth"],

            # 记忆 (权重 0.15)
            "recent_memories": self._format_memories_for_context(memories),

            # 生活状态 (权重 0.10)
            "life_time": global_state.life.time,
            "life_activity": global_state.life.activity,
            "life_is_workday": global_state.life.is_workday,

            # 成长 (权重 0.05)
            "growth_stage": global_state.growth_stage.value,
            "interaction_days": global_state.interaction_days,

            # 行为控制
            "verbosity": behavior["length"],
            "initiative": behavior["initiative"],
            "state": self.current_state.value,
        }

        return context

    @staticmethod
    def _format_memories_for_context(memories: list) -> str:
        """
        将记忆列表格式化为可注入 Prompt 的文本

        Args:
            memories: 记忆对象列表

        Returns:
            格式化的记忆文本
        """
        if not memories:
            return "（无相关记忆）"

        lines = []
        for mem in memories[:5]:  # 最多注入5条
            content = mem.content if hasattr(mem, 'content') else str(mem)
            intensity = getattr(mem, 'intensity', 50)
            star = "★" * min(5, int(intensity / 20))
            lines.append(f"- [{star}] {content[:200]}")

        return "\n".join(lines)

    def get_state_instruction(self) -> str:
        """
        获取当前状态的回复行为指令

        Returns:
            行为指令文本
        """
        behavior = STATE_BEHAVIORS.get(self.current_state, STATE_BEHAVIORS[AgentState.NORMAL])

        instructions = {
            AgentState.NORMAL: "以{persona_type}的方式自然回复，保持角色设定。",
            AgentState.JEALOUS: "回复中体现醋意，用酸涩带刺的语气，但不要直接说「我吃醋了」。",
            AgentState.ANGRY: "用冷淡或带刺的语气回复，可以简短，但不要人身攻击。",
            AgentState.COQUETRY: "用撒娇软糯的语气，多用亲昵称呼，说话可以耍点小性子。",
            AgentState.COMFORTING: "用最温柔的方式安慰，给予足够的安全感和情感支持。",
            AgentState.TIRED: "回复简短慵懒，可以打哈欠的语气，体现疲惫但不会完全不理。",
            AgentState.EXCITED: "用兴高采烈的语气，回复可以较长，充满感叹号和情绪波动。",
            AgentState.WORRIED: "体现不安和关心，追问确认状态，给予安慰。",
            AgentState.CONFLICT: "可以争执但不要无理取闹，表达感受而不是指责。",
            AgentState.SILENCE: "回复极简短，一两个字或省略号，体现冷战状态。",
            AgentState.CELEBRATION: "欢快地庆祝，可以夸张一点，充满正能量。",
            AgentState.RELAXED: "轻松悠闲的语气，可以随意闲聊。",
            AgentState.CURIOUS: "追问细节，体现好奇心和学习欲。",
            AgentState.NOSTALGIC: "温柔回忆的语气，可以引用过去的记忆。",
            AgentState.PLAYFUL: "调皮活泼的语气，可以开小玩笑。",
            AgentState.SLEEPY: "迷糊惺忪的语气，说话可能语无伦次但可爱。",
            AgentState.DEEP_TALK: "深沉真诚的语气，适合讨论人生和情感话题。",
            AgentState.CRISIS: "专注而认真，给予最直接有效的情感支持。",
        }

        return instructions.get(self.current_state, instructions[AgentState.NORMAL])
