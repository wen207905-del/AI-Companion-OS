"""
情绪引擎 (Emotion Engine)
管理9个基础情绪维度，处理情绪混合、衰减、触发转换和五阶段持久性模型。
"""

from ..models.emotion import EmotionState
from enum import Enum
from typing import Optional


class EmotionPhase(str, Enum):
    """五阶段情绪持久性模型"""
    BURST = "burst"       # 爆发
    PEAK = "peak"         # 高峰
    EASE = "ease"         # 缓和
    OBSERVE = "observe"   # 观察
    RECOVERY = "recovery" # 恢复


# 情绪触发事件及其效果
EMOTION_TRIGGERS: dict[str, dict[str, float]] = {
    "compliment_received":      {"happy": 8.0, "excited": 4.0, "calm": -3.0},
    "gift_received":            {"happy": 10.0, "excited": 6.0, "lonely": -5.0},
    "user_expressed_love":      {"happy": 12.0, "excited": 8.0, "lonely": -10.0, "fear": -5.0},
    "user_cold_shoulder":       {"sad": 10.0, "lonely": 8.0, "angry": 5.0, "happy": -10.0, "calm": -8.0},
    "user_angry_at_her":        {"sad": 12.0, "fear": 10.0, "angry": 8.0, "happy": -15.0, "calm": -10.0},
    "user_mentioned_other":     {"jealous": 12.0, "sad": 5.0, "angry": 4.0, "happy": -5.0},
    "user_threaten_leave":      {"sad": 18.0, "fear": 15.0, "angry": 10.0, "happy": -20.0},
    "user_ignores_her":         {"lonely": 12.0, "sad": 8.0, "calm": -5.0},
    "user_shares_bad_news":     {"sad": 8.0, "fear": 3.0, "calm": -5.0},
    "user_shares_good_news":    {"happy": 6.0, "excited": 5.0, "calm": -2.0},
    "anniversary":              {"happy": 8.0, "excited": 7.0, "lonely": -8.0},
    "make_up_after_conflict":   {"happy": 10.0, "calm": 10.0, "sad": -8.0, "angry": -8.0},
    "long_no_contact":          {"lonely": 6.0, "sad": 4.0, "happy": -4.0, "calm": -3.0},
    "user_sleeps":              {"tired": -10.0, "calm": 5.0},
    "hard_day":                 {"tired": 8.0, "calm": -5.0},
    "user_needs_comfort":       {"sad": 5.0, "calm": -3.0, "happy": -2.0},
    "exciting_event":           {"excited": 12.0, "happy": 6.0, "calm": -8.0},
    "peaceful_moment":          {"calm": 12.0, "happy": 4.0, "excited": -5.0},
}

# 情绪转换触发条件：当前情绪达到阈值时自动转换
EMOTION_TRANSITIONS: dict[str, dict[str, float]] = {
    "happy":  {"excited": 40.0, "calm": -30.0},       # happy>40 促进excited，抑制calm
    "sad":    {"lonely": 30.0, "angry": 20.0, "happy": -20.0},
    "fear":   {"sad": 15.0, "calm": -20.0},
    "angry":  {"jealous": 25.0, "happy": -25.0, "calm": -30.0},
    "jealous": {"sad": 10.0, "angry": 30.0, "calm": -15.0},
    "tired":  {"calm": 10.0, "happy": -10.0, "excited": -15.0},
    "excited": {"happy": 20.0},  # excited 促进 happy
    "lonely": {"sad": 15.0, "calm": -20.0},
    "calm":   {"happy": 15.0, "angry": -20.0},
}


