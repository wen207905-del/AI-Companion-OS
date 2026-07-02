"""
场景分类器 — Phase 2 完整实现

根据时间/天气/情绪组合判定场景类型，并给出行为倾向。
场景如：late_night_rainy_lonely、sunny_morning_happy 等。
"""

import re
from ..config import PHASE2_SCENE_OVERRIDES, PHASE2_ACTION_TYPES


class SceneClassifier:
    """场景分类器 — 组合时间+天气+情绪 → 场景键 → 行为倾向。

    场景键格式: {time_period}_{weather_type}_{emotion_label}
    例: late_night_rainy_lonely, sunny_morning_happy
    """

    SCENE_TEMPLATES = {
        # 寂寞悲伤类
        "late_night_rainy_lonely":  {"action_bias": {"SEND_MESSAGE": 0.7, "WRITE_DIARY": 0.3}},
        "late_night_rainy_sad":    {"action_bias": {"SEND_MESSAGE": 0.5, "WRITE_DIARY": 0.5}},
        "night_rainy_lonely":      {"action_bias": {"SEND_MESSAGE": 0.6, "SEND_IMAGE": 0.2, "WRITE_DIARY": 0.2}},
        "evening_rainy_lonely":    {"action_bias": {"SEND_MESSAGE": 0.5, "WRITE_DIARY": 0.5}},
        "night_stormy_lonely":     {"action_bias": {"SEND_MESSAGE": 0.3, "SEND_IMAGE": 0.4, "WRITE_DIARY": 0.3}},
        # 开心类
        "sunny_morning_happy":     {"action_bias": {"SEND_MESSAGE": 0.6, "GROUP_INTERACTION": 0.4}},
        "sunny_noon_happy":        {"action_bias": {"SEND_MESSAGE": 0.5, "GROUP_INTERACTION": 0.5}},
        "cloudy_afternoon_calm":   {"action_bias": {"SEND_MESSAGE": 0.7, "WRITE_DIARY": 0.3}},
        # 安静类
        "night_overcast_calm":     {"action_bias": {"WRITE_DIARY": 0.6, "SEND_MESSAGE": 0.4}},
        "late_night_snowy_calm":   {"action_bias": {"WRITE_DIARY": 0.7, "SEND_MESSAGE": 0.3}},
        # 愤怒/嫉妒类
        "evening_stormy_angry":    {"action_bias": {"WRITE_DIARY": 0.6, "RELATIONSHIP_EVENT": 0.4}},
        "night_heavy_rain_anxious":{"action_bias": {"SEND_MESSAGE": 0.8, "WRITE_DIARY": 0.2}},
        # 困倦类
        "morning_rainy_sleepy":    {"action_bias": {"SILENCE": 0.7, "WRITE_DIARY": 0.3}},
    }

    def __init__(self):
        pass

    def classify(self, world_state, emotion_state: dict = None,
                 mood_bias: str = "") -> dict:
        """分类当前场景并返回行为倾向。

        Args:
            world_state: WorldState 对象（含 time_period, weather, environment）
            emotion_state: 情绪状态（可选）
            mood_bias: 附加情绪偏置（来自 MoodPressureSystem / 缺席系统）

        Returns:
            {
                "scene_key":    "late_night_rainy_lonely",
                "scene_label":  "深夜雨夜-孤独",
                "action_bias":  {action_type: probability_weight, ...},
                "dominant_mood": "lonely",
                "atmosphere":   "melancholic",
                "match_type":   "exact" | "fallback",
            }
        """
        time_period = getattr(world_state, "time_period", "morning")
        weather_type = world_state.weather.type if hasattr(world_state, "weather") else "sunny"
        atmosphere = world_state.environment.atmosphere if hasattr(world_state, "environment") else "peaceful"

        # 推断主情绪标签
        emotion_label = self._infer_emotion_label(emotion_state or {}, mood_bias)

        # 构建场景键
        scene_key = f"{time_period}_{weather_type}_{emotion_label}"

        # 匹配模板
        if scene_key in self.SCENE_TEMPLATES:
            template = self.SCENE_TEMPLATES[scene_key]
            return {
                "scene_key": scene_key,
                "scene_label": f"{self._label_time(time_period)}{self._label_weather(weather_type)}-{self._label_emotion(emotion_label)}",
                "action_bias": template["action_bias"],
                "dominant_mood": emotion_label,
                "atmosphere": atmosphere,
                "match_type": "exact",
            }

        # 模糊匹配：尝试忽略天气的精确匹配
        fallback_key = f"{time_period}_*_{emotion_label}"
        matched = self._fuzzy_match(fallback_key)
        if matched:
            return {
                "scene_key": scene_key,
                "scene_label": f"{self._label_time(time_period)}-{self._label_emotion(emotion_label)}",
                "action_bias": matched["action_bias"],
                "dominant_mood": emotion_label,
                "atmosphere": atmosphere,
                "match_type": "weather_fallback",
            }

        # 最终回退
        return {
            "scene_key": scene_key,
            "scene_label": "默认场景",
            "action_bias": {"SEND_MESSAGE": 0.7, "SILENCE": 0.3},
            "dominant_mood": "neutral",
            "atmosphere": atmosphere,
            "match_type": "default_fallback",
        }

    def _infer_emotion_label(self, emotion_state: dict, mood_bias: str) -> str:
        """从情绪状态推断标准化情绪标签。"""
        # 优先用 mood_bias
        if mood_bias in ("lonely", "sad", "angry", "anxious", "sleepy", "jealous"):
            return mood_bias
        if mood_bias == "miss_you":
            return "lonely"

        if not emotion_state:
            return "neutral"

        # 找最高值情绪
        best = ("neutral", 0)
        for emo_key in ("lonely", "sad", "angry", "happy", "calm", "anxious", "sleepy", "jealous"):
            val = emotion_state.get(emo_key, 0)
            if isinstance(val, (int, float)) and val > best[1]:
                best = (emo_key, val)

        if best[1] < 0.2:
            return "neutral"
        return best[0]

    def _fuzzy_match(self, pattern: str) -> dict:
        """模糊匹配场景模板。"""
        for key, template in self.SCENE_TEMPLATES.items():
            if self._match_pattern(pattern, key):
                return template
        return None

    def _match_pattern(self, pattern: str, key: str) -> bool:
        """将带 * 通配符的 pattern 与 key 匹配。"""
        pat_parts = pattern.split("_")
        key_parts = key.split("_")
        if len(pat_parts) != len(key_parts):
            return False
        for pp, kp in zip(pat_parts, key_parts):
            if pp != "*" and pp != kp:
                return False
        return True

    # 标签翻译
    def _label_time(self, tp: str) -> str:
        return {"early_morning":"清晨","morning":"上午","noon":"正午","afternoon":"下午",
                "evening":"傍晚","night":"夜晚","late_night":"深夜"}.get(tp, tp)

    def _label_weather(self, wt: str) -> str:
        return {"sunny":"晴天","rainy":"雨天","heavy_rain":"暴雨","stormy":"暴风雨",
                "snowy":"雪天","overcast":"阴天","foggy":"雾天","cloudy":"多云"}.get(wt, wt)

    def _label_emotion(self, el: str) -> str:
        return {"happy":"快乐","lonely":"孤独","sad":"悲伤","angry":"愤怒",
                "anxious":"焦虑","sleepy":"困倦","jealous":"嫉妒",
                "calm":"平静","neutral":"中性"}.get(el, el)

    def get_action_tendency(self, classification: dict) -> dict:
        """从场景分类结果中提取行为倾向。"""
        return classification.get("action_bias", {"SEND_MESSAGE": 0.7})

    def get_scene_override(self, scene_key: str) -> dict:
        """获取场景级 Central Brain 覆写规则。"""
        return PHASE2_SCENE_OVERRIDES.get(scene_key, {})
