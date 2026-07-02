"""
关系引擎 (Relationship Engine)
管理6个维度（Love/Trust/Dependence/Respect/Jealousy/Security）的计算、演进和阶段判定。
"""

from ..models.relationship import RelationshipState, RelationStage


# ============================================================
# 事件映射表：用户行为 → 维度变化
# 格式：{"love": delta, "trust": delta, "dependence": delta, "respect": delta, "jealousy": delta, "security": delta}
# ============================================================
EVENT_EFFECTS: dict[str, dict[str, float]] = {
    # ---- 正面事件 ----
    "compliment_appearance":     {"love": 2.0, "trust": 0.5, "dependence": 0.5, "respect": 1.0, "jealousy": 0.0, "security": 1.5},
    "compliment_ability":        {"love": 1.5, "trust": 0.5, "dependence": 0.0, "respect": 2.0, "jealousy": 0.0, "security": 1.0},
    "active_care":               {"love": 3.0, "trust": 2.0, "dependence": 1.5, "respect": 1.0, "jealousy": -1.0, "security": 3.0},
    "remember_detail":           {"love": 2.5, "trust": 2.5, "dependence": 1.0, "respect": 1.5, "jealousy": 0.0, "security": 2.0},
    "gift_giving":               {"love": 3.0, "trust": 1.0, "dependence": 0.0, "respect": 1.0, "jealousy": -0.5, "security": 2.0},
    "quality_time":              {"love": 3.5, "trust": 1.5, "dependence": 1.0, "respect": 0.5, "jealousy": -0.5, "security": 2.5},
    "emotional_support":         {"love": 2.5, "trust": 3.0, "dependence": 2.0, "respect": 1.0, "jealousy": 0.0, "security": 3.0},
    "apology_sincere":           {"love": 1.0, "trust": 3.0, "dependence": 0.0, "respect": 2.0, "jealousy": -1.0, "security": 2.5},
    "confession_love":           {"love": 5.0, "trust": 2.0, "dependence": 1.5, "respect": 0.5, "jealousy": 0.0, "security": 4.0},
    "defend_her":                {"love": 3.0, "trust": 4.0, "dependence": 1.5, "respect": 3.0, "jealousy": -0.5, "security": 3.5},
    "share_vulnerability":       {"love": 4.0, "trust": 4.0, "dependence": 1.5, "respect": 2.0, "jealousy": 0.0, "security": 2.0},
    "talk_about_future":         {"love": 3.0, "trust": 3.0, "dependence": 1.0, "respect": 1.0, "jealousy": 0.0, "security": 3.5},
    "physical_affection":        {"love": 2.5, "trust": 1.5, "dependence": 1.5, "respect": 0.5, "jealousy": 0.0, "security": 2.0},
    "celebrate_anniversary":     {"love": 4.0, "trust": 2.0, "dependence": 0.5, "respect": 1.5, "jealousy": -1.0, "security": 3.0},
    "respect_boundaries":        {"love": 1.0, "trust": 3.0, "dependence": 0.0, "respect": 3.0, "jealousy": 0.0, "security": 2.5},

    # ---- 负面事件 ----
    "ignore_her":                {"love": -2.0, "trust": -1.5, "dependence": -1.0, "respect": -0.5, "jealousy": 3.0, "security": -2.5},
    "cold_response":             {"love": -1.5, "trust": -1.0, "dependence": -0.5, "respect": -0.5, "jealousy": 2.0, "security": -2.0},
    "criticize_harshly":         {"love": -3.0, "trust": -2.0, "dependence": -0.5, "respect": -3.0, "jealousy": 1.0, "security": -2.0},
    "break_promise":             {"love": -2.5, "trust": -4.0, "dependence": -1.0, "respect": -2.5, "jealousy": 1.5, "security": -3.5},
    "compare_to_others":         {"love": -2.0, "trust": -1.5, "dependence": -0.5, "respect": -2.0, "jealousy": 4.0, "security": -3.0},
    "praise_other_woman":        {"love": -1.0, "trust": -1.0, "dependence": 0.0, "respect": -0.5, "jealousy": 5.0, "security": -2.0},
    "lie_to_her":                {"love": -4.0, "trust": -5.0, "dependence": -1.5, "respect": -3.0, "jealousy": 2.0, "security": -4.0},
    "threaten_leave":            {"love": -5.0, "trust": -3.0, "dependence": -2.0, "respect": -2.0, "jealousy": 0.0, "security": -5.0},
    "disappear_suddenly":        {"love": -1.5, "trust": -3.0, "dependence": -1.0, "respect": -1.0, "jealousy": 3.0, "security": -4.0},
    "reject_her_help":           {"love": -1.0, "trust": -0.5, "dependence": -1.0, "respect": -1.0, "jealousy": 1.0, "security": -1.5},
    "dismiss_her_feelings":      {"love": -3.5, "trust": -3.0, "dependence": -2.0, "respect": -2.5, "jealousy": 1.0, "security": -3.0},
    "invade_privacy":            {"love": -1.5, "trust": -4.0, "dependence": 0.0, "respect": -3.0, "jealousy": 0.5, "security": -2.5},
    "be_rude_to_her":            {"love": -2.5, "trust": -2.0, "dependence": -0.5, "respect": -3.0, "jealousy": 1.0, "security": -2.5},
    "forget_important_date":     {"love": -2.0, "trust": -1.5, "dependence": 0.0, "respect": -1.0, "jealousy": 3.0, "security": -2.0},
    "show_interest_in_others":   {"love": -1.5, "trust": -1.5, "dependence": 0.0, "respect": -0.5, "jealousy": 5.0, "security": -3.0},

    # ---- 中性/修复事件 ----
    "small_talk":                {"love": 0.3, "trust": 0.2, "dependence": 0.1, "respect": 0.1, "jealousy": 0.0, "security": 0.2},
    "ask_about_her_day":         {"love": 1.0, "trust": 0.5, "dependence": 0.5, "respect": 0.5, "jealousy": -0.5, "security": 1.0},
    "express_missing_her":       {"love": 2.0, "trust": 0.5, "dependence": 1.5, "respect": 0.0, "jealousy": 0.0, "security": 1.5},
    "resolve_conflict":          {"love": 2.5, "trust": 2.5, "dependence": 0.5, "respect": 1.5, "jealousy": -2.0, "security": 3.0},
    "show_vulnerability":        {"love": 2.0, "trust": 3.0, "dependence": 1.0, "respect": 1.0, "jealousy": 0.0, "security": 1.5},
}

