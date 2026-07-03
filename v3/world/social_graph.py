"""
V4 Social Graph — 角色间社交关系图

有向加权图：A→B 和 B→A 可以不同。
关系类型：friend / rival / crush / neutral / mentor / dependent。
支持社交事件传播。
"""

import json
from datetime import datetime
from typing import Optional

# ── 关系类型 ──
RELATION_TYPES = ["friend", "rival", "crush", "neutral", "mentor", "dependent"]

# ── 社交事件操作类型 ──
SOCIAL_OPS = ["chat", "argue", "help", "ignore", "compliment", "insult", "share_event"]


class SocialGraph:
    """角色间社交关系图（有向加权图）。

    关系值双向独立：A 对 B 的好感不等于 B 对 A 的好感。
    """

    def __init__(self, db=None, event_bus=None):
        self.db = db
        self.event_bus = event_bus

        # (from_id, to_id) → {"value": float(-100~100), "type": str, "history": [...]}
        self._edges: dict = {}

    # ── 基础操作 ──

    def set_relation(self, from_id: str, to_id: str,
                      value: float, rel_type: str = "neutral"):
        """设置 A→B 的关系。"""
        if rel_type not in RELATION_TYPES:
            raise ValueError(f"未知关系类型: {rel_type}")

        key = (from_id, to_id)
        self._edges[key] = {
            "value": max(-100, min(100, value)),
            "type": rel_type,
            "history": [],
            "updated_at": datetime.now().isoformat(),
        }

        if self.db:
            try:
                self.db.upsert_social_relation(from_id, to_id, value, rel_type)
            except Exception:
                pass

    def get_relation(self, from_id: str, to_id: str) -> dict:
        """获取 A→B 的关系。"""
        key = (from_id, to_id)
        if key in self._edges:
            return dict(self._edges[key])
        return {"value": 0, "type": "neutral", "history": []}

    def modify_relation(self, from_id: str, to_id: str, 
                         delta: float, trigger: str = "system"):
        """修改关系值（增量）。"""
        current = self.get_relation(from_id, to_id)
        new_value = max(-100, min(100, current["value"] + delta))
        current["value"] = new_value
        current["updated_at"] = datetime.now().isoformat()
        current.setdefault("history", []).append({
            "timestamp": datetime.now().isoformat(),
            "delta": delta,
            "trigger": trigger,
            "new_value": new_value,
        })
        if len(current["history"]) > 50:
            current["history"] = current["history"][-50:]

        self._edges[(from_id, to_id)] = current

        # 事件
        if self.event_bus:
            self.event_bus.publish("relation_changed", {
                "from_id": from_id,
                "to_id": to_id,
                "delta": delta,
                "new_value": new_value,
                "trigger": trigger,
            })

        if self.db:
            try:
                self.db.upsert_social_relation(from_id, to_id, new_value, current["type"])
            except Exception:
                pass

        return current

    # ── 批量操作 ──

    def get_relationships(self, character_id: str) -> list:
        """获取某角色的所有对外关系。"""
        results = []
        for (f_id, t_id), edge in self._edges.items():
            if f_id == character_id:
                results.append({
                    "to": t_id, "value": edge["value"],
                    "type": edge["type"],
                })
        return sorted(results, key=lambda x: abs(x["value"]), reverse=True)

    def tick_update(self):
        """每 tick 的关系自然衰减（趋于 neutral=0）。"""
        for (f_id, t_id), edge in list(self._edges.items()):
            val = edge["value"]
            if val > 0:
                edge["value"] = max(0, val - 0.05)
            elif val < 0:
                edge["value"] = min(0, val + 0.05)
            self._edges[(f_id, t_id)] = edge

        return {"updated_edges": len(self._edges)}

    # ── 社交事件传播 ──

    def propagate_event(self, event: dict, 
                         source_id: str, target_id: str) -> list:
        """传播社交事件：A 和 B 互动 → 与 A 和 B 相关的其他角色收到通知。

        Args:
            event: {"type": "chat"|"argue"|..., "intensity": 0.5, ...}
            source_id: 发起方
            target_id: 目标方

        Returns:
            受影响角色列表
        """
        event_type = event.get("type", "system")
        intensity = event.get("intensity", 0.5)
        affected = []

        # 找到与 source 和 target 有关系的所有角色
        related_chars = set()
        for (f_id, t_id) in self._edges:
            if f_id == source_id or f_id == target_id:
                related_chars.add(t_id)
            if t_id == source_id or t_id == target_id:
                related_chars.add(f_id)
        related_chars.discard(source_id)
        related_chars.discard(target_id)

        # 对每个相关角色产生关系偏差
        for char_id in related_chars:
            impact = self._calculate_event_impact(event_type, intensity)

            # 影响 source 对该角色的关系
            self.modify_relation(source_id, char_id, impact.get("source_delta", 0), f"propagated:{event_type}")

            # 影响该角色对 source 的关系
            self.modify_relation(char_id, source_id, impact.get("observer_delta", 0), f"witnessed:{event_type}")

            affected.append({
                "character_id": char_id,
                "impact": impact,
            })

        return affected

    def _calculate_event_impact(self, event_type: str, intensity: float) -> dict:
        """计算事件传播的影响值。"""
        impact_map = {
            "chat": {"source_delta": 2, "observer_delta": 1},
            "argue": {"source_delta": -5, "observer_delta": -2},
            "help": {"source_delta": 5, "observer_delta": 3},
            "ignore": {"source_delta": -3, "observer_delta": -1},
            "compliment": {"source_delta": 4, "observer_delta": 2},
            "insult": {"source_delta": -8, "observer_delta": -3},
            "share_event": {"source_delta": 2, "observer_delta": 2},
        }
        base = impact_map.get(event_type, {"source_delta": 0, "observer_delta": 0})
        return {
            "source_delta": base["source_delta"] * intensity,
            "observer_delta": base["observer_delta"] * intensity,
        }

    # ── 导出 ──

    def export_graph(self) -> dict:
        """导出完整关系图（用于 API 响应）。"""
        nodes = set()
        edges = []
        for (f_id, t_id), edge in self._edges.items():
            nodes.add(f_id)
            nodes.add(t_id)
            edges.append({
                "from": f_id, "to": t_id,
                "value": edge["value"], "type": edge["type"],
            })
        return {
            "nodes": [{"id": n} for n in sorted(nodes)],
            "edges": edges,
        }
