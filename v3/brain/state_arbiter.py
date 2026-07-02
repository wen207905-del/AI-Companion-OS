"""
状态仲裁器 — Phase 2 完整实现

冲突检测 + 优先级规则引擎。
当多个情绪/关系信号冲突时，按优先级规则融合为统一状态。
"""


class StateArbiter:
    """状态仲裁器 — 解决冲突，优先级融合。

    输入多个情绪/关系信号，按以下规则仲裁：
    - 取最高分情绪为主情绪
    - 困倦 > 80 强制覆写
    - 嫉妒 > 70 限制行为
    - 孤独+依恋双高 = 增强主动行为
    """

    # 情绪优先级权重（数字越大越优先）
    EMOTION_PRIORITIES = {
        "sleepy":  100,
        "angry":   90,
        "jealous": 85,
        "anxious": 80,
        "sad":     70,
        "lonely":  60,
        "happy":   50,
        "calm":    30,
        "neutral": 0,
    }

    def __init__(self):
        pass

    def resolve(self, states: dict, personality: dict = None) -> dict:
        """冲突检测与仲裁。

        Args:
            states: {"emotion": {...}, "relationship": {...}, "mood_pressure": {...}, ...}
            personality: 性格配置（可选）

        Returns:
            {
                "primary_emotion":   str,         # 主情绪
                "merged_emotion":    dict,        # 融合后的情绪值
                "override_silence":  bool,        # 是否强制沉默
                "override_emotional":bool,        # 是否强制情绪表达
                "boost_proactive":   bool,        # 是否增强主动行为
                "tone":             str,          # 语调
                "rule_applied":     str,          # 应用的规则
                "conflicts":        list,         # 冲突列表
            }
        """
        emotion = states.get("emotion", {})
        relationship = states.get("relationship", {})
        personality = personality or {}

        # 检测冲突
        conflicts = self._detect_conflicts(emotion, relationship)

        # 规则 1: 困倦 > 80 → 强制沉默
        sleepy = emotion.get("sleepy", 0)
        if sleepy > 80:
            return self._apply_sleepy_rule(emotion, conflicts)

        # 规则 2: 嫉妒 > 70 → 限制为仅情绪消息
        jealous = emotion.get("jealous", 0)
        if jealous > 70:
            return self._apply_jealous_rule(emotion, relationship, conflicts)

        # 规则 3: 孤独 + 依恋双高 → 增强主动行为
        lonely = emotion.get("lonely", 0)
        attachment = relationship.get("attachment", 0)
        if lonely > 60 and attachment > 60:
            return self._apply_lonely_love_rule(emotion, relationship, conflicts)

        # 默认：取优先级最高的情绪
        primary = self._pick_primary_emotion(emotion)
        return {
            "primary_emotion":    primary,
            "merged_emotion":     emotion,
            "override_silence":   False,
            "override_emotional": False,
            "boost_proactive":    False,
            "tone":              self._infer_tone(primary),
            "rule_applied":      "default_max",
            "conflicts":         conflicts,
        }

    def _detect_conflicts(self, emotion: dict, relationship: dict) -> list:
        """检测情绪与关系之间的冲突。

        Returns:
            冲突描述列表
        """
        conflicts = []
        happy = emotion.get("happy", 0)
        sad = emotion.get("sad", 0)
        love = relationship.get("love", 0)
        trust = relationship.get("trust", 0)

        # 开心但关系冷淡
        if happy > 50 and love < 30:
            conflicts.append("happy_vs_cold_relationship")
        # 悲伤但关系亲密
        if sad > 50 and love > 70:
            conflicts.append("sad_vs_warm_relationship")
        # 嫉妒但信任高
        if emotion.get("jealous", 0) > 50 and trust > 70:
            conflicts.append("jealous_vs_high_trust")

        return conflicts

    def _pick_primary_emotion(self, emotion: dict) -> str:
        """取优先级最高的情绪。"""
        best = ("neutral", 0, 0)  # (label, val, priority)
        for emo_key, val in emotion.items():
            if isinstance(val, (int, float)) and val > 0:
                priority = self.EMOTION_PRIORITIES.get(emo_key, 0)
                if priority > best[2] or (priority == best[2] and val > best[1]):
                    best = (emo_key, val, priority)
        return best[0]

    def _apply_sleepy_rule(self, emotion, conflicts):
        """困倦规则：级别最高 → 强制 silence。"""
        return {
            "primary_emotion":    "sleepy",
            "merged_emotion":     emotion,
            "override_silence":   True,
            "override_emotional": False,
            "boost_proactive":    False,
            "tone":              "drowsy",
            "rule_applied":      "sleepy>80_force_silence",
            "conflicts":         conflicts,
        }

    def _apply_jealous_rule(self, emotion, relationship, conflicts):
        """嫉妒规则：限制为仅情绪表达。"""
        return {
            "primary_emotion":    "jealous",
            "merged_emotion":     emotion,
            "override_silence":   False,
            "override_emotional": True,   # 仅允许情绪类消息
            "boost_proactive":    False,
            "tone":              "jealous",
            "rule_applied":      "jealous>70_emotional_only",
            "conflicts":         conflicts,
        }

    def _apply_lonely_love_rule(self, emotion, relationship, conflicts):
        """孤独+依恋双高规则：增强主动行为。"""
        return {
            "primary_emotion":    "lonely",
            "merged_emotion":     emotion,
            "override_silence":   False,
            "override_emotional": False,
            "boost_proactive":    True,    # 增强主动
            "tone":              "yearning",
            "rule_applied":      "lonely+attachment_high_boost",
            "conflicts":         conflicts,
        }

    def _infer_tone(self, primary: str) -> str:
        """从主情绪推断语调。"""
        tone_map = {
            "happy": "cheerful", "sad": "soft", "angry": "sharp",
            "lonely": "yearning", "jealous": "jealous", "anxious": "nervous",
            "sleepy": "drowsy", "calm": "gentle", "neutral": "neutral",
        }
        return tone_map.get(primary, "neutral")

    def get_allowed_actions(self, arbitrated_state: dict) -> dict:
        """获取仲裁后的允许/阻止行为列表。"""
        allowed = {"SEND_MESSAGE", "SEND_IMAGE", "WRITE_DIARY",
                   "UPDATE_MEMORY", "RELATIONSHIP_EVENT", "GROUP_INTERACTION"}
        blocked = set()

        if arbitrated_state.get("override_silence"):
            blocked = allowed.copy()
            allowed = {"SILENCE"}

        if arbitrated_state.get("override_emotional"):
            blocked.discard("SEND_MESSAGE")
            blocked.discard("WRITE_DIARY")
            blocked.add("GROUP_INTERACTION")
            blocked.add("SEND_IMAGE")

        return {
            "allowed_actions":  list(allowed),
            "blocked_actions":  list(blocked),
        }
