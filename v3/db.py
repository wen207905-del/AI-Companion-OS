"""
V3 数据库模型

使用 SQLite，定义所有 V3 新表的建表语句和基础 ORM 操作。
Phase 2 新增: autonomy_decisions / mood_pressure_log / absence_log / feedback_events。
"""

import sqlite3
import json
import os
from datetime import datetime
from .config import V3_DB_PATH


class V3Database:
    """V3 数据库管理类，负责建表、连接和基础 CRUD 操作。"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or V3_DB_PATH
        self.conn: sqlite3.Connection = None

    def connect(self):
        """建立数据库连接并启用外键和 WAL 模式。"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        """关闭数据库连接。"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_tables(self):
        """创建所有 V3 表（含 Phase 1 + Phase 2）。"""
        cursor = self.conn.cursor()

        # ── 世界状态表 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS world_state (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         INTEGER NOT NULL,
                datetime_text   TEXT    NOT NULL,
                day_of_week     TEXT    NOT NULL,
                time_period     TEXT    NOT NULL,
                season          TEXT    NOT NULL,
                weather_type    TEXT    NOT NULL,
                temperature     REAL    NOT NULL,
                humidity        REAL    NOT NULL,
                wind_level      INTEGER NOT NULL,
                light           TEXT    NOT NULL,
                noise           TEXT    NOT NULL,
                atmosphere      TEXT    NOT NULL,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── 世界事件表 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS world_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         INTEGER NOT NULL,
                event_type      TEXT    NOT NULL,
                event_desc      TEXT    NOT NULL,
                severity        TEXT    DEFAULT 'normal',
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── 角色状态表 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_state (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL UNIQUE,
                current_activity TEXT   DEFAULT 'idle',
                current_location TEXT   DEFAULT 'home',
                activity_started TEXT,
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── 角色活动历史表 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_activity_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                tick_id         INTEGER NOT NULL,
                activity        TEXT    NOT NULL,
                time_period     TEXT    NOT NULL,
                weather_type    TEXT    NOT NULL,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── 角色视觉档案表 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_visual_profile (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL UNIQUE,
                face_json       TEXT    NOT NULL DEFAULT '{}',
                body_json       TEXT    NOT NULL DEFAULT '{}',
                hair_json       TEXT    NOT NULL DEFAULT '{}',
                style_id        TEXT    DEFAULT 'semi_realistic_v1',
                is_adult        INTEGER DEFAULT 1,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── 图片请求表 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_requests (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                request_json    TEXT    NOT NULL,
                status          TEXT    DEFAULT 'pending',
                trigger_type    TEXT    NOT NULL,
                album_category  TEXT    DEFAULT 'generated_archive',
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── 图片资产表 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_assets (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                request_id      INTEGER,
                file_path       TEXT    NOT NULL,
                album_category  TEXT    DEFAULT 'generated_archive',
                caption         TEXT,
                scene_type      TEXT,
                emotion_tag     TEXT,
                event_id        TEXT,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── Phase 2: 自主决策日志表 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS autonomy_decisions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         INTEGER NOT NULL,
                character_id    TEXT    NOT NULL,
                action_type     TEXT    NOT NULL,
                probability     REAL    NOT NULL,
                decision        TEXT    NOT NULL,
                reason          TEXT,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── 叙事线索表 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS narrative_threads (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_type     TEXT    NOT NULL,
                character_ids   TEXT    NOT NULL,
                status          TEXT    DEFAULT 'active',
                stage           INTEGER DEFAULT 0,
                data_json       TEXT    DEFAULT '{}',
                started_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── Tick 计数器 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tick_counter (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         INTEGER NOT NULL DEFAULT 0
            )
        """)

        # ── Phase 2: 情绪压力日志 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mood_pressure_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         INTEGER NOT NULL,
                character_id    TEXT    NOT NULL,
                emotion_type    TEXT    NOT NULL,
                pressure_before REAL    NOT NULL,
                pressure_after  REAL    NOT NULL,
                delta           REAL    NOT NULL,
                trigger         TEXT    DEFAULT 'tick',
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── Phase 2: 缺席记录 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS absence_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         INTEGER NOT NULL,
                inactive_minutes INTEGER NOT NULL,
                absence_stage   TEXT    NOT NULL,
                effect_summary  TEXT,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── Phase 2: 反馈事件记录 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         INTEGER NOT NULL,
                character_id    TEXT    NOT NULL,
                action_type     TEXT    NOT NULL,
                action_target   TEXT    DEFAULT 'user',
                intent          TEXT,
                confidence      REAL    NOT NULL,
                priority        INTEGER NOT NULL,
                execution_status TEXT   DEFAULT 'executed',
                user_response   TEXT    DEFAULT 'none',
                emotion_delta_json  TEXT DEFAULT '{}',
                relationship_delta_json TEXT DEFAULT '{}',
                memory_entry    TEXT,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ws_tick ON world_state(tick_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_we_tick ON world_events(tick_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cs_char ON character_state(character_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ad_char ON autonomy_decisions(character_id, tick_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ia_char ON image_assets(character_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mpl_char ON mood_pressure_log(character_id, tick_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fe_char ON feedback_events(character_id, tick_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_al_tick ON absence_log(tick_id)")

        self.conn.commit()

    # ──────── Tick 基础 ────────

    def get_tick_id(self) -> int:
        """获取当前 tick_id 并自增。"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT tick_id FROM tick_counter ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO tick_counter (tick_id) VALUES (1)")
            self.conn.commit()
            return 1
        else:
            new_id = row["tick_id"] + 1
            cursor.execute("INSERT INTO tick_counter (tick_id) VALUES (?)", (new_id,))
            self.conn.commit()
            return new_id

    # ──────── 世界状态 ────────

    def insert_world_state(self, tick_id: int, state: dict):
        """写入一条世界状态记录。"""
        self.conn.execute("""
            INSERT INTO world_state
                (tick_id, datetime_text, day_of_week, time_period, season,
                 weather_type, temperature, humidity, wind_level, light, noise, atmosphere)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tick_id,
            state["datetime"],
            state["day_of_week"],
            state["time_period"],
            state.get("season", "summer"),
            state["weather"]["type"],
            state["weather"]["temperature"],
            state["weather"]["humidity"],
            state["weather"]["wind_level"],
            state["environment"]["light"],
            state["environment"]["noise"],
            state["environment"]["atmosphere"],
        ))
        self.conn.commit()

    def insert_world_event(self, tick_id: int, event_type: str, event_desc: str, severity: str = "normal"):
        """写入一条世界事件。"""
        self.conn.execute(
            "INSERT INTO world_events (tick_id, event_type, event_desc, severity) VALUES (?, ?, ?, ?)",
            (tick_id, event_type, event_desc, severity)
        )
        self.conn.commit()

    # ──────── 角色状态 ────────

    def upsert_character_state(self, character_id: str, activity: str, location: str = "home"):
        """更新或插入角色当前状态。"""
        self.conn.execute("""
            INSERT INTO character_state (character_id, current_activity, current_location, activity_started, updated_at)
            VALUES (?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))
            ON CONFLICT(character_id) DO UPDATE SET
                current_activity = excluded.current_activity,
                current_location = excluded.current_location,
                activity_started = CASE
                    WHEN character_state.current_activity != excluded.current_activity
                    THEN datetime('now','localtime')
                    ELSE character_state.activity_started
                END,
                updated_at = datetime('now','localtime')
        """, (character_id, activity, location))
        self.conn.commit()

    def insert_character_activity_log(self, character_id: str, tick_id: int,
                                       activity: str, time_period: str, weather_type: str):
        """写入角色活动日志。"""
        self.conn.execute(
            "INSERT INTO character_activity_log (character_id, tick_id, activity, time_period, weather_type) VALUES (?, ?, ?, ?, ?)",
            (character_id, tick_id, activity, time_period, weather_type)
        )
        self.conn.commit()

    def get_all_characters(self) -> list:
        """获取所有角色 ID 列表。"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT character_id, current_activity, current_location FROM character_state")
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_world_states(self, limit: int = 10) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM world_state ORDER BY tick_id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_world_events(self, limit: int = 50) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM world_events ORDER BY tick_id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    # ──────── Phase 2: 自主决策 ────────

    def insert_autonomy_decision(self, tick_id: int, character_id: str,
                                  action_type: str, probability: float,
                                  decision: str, reason: str = None):
        """写入自主决策记录。"""
        self.conn.execute(
            "INSERT INTO autonomy_decisions (tick_id, character_id, action_type, probability, decision, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (tick_id, character_id, action_type, probability, decision, reason)
        )
        self.conn.commit()

    def get_last_autonomy_decision(self, character_id: str) -> dict:
        """获取角色最近一次自主决策。"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM autonomy_decisions WHERE character_id = ? ORDER BY tick_id DESC LIMIT 1",
            (character_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    # ──────── Phase 2: 情绪压力 ────────

    def insert_mood_pressure_log(self, tick_id: int, character_id: str,
                                  emotion_type: str, pressure_before: float,
                                  pressure_after: float, delta: float, trigger: str = "tick"):
        """写入情绪压力日志。"""
        self.conn.execute(
            "INSERT INTO mood_pressure_log (tick_id, character_id, emotion_type, pressure_before, pressure_after, delta, trigger) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tick_id, character_id, emotion_type, pressure_before, pressure_after, delta, trigger)
        )
        self.conn.commit()

    def get_character_pressures(self, character_id: str) -> dict:
        """获取角色当前所有情绪压力值。"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT emotion_type, pressure_after FROM mood_pressure_log
            WHERE character_id = ?
            AND id IN (
                SELECT MAX(id) FROM mood_pressure_log
                WHERE character_id = ?
                GROUP BY emotion_type
            )
        """, (character_id, character_id))
        return {row["emotion_type"]: row["pressure_after"] for row in cursor.fetchall()}

    # ──────── Phase 2: 缺席 ────────

    def insert_absence_log(self, tick_id: int, inactive_minutes: int,
                            absence_stage: str, effect_summary: str = None):
        """写入缺席记录。"""
        self.conn.execute(
            "INSERT INTO absence_log (tick_id, inactive_minutes, absence_stage, effect_summary) VALUES (?, ?, ?, ?)",
            (tick_id, inactive_minutes, absence_stage, effect_summary)
        )
        self.conn.commit()

    def get_last_absence_log(self) -> dict:
        """获取最近一次缺席记录。"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM absence_log ORDER BY tick_id DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    # ──────── Phase 2: 反馈事件 ────────

    def insert_feedback_event(self, tick_id: int = None, character_id: str = None,
                               action_type: str = None, action_target: str = "user",
                               intent: str = None, confidence: float = 0.0, priority: int = 0,
                               execution_status: str = "executed", user_response: str = "none",
                               emotion_delta: dict = None, relationship_delta: dict = None,
                               emotion_delta_json: str = "{}", relationship_delta_json: str = "{}",
                               memory_entry: str = None, score: float = None,
                               memory_record: str = None, world_affect: dict = None):
        """写入反馈事件记录。

        兼容两套调用方式：
        - FeedbackLoop：传 tick_id=None（自动获取），emotion_delta/relationship_delta dict，score/memory_record/world_affect
        - 原始调用：传 emotion_delta_json/relationship_delta_json 字符串
        """
        # 自动获取 tick_id
        if tick_id is None:
            tick_id = self.get_tick_id()

        # 处理 dict 参数 -> JSON 字符串
        if emotion_delta is not None:
            emotion_delta_json = json.dumps(emotion_delta, ensure_ascii=False)
        if relationship_delta is not None:
            relationship_delta_json = json.dumps(relationship_delta, ensure_ascii=False)

        # 处理 FeedbackLoop 的简化参数
        effective_confidence = confidence if score is None else score / 100.0
        effective_memory = memory_entry or memory_record

        self.conn.execute("""
            INSERT INTO feedback_events
                (tick_id, character_id, action_type, action_target, intent,
                 confidence, priority, execution_status, user_response,
                 emotion_delta_json, relationship_delta_json, memory_entry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tick_id, character_id, action_type, action_target, intent,
              effective_confidence, priority, execution_status, user_response,
              emotion_delta_json, relationship_delta_json, effective_memory))
        self.conn.commit()

    def get_recent_feedback_events(self, character_id: str = None, limit: int = 50) -> list:
        cursor = self.conn.cursor()
        if character_id:
            cursor.execute("SELECT * FROM feedback_events WHERE character_id = ? ORDER BY tick_id DESC LIMIT ?",
                           (character_id, limit))
        else:
            cursor.execute("SELECT * FROM feedback_events ORDER BY tick_id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_action_last_occurrence(self, character_id: str, action_type: str) -> str:
        """获取角色某行为类型最后一次发生的时间（用于冷却判定）。"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT created_at FROM feedback_events WHERE character_id = ? AND action_type = ? ORDER BY created_at DESC LIMIT 1",
            (character_id, action_type)
        )
        row = cursor.fetchone()
        return row["created_at"] if row else None
