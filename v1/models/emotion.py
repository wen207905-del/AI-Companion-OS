"""
情绪引擎数据模型
9个基础情绪维度：Happy/Sad/Fear/Angry/Jealous/Tired/Excited/Lonely/Calm
"""

from pydantic import BaseModel, Field
from typing import ClassVar


class EmotionState(BaseModel):
    """
    情绪状态，包含9个情绪维度
    取值范围 [0, 100]
    """

    happy: float = Field(default=60.0, ge=0.0, le=100.0, description="开心")
    sad: float = Field(default=5.0, ge=0.0, le=100.0, description="悲伤")
    fear: float = Field(default=5.0, ge=0.0, le=100.0, description="恐惧")
    angry: float = Field(default=0.0, ge=0.0, le=100.0, description="生气")
    jealous: float = Field(default=0.0, ge=0.0, le=100.0, description="嫉妒")
    tired: float = Field(default=10.0, ge=0.0, le=100.0, description="疲惫")
    excited: float = Field(default=20.0, ge=0.0, le=100.0, description="兴奋")
    lonely: float = Field(default=15.0, ge=0.0, le=100.0, description="孤独")
    calm: float = Field(default=70.0, ge=0.0, le=100.0, description="平静")

    # 衰减速率（类变量，每 tick）
    DECAY_RATES: ClassVar[dict[str, float]] = {
        "happy": 0.03,
        "sad": 0.02,
        "fear": 0.04,
        "angry": 0.015,
        "jealous": 0.02,
        "tired": 0.08,
        "excited": 0.06,
        "lonely": 0.01,
        "calm": 0.01,
    }

    # 情绪混合权重
    MIX_WEIGHTS: ClassVar[dict[str, dict[str, float]]] = {
        "sad_angry": {"sad": 0.55, "angry": 0.45},
        "sad_lonely": {"sad": 0.7, "lonely": 0.3},
        "happy_excited": {"happy": 0.4, "excited": 0.6},
        "angry_jealous": {"angry": 0.4, "jealous": 0.6},
        "fear_sad": {"fear": 0.6, "sad": 0.4},
    }

    @property
    def dominant_emotion(self) -> tuple[str, float]:
        """
        获取主导情绪（综合混合规则）

        Returns:
            (情绪名称, 混合后强度)
        """
        # 获取原始最高值
        emotions = {
            "happy": self.happy,
            "sad": self.sad,
            "fear": self.fear,
            "angry": self.angry,
            "jealous": self.jealous,
            "tired": self.tired,
            "excited": self.excited,
            "lonely": self.lonely,
            "calm": self.calm,
        }

        # 最高单情绪
        top_name = max(emotions, key=emotions.get)
        top_val = emotions[top_name]

        # 如果多个负面情绪同时存在，使用混合规则
        if self.sad > 30 and self.angry > 20:
            w = self.MIX_WEIGHTS["sad_angry"]
            mixed = self.sad * w["sad"] + self.angry * w["angry"]
            return ("sad_angry", round(mixed, 1))

        if self.sad > 30 and self.lonely > 30:
            w = self.MIX_WEIGHTS["sad_lonely"]
            mixed = self.sad * w["sad"] + self.lonely * w["lonely"]
            return ("sad_lonely", round(mixed, 1))

        if self.angry > 20 and self.jealous > 20:
            w = self.MIX_WEIGHTS["angry_jealous"]
            mixed = self.angry * w["angry"] + self.jealous * w["jealous"]
            return ("angry_jealous", round(mixed, 1))

        if self.fear > 20 and self.sad > 20:
            w = self.MIX_WEIGHTS["fear_sad"]
            mixed = self.fear * w["fear"] + self.sad * w["sad"]
            return ("fear_sad", round(mixed, 1))

        return (top_name, top_val)

    @property
    def is_negative_dominant(self) -> bool:
        """当前是否以负面情绪为主导"""
        name, _ = self.dominant_emotion
        return name in ("sad", "angry", "fear", "jealous", "lonely",
                        "sad_angry", "sad_lonely", "angry_jealous", "fear_sad")

    def mix_emotions(self, primary: str, secondary: str, primary_val: float, secondary_val: float) -> tuple[str, float]:
        """
        计算两种情绪混合后的结果

        Args:
            primary: 主情绪名称
            secondary: 次情绪名称
            primary_val: 主情绪强度
            secondary_val: 次情绪强度

        Returns:
            (混合情绪名称, 混合强度)
        """
        key = f"{primary}_{secondary}"
        if key in self.MIX_WEIGHTS:
            w = self.MIX_WEIGHTS[key]
            val = primary_val * w[primary] + secondary_val * w[secondary]
            return (key, round(val, 1))
        # 没有预定义规则时使用加权平均
        avg = (primary_val * 0.6 + secondary_val * 0.4)
        return (primary, round(avg, 1))

    def clamp_all(self):
        """将所有情绪维度裁剪到 [0, 100]"""
        for name in ["happy", "sad", "fear", "angry", "jealous",
                      "tired", "excited", "lonely", "calm"]:
            val = getattr(self, name)
            setattr(self, name, max(0.0, min(100.0, round(val, 1))))

    def to_dict(self) -> dict:
        """导出为字典"""
        dominant_name, dominant_val = self.dominant_emotion
        return {
            "happy": self.happy,
            "sad": self.sad,
            "fear": self.fear,
            "angry": self.angry,
            "jealous": self.jealous,
            "tired": self.tired,
            "excited": self.excited,
            "lonely": self.lonely,
            "calm": self.calm,
            "dominant": dominant_name,
            "dominant_value": dominant_val,
            "is_negative": self.is_negative_dominant,
        }
