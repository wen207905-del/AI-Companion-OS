"""
V4 Intention Engine — 长期意图引擎

长期意图随时间衰减/增强，影响 Autonomy 评分权重。
"""

from datetime import datetime, timedelta
from typing import Optional

# ── 长期意图类型 ──
INTENTION_TYPES = [
    "become_closer",     # 想拉近关系
    "create_distance",   # 想保持距离
    "seek_attention",    # 想引起注意
    "protect_user",      # 想保护用户
    "test_boundary",     # 想试探边界
]

# ── 默认衰减率（每小时） ──
DEFAULT_DECAY_RATE = 0.005  # 每小时衰减 0.5%


class IntentionEngine:
    """长期意图引擎。

    意图随角色经历变化，影响 Autonomy 中各项评分权重。
    """

    def __init__(self, db=None, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self._intentions: dict = {}  # char_id → {intention_type: strength, last_update: datetime}

    def get_intentions(self, character_id: str) -> dict:
        """获取角色当前意图。"""
        if character_id not in self._intentions:
            self._load_or_init(character_id)
        self._decay(character_id)
        return {
            k: v["strength"]
            for k, v in self._intentions[character_id].items()
            if k != "_last_update"
        }

    def _load_or_init(self, character_id: str):
        """从数据库加载或初始化。"""
        if self.db:
            try:
                existing = self.db.get_intentions(character_id)
                if existing:
                    self._intentions[character_id] = {}
                    for intent in existing:
                        name = intent.get("type") or intent.get("intention_type")
                        if name in INTENTION_TYPES:
                            self._intentions[character_id][name] = {
                                "strength": float(intent.get("strength", 0.2)),
                                "last_update": datetime.now(),
                            }
                    self._intentions[character_id]["_last_update"] = datetime.now()
                    return
            except Exception:
                pass

        self._intentions[character_id] = {}
        for it in INTENTION_TYPES:
            self._intentions[character_id][it] = {
                "strength": 0.1,
                "last_update": datetime.now(),
            }
        self._intentions[character_id]["_last_update"] = datetime.now()

    def _decay(self, character_id: str):
        """随时间自然衰减。"""
        if character_id not in self._intentions:
            return
        now = datetime.now()
        last = self._intentions[character_id].get("_last_update", now)
        hours = max(0, (now - last).total_seconds() / 3600)

        if hours > 0:
            for it in INTENTION_TYPES:
                old = self._intentions[character_id].get(it, {})
                strength = old.get("strength", 0.1)
                strength = max(0.01, strength * (1 - DEFAULT_DECAY_RATE * hours))
                self._intentions[character_id][it] = {
                    "strength": strength,
                    "last_update": now,
                }
            self._intentions[character_id]["_last_update"] = now

    # ── 修改意图 ──

    def boost(self, character_id: str, intention_type: str,
              amount: float = 0.1):
        """增强某意图。"""
        if intention_type not in INTENTION_TYPES:
            return
        self.get_intentions(character_id)  # 确保初始化
        old = self._intentions[character_id].get(intention_type, {}).get("strength", 0.1)
        new = min(1.0, old + amount)
        self._intentions[character_id][intention_type] = {
            "strength": new,
            "last_update": datetime.now(),
        }

        if self.db:
            try:
                self.db.upsert_intention(character_id, intention_type, new)
            except Exception:
                pass

    def dampen(self, character_id: str, intention_type: str,
               amount: float = 0.1):
        """削弱某意图。"""
        if intention_type not in INTENTION_TYPES:
            return
        self.get_intentions(character_id)
        old = self._intentions[character_id].get(intention_type, {}).get("strength", 0.1)
        new = max(0.01, old - amount)
        self._intentions[character_id][intention_type] = {
            "strength": new,
            "last_update": datetime.now(),
        }

        if self.db:
            try:
                self.db.upsert_intention(character_id, intention_type, new)
            except Exception:
                pass

    # ── 对 Autonomy 的影响 ──

    def get_autonomy_bias(self, character_id: str) -> dict:
        """获取意图对自主决策的偏差影响。

        Returns:
            {desire_type: weight_bias, ...}  范围 -0.1 ~ +0.1
        """
        intents = self.get_intentions(character_id)
        bias = {}

        bc = intents.get("become_closer", 0)
        if bc > 0.3:
            bias["desire_to_connect"] = min(0.1, (bc - 0.3) * 0.2)

        cd = intents.get("create_distance", 0)
        if cd > 0.3:
            bias["desire_to_avoid"] = min(0.1, (cd - 0.3) * 0.2)

        sa = intents.get("seek_attention", 0)
        if sa > 0.4:
            bias["desire_to_express"] = min(0.1, (sa - 0.4) * 0.25)

        tb = intents.get("test_boundary", 0)
        if tb > 0.5:
            bias["desire_to_compete"] = min(0.1, (tb - 0.5) * 0.3)

        return bias