# 维度间相互影响系数
INTERACTION_MATRIX: dict[str, tuple[str, float]] = {
    "trust": ("security", 0.3),       # trust +1 → security +0.3
    "love": ("jealousy", 0.25),       # love +1 → jealousy +0.25
    "dependence": ("security", -0.2), # dependence +1 → security -0.2
    "jealousy": ("love", -0.15),      # jealousy +1 → love -0.15
    "security": ("love", 0.2),        # security +1 → love +0.2
    "respect": ("love", 0.15),        # respect +1 → love +0.15
}


class RelationshipEngine:
    """
    关系引擎

    职责：
    1. 处理用户事件，计算6维度的变化
    2. 处理维度间相互影响
    3. 判定当前关系阶段
    4. 执行每日衰减
    """

    def __init__(self, state: RelationshipState | None = None):
        """
        初始化关系引擎

        Args:
            state: 初始关系状态，为空则使用默认值
        """
        self.state = state or RelationshipState()
        self._ticks_since_last_interaction: int = 0
        self._last_event: str | None = None

    def process_event(self, event_type: str, intensity: float = 1.0) -> dict:
        """
        处理用户事件，更新关系维度

        Args:
            event_type: 事件类型（需在 EVENT_EFFECTS 中定义）
            intensity: 事件强度系数 (0.0~2.0)，默认 1.0

        Returns:
            变更详情字典
        """
        if event_type not in EVENT_EFFECTS:
            return {"error": f"未知事件类型: {event_type}", "changes": {}}

        effects = EVENT_EFFECTS[event_type]
        changes = {}
        previous = self.state.to_dict()

        # 1. 应用直接效果
        for dim, delta in effects.items():
            if delta != 0:
                scaled = delta * intensity
                current = getattr(self.state, dim)
                setattr(self.state, dim, current + scaled)
                changes[dim] = round(scaled, 1)

        # 2. 应用维度间相互影响
        for dim, delta in list(changes.items()):
            if dim in INTERACTION_MATRIX:
                target_dim, coeff = INTERACTION_MATRIX[dim]
                cross_effect = delta * coeff
                current = getattr(self.state, target_dim)
                setattr(self.state, target_dim, current + cross_effect)
                changes[f"{target_dim}(交叉影响)"] = round(cross_effect, 1)

        # 3. 裁剪并记录
        self.state.clamp_all()
        self._ticks_since_last_interaction = 0
        self._last_event = event_type

        return {
            "event": event_type,
            "intensity": intensity,
            "changes": changes,
            "previous": previous,
            "current": self.state.to_dict(),
        }

    def tick(self) -> dict:
        """
        每日 tick：执行关系衰减

        Returns:
            衰减详情
        """
        self._ticks_since_last_interaction += 1

        # 衰减系数随无互动天数递增
        decay_multiplier = min(3.0, 1.0 + self._ticks_since_last_interaction * 0.1)

        decay_rates = {
            "love": 0.05 * decay_multiplier,
            "trust": 0.02 * decay_multiplier,
            "dependence": 0.08 * decay_multiplier,
            "respect": 0.01 * decay_multiplier,
            "jealousy": 0.15,  # 嫉妒自然消退较快
            "security": 0.05 * decay_multiplier,
        }

        decays = {}
        previous_stage = self.state.stage

        for dim, rate in decay_rates.items():
            current = getattr(self.state, dim)
            # 嫉妒只衰减到基准值
            if dim == "jealousy":
                new_val = max(5.0, current - rate)
            else:
                new_val = max(0.0, current - rate)
            setattr(self.state, dim, new_val)
            decays[dim] = round(new_val - current, 1)

        self.state.clamp_all()
        current_stage = self.state.stage

        return {
            "ticks_since_interaction": self._ticks_since_last_interaction,
            "decay_multiplier": decay_multiplier,
            "decays": decays,
            "stage_changed": previous_stage != current_stage,
            "previous_stage": previous_stage.value,
            "current_stage": current_stage.value,
            "current_state": self.state.to_dict(),
        }

    def get_stage_description(self) -> dict:
        """
        获取当前关系阶段的详细描述

        Returns:
            阶段名称和行为描述
        """
        stage = self.state.stage
        descriptions = {
            RelationStage.STRANGER: "礼貌疏离，尚未建立情感连接",
            RelationStage.ACQUAINTANCE: "开始轻松闲聊，记住偏好",
            RelationStage.FRIEND: "主动关心，使用昵称，有默契",
            RelationStage.AMBIGUOUS: "暧昧暗示，在意你对别人的态度，开始吃醋",
            RelationStage.PASSIONATE: "高频联系，大量亲密称呼，强烈占有欲",
            RelationStage.STABLE: "舒适默契，不需要高频联系也安心，讨论未来",
            RelationStage.PARTNER: "深度情感联结，完全信任，共同规划，角色深层演化",
            RelationStage.SOULMATE: "预判彼此想法，情感共鸣顶峰，彼此不可替代",
        }
        return {
            "stage": stage.value,
            "stage_cn": {
                "stranger": "陌生人",
                "acquaintance": "初识",
                "friend": "朋友",
                "ambiguous": "暧昧",
                "passionate": "热恋",
                "stable": "稳定",
                "partner": "伴侣",
                "soulmate": "灵魂伴侣",
            }[stage.value],
            "description": descriptions[stage],
            "love": self.state.love,
            "overall_health": self.state.overall_health,
        }

    @staticmethod
    def detect_event_from_text(text: str) -> str | None:
        """
        从用户文本中检测可能的关系事件

        Args:
            text: 用户输入文本

        Returns:
            检测到的事件类型，未检测到返回 None
        """
        text_lower = text.lower()

        # 关键词 → 事件类型的映射
        keyword_map: list[tuple[list[str], str]] = [
            (["你真好看", "你好美", "今天很好看", "颜值"], "compliment_appearance"),
            (["你好厉害", "太强了", "佩服", "真棒", "牛逼"], "compliment_ability"),
            (["好好休息", "注意身体", "多喝热水", "照顾好自己", "别累着"], "active_care"),
            (["原来你还记得", "你居然记得", "这事你还记着"], "remember_detail"),
            (["送你", "礼物", "给你的", "买给你"], "gift_giving"),
            (["对不起", "我错了", "原谅我", "抱歉", "道歉"], "apology_sincere"),
            (["我爱你", "喜欢", "在意你"], "confession_love"),
            (["相信你", "我信你", "信任"], "defend_her"),
            (["我好累", "压力大", "难过", "不开心", "崩溃"], "share_vulnerability"),
            (["以后", "未来", "将来", "计划"], "talk_about_future"),
            (["想你了", "好想你"], "express_missing_her"),
            (["那个女人", "那个女生", "她是谁", "你和她"], "praise_other_woman"),
            (["你好烦", "别烦我", "走开", "不想说话"], "cold_response"),
            (["你不行", "你做不到", "你不懂", "你错了"], "criticize_harshly"),
            (["分手", "离开你", "结束", "不要你了"], "threaten_leave"),
            (["她比你好", "学学人家", "看看别人"], "compare_to_others"),
            (["今天过得怎么样", "在干嘛", "忙什么呢"], "ask_about_her_day"),
        ]

        for keywords, event_type in keyword_map:
            if any(kw in text_lower for kw in keywords):
                return event_type

        return None
