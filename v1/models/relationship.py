"""
关系引擎数据模型
6个核心维度：Love(爱意)、Trust(信任)、Dependence(依赖度)、Respect(尊重)、Jealousy(嫉妒值)、Security(安全感)
"""

from pydantic import BaseModel, Field, model_validator
from typing import ClassVar
from enum import Enum


class RelationStage(str, Enum):
    """关系阶段枚举"""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    AMBIGUOUS = "ambiguous"
    PASSIONATE = "passionate"
    STABLE = "stable"
    PARTNER = "partner"
    SOULMATE = "soulmate"


class RelationshipState(BaseModel):
    """
    关系状态，包含6个维度和当前关系阶段
    所有维度取值范围 [0, 100]
    """

    love: float = Field(default=10.0, ge=0.0, le=100.0, description="爱意")
    trust: float = Field(default=15.0, ge=0.0, le=100.0, description="信任")
    dependence: float = Field(default=5.0, ge=0.0, le=100.0, description="依赖度")
    respect: float = Field(default=20.0, ge=0.0, le=100.0, description="尊重")
    jealousy: float = Field(default=5.0, ge=0.0, le=100.0, description="嫉妒值")
    security: float = Field(default=30.0, ge=0.0, le=100.0, description="安全感")

    # 阶段阈值定义（类变量）
    STAGE_THRESHOLDS: ClassVar[list[tuple[RelationStage, float, float]]] = [
        (RelationStage.STRANGER, 0.0, 19.9),
        (RelationStage.ACQUAINTANCE, 20.0, 34.9),
        (RelationStage.FRIEND, 35.0, 49.9),
        (RelationStage.AMBIGUOUS, 50.0, 64.9),
        (RelationStage.PASSIONATE, 65.0, 79.9),
        (RelationStage.STABLE, 80.0, 89.9),
        (RelationStage.PARTNER, 90.0, 97.9),
        (RelationStage.SOULMATE, 98.0, 100.0),
    ]

    @property
    def stage(self) -> RelationStage:
        """根据 love 值计算当前关系阶段"""
        for stage, low, high in self.STAGE_THRESHOLDS:
            if low <= self.love <= high:
                return stage
        return RelationStage.STRANGER

    @property
    def overall_health(self) -> float:
        """
        关系整体健康度
        综合 love/trust/security/resepect 四个正面维度，减去 jealousy/dependence 的负面影响
        """
        positive = (self.love * 0.35 + self.trust * 0.25 +
                    self.security * 0.25 + self.respect * 0.15)
        negative = (self.jealousy * 0.5 + self.dependence * 0.1)
        return max(0.0, min(100.0, positive - negative))

    def clamp_all(self):
        """将所有维度裁剪到 [0, 100] 范围"""
        for field_name in ["love", "trust", "dependence", "respect", "jealousy", "security"]:
            val = getattr(self, field_name)
            setattr(self, field_name, max(0.0, min(100.0, round(val, 1))))

    def to_dict(self) -> dict:
        """导出为字典，包含阶段信息"""
        return {
            "love": self.love,
            "trust": self.trust,
            "dependence": self.dependence,
            "respect": self.respect,
            "jealousy": self.jealousy,
            "security": self.security,
            "stage": self.stage.value,
            "overall_health": round(self.overall_health, 1),
        }
