"""
决策因子收集器 — Phase 2 完整实现

6 类因子收集器：Emotion / Relationship / World / User / Personality / Memory。
每类返回标准化 [0, 100] 分值，供 Autonomy Engine 的评分模型使用。

评分模型：
    score = emotion.lonely*0.25 + relationship.attachment*0.2
          + world.night_factor*0.15 + user.inactive_time*0.2
          + personality.initiative*0.1 + memory.triggers*0.1
"""

from ..config import PHASE2_SCORE_WEIGHTS


class DecisionFactors:
    """决策因子管理器 — 收集和标准化 6 类因子。

    所有因子输出均标准化到 [0, 100] 范围，由 Autonomy Engine
    按权重加权求和得综合评分。
    """

    def __init__(self):
        self.mood_pressure = None   # MoodPressureSystem 实例（外部注入）
        self.absence_system = None  # AbsenceSystem 实例（外部注入）

    # ── 主入口 ──

    def collect_all_factors(self, character_id: str, world_state,
                            emotion_state: dict, relationship_state: dict,
                            personality: dict, user_activity: dict,
                            memory_context: dict = None) -> dict:
        """汇总所有决策因子。

        Returns:
            {"emotion","relationship","world","user","personality","memory","raw_scores"}
        """
        emo = self._calc_emotion_factor(emotion_state)
        rel = self._calc_relationship_factor(relationship_state)
        wld = self._calc_world_factor(world_state)
        usr = self._calc_user_factor(user_activity)
        per = self._calc_personality_factor(personality)
        mem = self._calc_memory_factor(memory_context or {})

        raw_scores = {
            "emotion_lonely":              emo.get("lonely", 0),
            "relationship_attachment":     rel.get("attachment", 0),
            "world_night_factor":          wld.get("night_factor", 0),
            "user_inactive_time":          usr.get("inactive_time", 0),
            "personality_initiative":      per.get("initiative", 0),
            "memory_triggers":             mem.get("triggers", 0),
        }
        return {"emotion": emo, "relationship": rel, "world": wld,
                "user": usr, "personality": per, "memory": mem,
                "raw_scores": raw_scores}

    def compute_score(self, raw_scores: dict) -> float:
        """按权重计算综合评分 [0,100]."""
        weights = PHASE2_SCORE_WEIGHTS
        score = sum(raw_scores.get(k, 0) * w for k, w in weights.items())
        return min(score, 100.0)

    # ── 6 类因子计算 ──

    def _calc_emotion_factor(self, emotion_state: dict) -> dict:
        """情绪因子 [0,100]。"""
        factors = {}
        for key in ("lonely", "happy", "sleepy", "jealous", "sad", "angry", "calm", "anxious"):
            val = emotion_state.get(key, 0)
            if isinstance(val, (int, float)):
                factors[key] = min(val * 100.0 if val <= 1.0 else val, 100.0)
            else:
                factors[key] = 0.0
        return factors

    def _calc_relationship_factor(self, relationship_state: dict) -> dict:
        """关系因子 [0,100]."""
        factors = {}
        for key in ("love", "trust", "attachment", "security"):
            val = relationship_state.get(key, 0)
            if isinstance(val, (int, float)):
                factors[key] = min(val * 100.0 if val <= 1.0 else val, 100.0)
            else:
                factors[key] = 0.0
        return factors

    def _calc_world_factor(self, world_state) -> dict:
        """世界因子（含 night_factor [0,100]）."""
        night_map = {"early_morning":60,"morning":10,"noon":15,
                     "afternoon":20,"evening":50,"night":80,"late_night":95}
        tp = getattr(world_state, "time_period", "morning")
        wt = world_state.weather.type if hasattr(world_state, "weather") else "sunny"
        at = world_state.environment.atmosphere if hasattr(world_state, "environment") else "peaceful"
        wlm = {"rainy":60,"heavy_rain":75,"stormy":80,"snowy":35,"overcast":45,"foggy":40,"cloudy":20,"sunny":5}
        return {"night_factor": night_map.get(tp, 20),
                "weather_lonely": wlm.get(wt, 20),
                "weather_type": wt, "atmosphere": at, "time_period": tp}

    def _calc_user_factor(self, user_activity: dict) -> dict:
        """用户因子。inactive_time [0,100] = min(minutes/1440*100, 100)."""
        im = user_activity.get("inactive_minutes", 0)
        return {"inactive_time": min(im / 1440.0 * 100.0, 100.0),
                "inactive_minutes": im,
                "last_sentiment": user_activity.get("last_sentiment", "neutral")}

    def _calc_personality_factor(self, personality: dict) -> dict:
        """性格因子 [0,100]."""
        factors = {}
        for key in ("initiative", "shyness", "boldness"):
            val = personality.get(key, 0.5)
            factors[key] = min(val * 100.0 if isinstance(val, (int, float)) and val <= 1.0
                               else val if isinstance(val, (int, float)) else 50.0, 100.0)
        return factors

    def _calc_memory_factor(self, memory_context: dict) -> dict:
        """记忆因子。每 1 个触发 = 20 分，上限 100."""
        tc = memory_context.get("trigger_count", 0)
        return {"triggers": min(tc * 20.0, 100.0),
                "trigger_count": tc,
                "recent_topics": memory_context.get("recent_topics", [])}

    # ── 外部注入 ──

    def inject_external(self, factors: dict, character_id: str,
                        mood_pressure=None, absence_system=None) -> dict:
        """将 MoodPressure / AbsenceSystem 数据注入因子。"""
        if mood_pressure:
            pressures = mood_pressure.get_pressure_for_autonomy(character_id)
            for etype, pval in pressures.items():
                factors["emotion"][etype] = pval
                if etype == "lonely":
                    factors["raw_scores"]["emotion_lonely"] = pval
        if absence_system:
            factors["raw_scores"]["world_night_factor"] = absence_system.get_night_factor(
                factors["world"].get("time_period", "morning"))
            factors["raw_scores"]["user_inactive_time"] = absence_system.get_user_inactive_factor()
        return factors
