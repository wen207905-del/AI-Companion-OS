"""
User Message Perception — 用户消息感知

感知用户消息的内容、情感、长度、频率。
为 Autonomy Engine 和 Emotion Dynamics 提供用户侧输入。
"""

import re


class UserMessagePerception:
    """用户消息感知器。"""

    # 简单情感词映射（用于快速推断，不替代 LLM 分析）
    POSITIVE_WORDS = [
        "喜欢", "可爱", "想你了", "爱你", "好看", "开心", "谢谢", "好棒",
        "真不错", "太美了", "想", "想念", "亲亲", "抱抱", "温柔",
    ]
    NEGATIVE_WORDS = [
        "烦", "难过", "生气", "讨厌", "走开", "不想", "累了", "别烦我",
        "不开心", "失望", "绝望", "哭", "难受",
    ]

    def perceive(self, text: str) -> dict:
        """分析用户消息。

        Returns:
            {
                has_message: bool,
                text_preview: str,
                length: int,
                sentiment: str,       # positive / negative / neutral
                sentiment_intensity: float,  # 0-1
                is_question: bool,
                mentions_character: bool,
                contains_compliment: bool,
                contains_request: bool,
            }
        """
        text = text.strip()
        if not text:
            return {"has_message": True, "text_preview": "", "length": 0,
                    "sentiment": "neutral", "sentiment_intensity": 0}

        result = {
            "has_message": True,
            "text_preview": text[:200],
            "length": len(text),
            "is_question": text.endswith("?") or text.endswith("？") or "?" in text,
        }

        # 情感分析
        pos_count = sum(1 for w in self.POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in self.NEGATIVE_WORDS if w in text)

        total_match = pos_count + neg_count
        if total_match > 0:
            score = (pos_count - neg_count) / total_match
            if score > 0.2:
                result["sentiment"] = "positive"
                result["sentiment_intensity"] = min(1.0, abs(score))
            elif score < -0.2:
                result["sentiment"] = "negative"
                result["sentiment_intensity"] = min(1.0, abs(score))
            else:
                result["sentiment"] = "neutral"
                result["sentiment_intensity"] = 0.3
        else:
            result["sentiment"] = "neutral"
            result["sentiment_intensity"] = 0.1

        # 是否为夸奖
        result["contains_compliment"] = any(w in text for w in [
            "可爱", "好看", "好棒", "喜欢", "真不错", "太美了", "温柔", "厉害", "聪明"
        ])

        # 是否包含请求
        result["contains_request"] = any(w in text for w in [
            "帮我", "可以", "能不能", "可不可以", "好吗", "行吗", "行不行"
        ])

        return result
