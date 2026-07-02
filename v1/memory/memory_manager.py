"""
记忆管理器 (Memory Manager)
使用 SQLite 实现四级记忆（永久/长期/短期/会话）的存储、检索、强化和衰减。
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional

from ..models.memory_model import Memory, MemoryTier, UserProfile


class MemoryManager:
    """
    记忆管理器

    数据库表：
    - memories: 核心记忆存储
    - user_profile: 用户画像
    - milestones: 里程碑记录

    职责：
    1. 四级记忆存储与管理
    2. 记忆检索（按相关度排序）
    3. 记忆强化（召回计数刷新）
    4. 记忆衰减（定期过期清理）
    5. 获取最近上下文（用于 Prompt 注入）
    """

    # TTL 定义（秒）
    TTL_CONFIG: dict[MemoryTier, Optional[int]] = {
        MemoryTier.PERMANENT: None,        # 永不过期
        MemoryTier.LONG: 365 * 24 * 3600,  # 365 天
        MemoryTier.SHORT: 7 * 24 * 3600,   # 7 天
        MemoryTier.SESSION: 1800,           # 30 分钟
    }

    def __init__(self, db_dir: str = "data"):
        """
        初始化记忆管理器

        Args:
            db_dir: 数据库文件存放目录
        """
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, "ai_companion.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()

        # 记忆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tier TEXT NOT NULL DEFAULT 'session',
                content TEXT NOT NULL,
                emotion_tags TEXT DEFAULT '[]',
                intensity REAL DEFAULT 50.0,
                timestamp TEXT NOT NULL,
                last_recall TEXT,
                recall_count INTEGER DEFAULT 0,
                ttl INTEGER
            )
        """)

        # 用户画像表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 里程碑表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                details TEXT DEFAULT '{}'
            )
        """)

        # 创建索引加速查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_tier ON memories(tier)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_ttl ON memories(ttl)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_intensity ON memories(intensity)")

        self.conn.commit()

    def store(self, tier: MemoryTier, content: str,
              emotion_tags: list[str] | None = None,
              intensity: float = 50.0) -> int:
        """
        存储一条新记忆

        Args:
            tier: 记忆层级
            content: 记忆内容
            emotion_tags: 关联情绪标签
            intensity: 情感强度 (0-100)

        Returns:
            新记忆的 ID
        """
        now = datetime.now()
        timestamp = now.isoformat()

        # 计算 TTL
        base_ttl = self.TTL_CONFIG.get(tier)
        ttl = None
        if base_ttl is not None:
            ttl = int(now.timestamp()) + base_ttl

        # 高情感强度自动升级 tier
        if intensity >= 80 and tier == MemoryTier.SESSION:
            tier = MemoryTier.SHORT
        elif intensity >= 90 and tier == MemoryTier.SHORT:
            tier = MemoryTier.LONG

        emotion_tags_json = json.dumps(emotion_tags or [], ensure_ascii=False)

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO memories (tier, content, emotion_tags, intensity, timestamp, last_recall, recall_count, ttl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tier.value, content, emotion_tags_json, intensity,
            timestamp, timestamp, 1, ttl
        ))
        self.conn.commit()
        return cursor.lastrowid

    def recall(self, query: str, limit: int = 10,
               tier_filter: MemoryTier | None = None) -> list[Memory]:
        """
        按相关度检索记忆

        Args:
            query: 查询关键词
            limit: 返回数量上限
            tier_filter: 可选，限制搜索的记忆层级

        Returns:
            按相关度排序的记忆列表
        """
        cursor = self.conn.cursor()

        # 基础查询：排除已过期的非永久记忆
        now_ts = int(datetime.now().timestamp())

        where_clauses = [
            "(ttl IS NULL OR ttl > ?)"
        ]
        params = [now_ts]

        if tier_filter:
            where_clauses.append("tier = ?")
            params.append(tier_filter.value)

        where_sql = " AND ".join(where_clauses)

        # 按相关度排序：结合情感强度和关键词匹配
        cursor.execute(f"""
            SELECT id, tier, content, emotion_tags, intensity, timestamp, last_recall, recall_count, ttl
            FROM memories
            WHERE {where_sql}
            ORDER BY
                CASE WHEN content LIKE ? THEN 3 ELSE 0 END +
                (intensity / 100.0 * 2) +
                (recall_count * 0.5) +
                CASE WHEN tier = 'permanent' THEN 1 ELSE 0 END
                DESC
            LIMIT ?
        """, params + [f"%{query}%", limit])

        rows = cursor.fetchall()
        memories = []

        for row in rows:
            mem = Memory(
                id=row["id"],
                tier=MemoryTier(row["tier"]),
                content=row["content"],
                emotion_tags=json.loads(row["emotion_tags"]),
                intensity=row["intensity"],
                timestamp=row["timestamp"],
                last_recall=row["last_recall"],
                recall_count=row["recall_count"],
                ttl=row["ttl"],
            )
            memories.append(mem)

        return memories

    def reinforce(self, memory_id: int):
        """
        强化记忆：增加 recall_count，刷新时间戳和 TTL

        Args:
            memory_id: 记忆 ID
        """
        cursor = self.conn.cursor()
        now = datetime.now()

        # 获取当前记忆
        cursor.execute("SELECT tier, recall_count, ttl FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if not row:
            return

        tier = MemoryTier(row["tier"])
        recall_count = row["recall_count"]

        # 最多延长10次
        if recall_count >= 10:
            return

        # 计算新TTL
        new_ttl = row["ttl"]
        if tier != MemoryTier.PERMANENT and new_ttl is not None:
            current_remaining = new_ttl - int(datetime.now().timestamp())
            if current_remaining > 0:
                new_ttl = int(datetime.now().timestamp()) + int(current_remaining * 1.5)

        cursor.execute("""
            UPDATE memories
            SET last_recall = ?, recall_count = recall_count + 1, ttl = ?
            WHERE id = ?
        """, (now.isoformat(), new_ttl, memory_id))
        self.conn.commit()

    def decay(self) -> dict:
        """
        检查并衰减/遗忘过期记忆

        Returns:
            衰减统计
        """
        cursor = self.conn.cursor()
        now_ts = int(datetime.now().timestamp())

        # 获取所有非永久、已过期的记忆
        cursor.execute("""
            SELECT id, tier, content, intensity
            FROM memories
            WHERE tier != 'permanent' AND ttl IS NOT NULL AND ttl <= ?
        """, (now_ts,))
        expired = cursor.fetchall()

        decayed = []
        fully_forgotten = []

        for row in expired:
            mem_id = row["id"]
            tier = MemoryTier(row["tier"])

            # 高情感强度 (>60) 的记忆降级而非直接删除
            if row["intensity"] > 60 and tier != MemoryTier.SESSION:
                # 降级到下一级
                downgrade_map = {
                    MemoryTier.LONG: MemoryTier.SHORT,
                    MemoryTier.SHORT: MemoryTier.SESSION,
                }
                new_tier = downgrade_map.get(tier)
                if new_tier:
                    new_ttl = int(datetime.now().timestamp()) + self.TTL_CONFIG.get(new_tier, 1800)
                    cursor.execute("""
                        UPDATE memories SET tier = ?, ttl = ? WHERE id = ?
                    """, (new_tier.value, new_ttl, mem_id))
                    decayed.append({"id": mem_id, "from_tier": tier.value, "to_tier": new_tier.value})
            else:
                # 低情感强度直接删除
                cursor.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
                fully_forgotten.append({"id": mem_id, "tier": tier.value, "content_preview": row["content"][:50]})

        self.conn.commit()

        return {
            "expired_count": len(expired),
            "decayed_count": len(decayed),
            "decayed": decayed,
            "fully_forgotten_count": len(fully_forgotten),
            "fully_forgotten": fully_forgotten,
        }

    def get_recent_context(self, n: int = 5) -> list[Memory]:
        """
        获取最近N条相关记忆，用于注入 Prompt

        Args:
            n: 返回条数

        Returns:
            按相关度排序的记忆列表
        """
        cursor = self.conn.cursor()
        now_ts = int(datetime.now().timestamp())

        cursor.execute("""
            SELECT id, tier, content, emotion_tags, intensity, timestamp, last_recall, recall_count, ttl
            FROM memories
            WHERE (ttl IS NULL OR ttl > ?)
            ORDER BY
                CASE tier
                    WHEN 'permanent' THEN 4
                    WHEN 'long' THEN 3
                    WHEN 'short' THEN 2
                    WHEN 'session' THEN 1
                END DESC,
                intensity DESC,
                last_recall DESC
            LIMIT ?
        """, (now_ts, n))

        rows = cursor.fetchall()
        memories = []

        for row in rows:
            mem = Memory(
                id=row["id"],
                tier=MemoryTier(row["tier"]),
                content=row["content"],
                emotion_tags=json.loads(row["emotion_tags"]),
                intensity=row["intensity"],
                timestamp=row["timestamp"],
                last_recall=row["last_recall"],
                recall_count=row["recall_count"],
                ttl=row["ttl"],
            )
            memories.append(mem)

        return memories

    # ========== 用户画像 ==========

    def set_user_profile(self, field: str, value: str):
        """
        设置用户画像字段

        Args:
            field: 字段名
            value: 字段值
        """
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO user_profile (field, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(field) DO UPDATE SET value = ?, updated_at = ?
        """, (field, value, now, value, now))
        self.conn.commit()

    def get_user_profile(self, field: str) -> Optional[str]:
        """获取用户画像字段"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM user_profile WHERE field = ?", (field,))
        row = cursor.fetchone()
        return row["value"] if row else None

    def get_all_user_profile(self) -> dict[str, str]:
        """获取全部用户画像"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT field, value FROM user_profile ORDER BY field")
        return {row["field"]: row["value"] for row in cursor.fetchall()}

    # ========== 里程碑 ==========

    def record_milestone(self, event_name: str, details: dict | None = None):
        """
        记录里程碑事件

        Args:
            event_name: 事件名称
            details: 事件详情
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO milestones (event_name, occurred_at, details)
            VALUES (?, ?, ?)
        """, (event_name, datetime.now().isoformat(), json.dumps(details or {}, ensure_ascii=False)))
        self.conn.commit()

    def get_milestones(self) -> list[dict]:
        """获取所有里程碑"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT event_name, occurred_at, details FROM milestones ORDER BY occurred_at")
        return [
            {"event_name": row["event_name"], "occurred_at": row["occurred_at"],
             "details": json.loads(row["details"])}
            for row in cursor.fetchall()
        ]

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