class EmotionEngine:
    """
    情绪引擎

    职责：
    1. 管理9个情绪维度的计算
    2. 处理情绪混合规则
    3. 执行情绪衰减
    4. 管理五阶段持久性模型
    5. 检测和触发情绪转换
    """

    def __init__(self, state: EmotionState | None = None):
        """
        初始化情绪引擎

        Args:
            state: 初始情绪状态，为空则使用默认值
        """
        self.state = state or EmotionState()
        self._phase: EmotionPhase = EmotionPhase.RECOVERY
        self._phase_ticks: int = 0
        self._phase_durations = {
            EmotionPhase.BURST: 1,
            EmotionPhase.PEAK: 3,
            EmotionPhase.EASE: 8,
            EmotionPhase.OBSERVE: 12,
            EmotionPhase.RECOVERY: 20,
        }

    def trigger_emotion(self, event: str, intensity: float = 1.0) -> dict:
        """
        触发情绪事件

        Args:
            event: 事件名称
            intensity: 事件强度系数

        Returns:
            变更详情
        """
        if event not in EMOTION_TRIGGERS:
            return {"error": f"未知情绪事件: {event}"}

        effects = EMOTION_TRIGGERS[event]
        changes = {}
        previous = self.state.to_dict()

        # 1. 应用直接效果
        for dim, delta in effects.items():
            if delta != 0:
                scaled = delta * intensity
                current = getattr(self.state, dim)
                setattr(self.state, dim, current + scaled)
                changes[dim] = round(scaled, 1)

        # 2. 应用情绪转换（高值情绪对其他情绪的影响）
        for dim, transitions in EMOTION_TRANSITIONS.items():
            current_val = getattr(self.state, dim)
            for target, threshold in transitions.items():
                if abs(current_val) > abs(threshold):
                    effect = (current_val - abs(threshold)) * 0.1
                    if threshold > 0:
                        setattr(self.state, target, getattr(self.state, target) + effect)
                    else:
                        setattr(self.state, target, getattr(self.state, target) + effect)

        # 3. 裁剪并设置持久性阶段
        self.state.clamp_all()
        self._enter_phase(EmotionPhase.BURST)

        return {
            "event": event,
            "intensity": intensity,
            "changes": changes,
            "previous": previous,
            "current": self.state.to_dict(),
            "phase": self._phase.value,
        }

    def _enter_phase(self, phase: EmotionPhase):
        """进入情绪持久性阶段"""
        self._phase = phase
        self._phase_ticks = 0

    def tick(self) -> dict:
        """
        每tick执行：情绪衰减 + 持久性阶段推进

        Returns:
            当前情绪状态摘要
        """
        self._phase_ticks += 1

        # 根据当前阶段决定衰减速率
        phase_multipliers = {
            EmotionPhase.BURST: 0.0,    # 爆发阶段不衰减
            EmotionPhase.PEAK: 0.0,     # 高峰阶段不衰减
            EmotionPhase.EASE: 0.5,     # 缓和阶段衰减50%
            EmotionPhase.OBSERVE: 0.8,  # 观察阶段衰减80%
            EmotionPhase.RECOVERY: 1.0, # 恢复阶段正常衰减
        }
        multiplier = phase_multipliers.get(self._phase, 1.0)

        decays = {}
        for dim, rate in self.state.DECAY_RATES.items():
            current = getattr(self.state, dim)
            # 情绪衰减总是向中性/正向移动
            if dim in ("tired", "sad", "angry", "jealous", "fear", "lonely"):
                # 负面情绪向0衰减
                effective_rate = rate * multiplier
                new_val = max(0.0, current - effective_rate)
            else:
                # 正面/中性情绪向基线衰减
                baselines = {"happy": 60, "excited": 20, "calm": 70}
                baseline = baselines.get(dim, 50)
                effective_rate = rate * multiplier
                if current > baseline:
                    new_val = max(baseline, current - effective_rate)
                else:
                    new_val = min(baseline, current + effective_rate)
            setattr(self.state, dim, new_val)
            decays[dim] = round(new_val - current, 1)

        self.state.clamp_all()

        # 检查是否可以推进阶段
        duration = self._phase_durations[self._phase]
        if self._phase_ticks >= duration:
            next_phases = {
                EmotionPhase.BURST: EmotionPhase.PEAK,
                EmotionPhase.PEAK: EmotionPhase.EASE,
                EmotionPhase.EASE: EmotionPhase.OBSERVE,
                EmotionPhase.OBSERVE: EmotionPhase.RECOVERY,
                EmotionPhase.RECOVERY: EmotionPhase.RECOVERY,  # 保持在恢复阶段
            }
            self._enter_phase(next_phases[self._phase])

        return {
            "phase": self._phase.value,
            "phase_ticks": self._phase_ticks,
            "decays": {k: round(v, 1) for k, v in decays.items()},
            "state": self.state.to_dict(),
        }

    def get_emotional_tone(self) -> dict:
        """
        获取当前情绪基调，用于影响语言风格

        Returns:
            包含情感基调各个维度的字典
        """
        emo = self.state
        dominant_name, dominant_val = emo.dominant_emotion
        is_negative = emo.is_negative_dominant

        # 计算情感基调对回复的影响
        verbosity = "normal"
        if emo.excited > 60 or emo.happy > 70:
            verbosity = "verbose"
        elif emo.tired > 60 or emo.sad > 50:
            verbosity = "brief"

        warmth = "neutral"
        if emo.happy > 50 and emo.calm > 50:
            warmth = "warm"
        elif emo.angry > 30 or emo.sad > 40:
            warmth = "cool"

        initiative = "moderate"
        if emo.excited > 50 or emo.happy > 65:
            initiative = "high"
        elif emo.tired > 50 or emo.sad > 40:
            initiative = "low"

        return {
            "dominant_emotion": dominant_name,
            "dominant_value": dominant_val,
            "is_negative": is_negative,
            "verbosity": verbosity,
            "warmth": warmth,
            "initiative": initiative,
            "phase": self._phase.value,
        }
