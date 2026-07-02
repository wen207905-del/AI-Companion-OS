"""
事件分析器：对事件进行语义分析，输出各引擎的数值变化建议。事件是唯一数值变化入口。
"""
import json
import time
from dataclasses import dataclass, field
from typing import Optional

from config import USER_NAME


@dataclass
class AnalysisResult:
    event_id: str
    primary_target: str           # 主要影响角色
    effects: list = field(default_factory=list)  # [{target, engine, field, delta, reason}]
    memory_snapshot: str = ""     # 供记忆系统使用的文本摘要
    timeline_entry: Optional[dict] = None  # 里程碑事件

class EventAnalyzer:
    """事件分析器：基于规则 + 上下文的事件语义分析"""

    # 事件权重映射
    WEIGHT_MAP = {
        "conversation": 1,
        "long_conversation": 3,
        "accompany": 5,
        "gift": 30,
        "anniversary": 20,
        "first_confession": 100,
        "first_date": 80,
        "trip": 50,
        "argument": -15,
        "neglect": -8,
        "jealousy_trigger": 10,
        "time_passive": 0,
        "system": 0,
    }

    # 关键词→关系维度影响映射
    KEYWORD_EFFECTS = {
        "爱你": [("love", 2), ("attachment", 1)],
        "想你": [("love", 2), ("attachment", 2)],
        "对不起": [("trust", -1), ("security", -2)],
        "辛苦了": [("respect", 2), ("love", 1)],
        "晚安": [("attachment", 1), ("security", 1)],
        "真好看": [("love", 1), ("intimacy_emotional", 1)],
        "过来": [("attachment", 1)],
        "陪我": [("attachment", 3), ("love", 1)],
        "笨蛋": [("love", 1)],
        "乖": [("attachment", 2), ("respect", 1)],
        "别走": [("attachment", 3), ("security", -2)],
        "不在": [("security", -1)],
        "讨厌": [("love", -2), ("trust", -1)],
        "烦": [("respect", -1), ("love", -1)],
        "不爱你": [("love", -3), ("trust", -1)],
        "不喜欢": [("love", -2)],
    }

    # 情绪关键词
    EMOTION_KEYWORDS = {
        "开心": ("happy", 10), "高兴": ("happy", 10), "哈哈": ("happy", 8),
        "难过": ("sad", 15), "哭": ("sad", 20), "伤心": ("sad", 15),
        "生气": ("angry", 20), "紧张": ("stressed", 15), "累": ("tired", 15),
        "害怕": ("fearful", 15), "担心": ("suspicious", 10),
        "害羞": ("shy", 15), "不好意思": ("embarrassed", 10),
        "兴奋": ("excited", 15), "激动": ("excited", 12),
        "孤单": ("lonely", 20), "寂寞": ("lonely", 15),
    }

    # 每轮私聊/群聊基础增长（不依赖关键词）
    CONVERSATION_BASELINE = [
        ("love", 1.2),
        ("attachment", 0.8),
        ("intimacy_emotional", 0.5),
        ("trust", 0.4),
    ]

    # 亲密/身体向对话额外增长
    INTIMATE_KEYWORD_EFFECTS = [
        ("抱", [("attachment", 1.5), ("intimacy_physical", 1.2), ("love", 0.8)]),
        ("亲", [("intimacy_physical", 1.5), ("love", 1.0), ("intimacy_emotional", 0.8)]),
        ("吻", [("intimacy_physical", 1.5), ("love", 1.0)]),
        ("摸", [("intimacy_physical", 1.2), ("attachment", 0.8)]),
        ("胸", [("intimacy_physical", 1.8), ("love", 0.6)]),
        ("脱", [("intimacy_physical", 2.0), ("attachment", 1.0)]),
        ("吮", [("intimacy_physical", 2.0), ("love", 0.8)]),
        ("吸", [("intimacy_physical", 1.8), ("love", 0.6)]),
        ("宝贝", [("love", 1.5), ("attachment", 1.0)]),
        ("爱你", [("love", 2.5), ("attachment", 1.5)]),
        ("想你", [("love", 2.0), ("attachment", 1.8)]),
        ("回家", [("attachment", 1.2), ("security", 0.8)]),
        ("咬", [("intimacy_physical", 1.5), ("love", 0.8)]),
    ]

    def _targets(self, event) -> list[str]:
        """私聊返回单个角色；群聊返回所有非 user 成员"""
        if len(event.participants) > 2:
            return [p for p in event.participants if p != "user"]
        if len(event.participants) > 1:
            return [event.participants[1]]
        return [event.participants[0]]

    def _keyword_in_text(self, text: str, keyword: str) -> bool:
        if keyword not in text:
            return False
        if keyword in ("爱你", "想你", "喜欢") and f"不{keyword}" in text:
            return False
        return True

    def analyze(self, event) -> AnalysisResult:
        """分析一个事件，返回对各引擎的影响"""
        targets = self._targets(event)
        primary = targets[0]
        result = AnalysisResult(
            event_id=event.event_id,
            primary_target=primary,
            effects=[],
            memory_snapshot=""
        )

        base_weight = self.WEIGHT_MAP.get(event.event_type, 1)
        effective_weight = max(1, base_weight + event.weight - 1)
        group_scale = 0.5 if len(targets) > 1 else 1.0

        if event.raw_input:
            text = event.raw_input.lower()
            for keyword, kw_effects in self.KEYWORD_EFFECTS.items():
                if self._keyword_in_text(text, keyword):
                    for target in targets:
                        for field, delta in kw_effects:
                            result.effects.append({
                                "target": target,
                                "engine": "relationship",
                                "field": field,
                                "delta": delta * effective_weight * group_scale,
                                "reason": f"关键词匹配: '{keyword}'",
                            })

            for keyword, (emotion_field, delta) in self.EMOTION_KEYWORDS.items():
                if keyword in text:
                    for target in targets:
                        result.effects.append({
                            "target": target,
                            "engine": "emotion",
                            "field": emotion_field,
                            "delta": delta * (1 + effective_weight * 0.2) * group_scale,
                            "reason": f"情绪关键词: '{keyword}'",
                        })

            display_name = event.metadata.get("display_name", primary)
            group_name = event.metadata.get("group_name", "群聊")
            ts = time.strftime(
                '%Y-%m-%d %H:%M',
                time.localtime(event.timestamp),
            ) if event.timestamp else ""
            if len(targets) > 1:
                result.memory_snapshot = (
                    f"[{ts}] {USER_NAME}在群聊「{group_name}」说：「{event.raw_input[:60]}」"
                )
            else:
                result.memory_snapshot = (
                    f"[{ts}] {USER_NAME}对{display_name}说：「{event.raw_input[:50]}」"
                )

        # 同伴事件额外效果
        if event.event_type == "accompany":
            result.effects.append({
                "target": primary, "engine": "relationship",
                "field": "attachment", "delta": 4 * effective_weight,
                "reason": "陪伴事件"
            })
            result.effects.append({
                "target": primary, "engine": "emotion",
                "field": "happy", "delta": 10,
                "reason": "陪伴带来的愉悦"
            })

        # 嫉妒连锁
        if event.event_type == "jealousy_trigger":
            for char_id in event.metadata.get("affected_characters", []):
                result.effects.append({
                    "target": char_id, "engine": "relationship",
                    "field": "jealousy", "delta": 15,
                    "reason": "跨角色嫉妒连锁"
                })
                result.effects.append({
                    "target": char_id, "engine": "relationship",
                    "field": "security", "delta": -8,
                    "reason": "安全感下降"
                })

        # 每轮对话基础增长 + 亲密向加成
        if event.event_type == "conversation" and event.raw_input:
            text = event.raw_input
            for target in targets:
                for field, delta in self.CONVERSATION_BASELINE:
                    result.effects.append({
                        "target": target,
                        "engine": "relationship",
                        "field": field,
                        "delta": delta * group_scale,
                        "reason": "对话基础增长",
                    })
                result.effects.append({
                    "target": target,
                    "engine": "emotion",
                    "field": "happy",
                    "delta": 3 * group_scale,
                    "reason": "对话互动",
                })
                for keyword, kw_effects in self.INTIMATE_KEYWORD_EFFECTS:
                    if keyword in text:
                        for field, delta in kw_effects:
                            result.effects.append({
                                "target": target,
                                "engine": "relationship",
                                "field": field,
                                "delta": delta * group_scale,
                                "reason": f"亲密互动: '{keyword}'",
                            })
                        result.effects.append({
                            "target": target,
                            "engine": "emotion",
                            "field": "excited",
                            "delta": 5 * group_scale,
                            "reason": f"亲密互动: '{keyword}'",
                        })
                        result.effects.append({
                            "target": target,
                            "engine": "emotion",
                            "field": "shy",
                            "delta": 4 * group_scale,
                            "reason": f"亲密互动: '{keyword}'",
                        })

        return result


event_analyzer = EventAnalyzer()
