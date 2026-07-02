"""
全局状态模型
聚合 Persona + RelationshipState + EmotionState + 生活状态 + 成长阶段
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

from .persona import Persona
from .relationship import RelationshipState, RelationStage
from .emotion import EmotionState


class GrowthStage(str, Enum):
    """成长阶段枚举"""
    INITIAL = "initial"       # 初始状态 (0-3个月)
    WARMING = "warming"       # 熟悉期 (3-6个月)
    TRUST = "trust"           # 信任期 (6-12个月)
    DEEP = "deep"             # 深度发展期 (1-2年)
    MATURE = "mature"         # 成熟期 (2年+)


class LifeActivity(BaseModel):
    """当前生活活动"""
    time: str = Field(description="当前时间 HH:MM")
    activity: str = Field(description="当前活动描述")
    is_workday: bool = Field(default=True, description="是否工作日")
    season: str = Field(default="summer", description="季节")


class GlobalState(BaseModel):
    """
    全局状态，聚合所有子系统状态
    作为请求上下文传递给 Prompt 组装器和各引擎
    """

    # 人格
    persona: Persona = Field(description="当前角色人格")

    # 关系
    relationship: RelationshipState = Field(default_factory=RelationshipState, description="关系状态")

    # 情绪
    emotion: EmotionState = Field(default_factory=EmotionState, description="情绪状态")

    # 生活
    life: LifeActivity = Field(
        default_factory=lambda: LifeActivity(time="09:00", activity="工作中", is_workday=True, season="summer"),
        description="当前生活状态"
    )

    # 成长
    growth_stage: GrowthStage = Field(default=GrowthStage.INITIAL, description="当前成长阶段")
    interaction_days: int = Field(default=0, description="累计互动天数")
    milestones_completed: list[str] = Field(default_factory=list, description="已完成的里程碑事件名")

    # 元数据
    current_time: str = Field(default_factory=lambda: datetime.now().isoformat(), description="当前时间")

    def get_reply_context(self) -> dict:
        """
        生成用于回复生成的完整上下文字典

        Returns:
            包含所有状态信息的字典
        """
        return {
            "persona_name": self.persona.name,
            "persona_type": self.persona.type,
            "relation_stage": self.relationship.stage.value,
            "relation_love": self.relationship.love,
            "emotion_dominant": self.emotion.dominant_emotion[0],
            "emotion_is_negative": self.emotion.is_negative_dominant,
            "life_activity": self.life.activity,
            "life_time": self.life.time,
            "growth_stage": self.growth_stage.value,
            "interaction_days": self.interaction_days,
        }

    def summary(self) -> str:
        """
        生成可读的状态摘要

        Returns:
            状态摘要字符串
        """
        rel = self.relationship
        emo = self.emotion
        dom_name, dom_val = emo.dominant_emotion

        lines = [
            f"角色: {self.persona.name} ({self.persona.type})",
            f"关系: {rel.stage.value} | 爱意:{rel.love:.0f} 信任:{rel.trust:.0f} 安全感:{rel.security:.0f}",
            f"情绪: {dom_name}({dom_val:.0f}) | 开心:{emo.happy:.0f} 平静:{emo.calm:.0f}",
            f"生活: {self.life.time} {self.life.activity}",
            f"成长: {self.growth_stage.value} | 互动天数:{self.interaction_days}",
            f"里程碑: {', '.join(self.milestones_completed[-5:]) or '无'}",
        ]
        return "\n".join(lines)
