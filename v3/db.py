"""
V3 数据库模型

支持 SQLite（默认）和 PostgreSQL（通过环境变量 DB_TYPE=postgres 切换）。
定义所有 V3 新表的建表语句和基础 ORM 操作。
Phase 2 新增: autonomy_decisions / mood_pressure_log / absence_log / feedback_events。
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

from .config import V3_DB_PATH, DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


class V3Database:
    """V3 数据库管理类，支持 SQLite 和 PostgreSQL 双后端。

    通过环境变量 DB_TYPE 切换：
    - DB_TYPE=sqlite（默认）：使用 SQLite 文件存储
    - DB_TYPE=postgres：使用 PostgreSQL，连接参数从环境变量读取

    Usage:
        db = V3Database()
        db.connect()
        db.create_tables()
        # ... 操作 ...
        db.close()
    """

    def __init__(self, db_path: str = None):
        self._db_type = DB_TYPE
        self.db_path = db_path or V3_DB_PATH
        self.conn = None
        self._pool = None  # PostgreSQL 连接池（psycopg2 pool）

    def connect(self):
        """建立数据库连接。

        SQLite: 启用 WAL 模式 + 外键。
        PostgreSQL: 使用 psycopg2 连接池。
        """
        if self._db_type == "postgres":
            return self._connect_postgres()
        else:
            return self._connect_sqlite()

    def _connect_sqlite(self):
        """SQLite 连接。"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def _connect_postgres(self):
        """PostgreSQL 连接（使用连接池）。"""
        try:
            import psycopg2
            from psycopg2 import pool
            from psycopg2.extras import RealDictCursor
        except ImportError:
            raise ImportError(
                "psycopg2-binary 未安装。请运行: pip install psycopg2-binary"
            )

        if self._pool is None:
            self._pool = pool.SimpleConnectionPool(
                1, 10,
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                dbname=DB_NAME,
            )

        self.conn = self._pool.getconn()
        # 设置 cursor_factory 以获得类 dict 访问
        self._pg_cursor_factory = RealDictCursor
        return self.conn

    def close(self):
        """关闭数据库连接。"""
        if self.conn:
            if self._db_type == "postgres":
                if self._pool:
                    self._pool.putconn(self.conn)
                self.conn = None
            else:
                self.conn.close()
                self.conn = None

    def close_all(self):
        """关闭所有连接（PostgreSQL 连接池）。"""
        if self._db_type == "postgres" and self._pool:
            self._pool.closeall()
            self._pool = None
        elif self.conn:
            self.conn.close()
            self.conn = None

    def _execute(self, sql: str, params: tuple = None):
        """统一执行 SQL，兼容 SQLite 和 PostgreSQL。

        PostgreSQL 会自动替换：
        - DATETIME('now','localtime') → NOW()
        - INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
        - 保留 ON CONFLICT ... DO UPDATE 语法（两者均支持）
        """
        if self._db_type == "postgres":
            sql = self._pg_adapt_sql(sql)

        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor

    def _pg_adapt_sql(self, sql: str) -> str:
        """将 SQLite 特定语法转换为 PostgreSQL 语法。"""
        # datetime('now','localtime') → NOW()
        sql = sql.replace("datetime('now','localtime')", "NOW()")
        # INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        return sql

    def _pg_cursor(self):
        """返回 PostgreSQL 兼容的 cursor，SQLite 直接使用 self.conn。"""
        if self._db_type == "postgres":
            return self.conn.cursor(cursor_factory=self._pg_cursor_factory)
        return self.conn.cursor()

    def create_tables(self):
        """创建所有 V3 表（含 Phase 1 + Phase 2）。"""
        cursor = self._execute("""
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

        self._execute("""
            CREATE TABLE IF NOT EXISTS world_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         INTEGER NOT NULL,
                event_type      TEXT    NOT NULL,
                event_desc      TEXT    NOT NULL,
                severity        TEXT    DEFAULT 'normal',
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS character_state (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL UNIQUE,
                current_activity TEXT   DEFAULT 'idle',
                current_location TEXT   DEFAULT 'home',
                activity_started TEXT,
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
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

        self._execute("""
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

        self._execute("""
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

        self._execute("""
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

        self._execute("""
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

        self._execute("""
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

        self._execute("""
            CREATE TABLE IF NOT EXISTS tick_counter (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         INTEGER NOT NULL DEFAULT 0
            )
        """)

        self._execute("""
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

        self._execute("""
            CREATE TABLE IF NOT EXISTS absence_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         INTEGER NOT NULL,
                inactive_minutes INTEGER NOT NULL,
                absence_stage   TEXT    NOT NULL,
                effect_summary  TEXT,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
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

        # ── V4 新增表 ──

        self._execute("""
            CREATE TABLE IF NOT EXISTS emotion_snapshots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                tick_id         INTEGER NOT NULL,
                emotions_json   TEXT    NOT NULL DEFAULT '{}',
                pressures_json  TEXT    NOT NULL DEFAULT '{}',
                dominant        TEXT    DEFAULT 'calm',
                absence_hours   REAL    DEFAULT 0,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS relationship_snapshots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                tick_id         INTEGER NOT NULL,
                attachment      REAL    DEFAULT 0,
                trust           REAL    DEFAULT 50,
                intimacy        REAL    DEFAULT 0,
                warmth          REAL    DEFAULT 50,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS memory_items (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                user_id         TEXT    DEFAULT 'default_user',
                memory_type     TEXT    NOT NULL DEFAULT 'short',
                content         TEXT    NOT NULL,
                summary         TEXT    DEFAULT '',
                emotion_tags    TEXT    DEFAULT '[]',
                importance      REAL    DEFAULT 0.5,
                intensity       REAL    DEFAULT 0.5,
                source          TEXT    DEFAULT 'system',
                metadata_json   TEXT    DEFAULT '{}',
                access_count    INTEGER DEFAULT 0,
                last_accessed   TEXT,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS diary_entries (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                entry_date      TEXT    NOT NULL,
                title           TEXT,
                content         TEXT    NOT NULL,
                mood            TEXT    DEFAULT 'neutral',
                weather         TEXT,
                key_events      TEXT    DEFAULT '[]',
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                event_type      TEXT    NOT NULL,
                event_name      TEXT    NOT NULL,
                event_date      TEXT    NOT NULL,
                repeat_yearly   INTEGER DEFAULT 0,
                emotional_impact TEXT   DEFAULT '{}',
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── V4 新增索引 ──
        self._execute("CREATE INDEX IF NOT EXISTS idx_es_char ON emotion_snapshots(character_id, tick_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_rs_char ON relationship_snapshots(character_id, tick_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_mi_char ON memory_items(character_id, memory_type)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_de_char ON diary_entries(character_id, entry_date)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_ce_char ON calendar_events(character_id, event_date)")

        # 索引 — PostgreSQL 中 CREATE INDEX IF NOT EXISTS 也支持
        self._execute("CREATE INDEX IF NOT EXISTS idx_ws_tick ON world_state(tick_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_we_tick ON world_events(tick_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_cs_char ON character_state(character_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_ad_char ON autonomy_decisions(character_id, tick_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_ia_char ON image_assets(character_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_mpl_char ON mood_pressure_log(character_id, tick_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_fe_char ON feedback_events(character_id, tick_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_al_tick ON absence_log(tick_id)")

        self.commit()

    # ──────── 通用工具 ────────

    def commit(self):
        """提交事务。SQLite 直接 commit，PostgreSQL 也 commit。"""
        if self.conn:
            self.conn.commit()

    def _fetchone(self, cursor) -> Optional[dict]:
        """统一获取一行。"""
        row = cursor.fetchone()
        if row is None:
            return None
        if self._db_type == "postgres":
            return dict(row)
        return dict(row)

    def _fetchall(self, cursor) -> list:
        """统一获取多行。"""
        rows = cursor.fetchall()
        if self._db_type == "postgres":
            return [dict(r) for r in rows]
        return [dict(r) for r in rows]

    # ──────── Tick 基础 ────────

    def get_tick_id(self) -> int:
        """获取当前 tick_id 并自增。"""
        # 使用 _pg_cursor() 确保 PG 游标类型
        cursor = self._pg_cursor()
        cursor.execute("SELECT tick_id FROM tick_counter ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO tick_counter (tick_id) VALUES (1)")
            self.commit()
            return 1
        else:
            new_id = (row["tick_id"] if self._db_type == "postgres" else row["tick_id"]) + 1
            cursor.execute("INSERT INTO tick_counter (tick_id) VALUES (%s)" if self._db_type == "postgres" else "INSERT INTO tick_counter (tick_id) VALUES (?)", (new_id,))
            self.commit()
            return new_id

    # ──────── 世界状态 ────────

    def insert_world_state(self, tick_id: int, state: dict):
        """写入一条世界状态记录。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        placeholder = "%s" if pg else "?"
        sql = f"""
            INSERT INTO world_state
                (tick_id, datetime_text, day_of_week, time_period, season,
                 weather_type, temperature, humidity, wind_level, light, noise, atmosphere)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                    {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                    {placeholder}, {placeholder})
        """
        cursor.execute(sql, (
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
        self.commit()

    def insert_world_event(self, tick_id: int, event_type: str,
                            event_desc: str, severity: str = "normal"):
        """写入一条世界事件。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        ph = "%s" if pg else "?"
        cursor.execute(
            f"INSERT INTO world_events (tick_id, event_type, event_desc, severity) VALUES ({ph}, {ph}, {ph}, {ph})",
            (tick_id, event_type, event_desc, severity)
        )
        self.commit()

    # ──────── 角色状态 ────────

    def upsert_character_state(self, character_id: str, activity: str,
                                location: str = "home"):
        """更新或插入角色当前状态。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        ph = "%s" if pg else "?"

        if pg:
            cursor.execute(f"""
                INSERT INTO character_state
                    (character_id, current_activity, current_location, activity_started, updated_at)
                VALUES ({ph}, {ph}, {ph}, NOW(), NOW())
                ON CONFLICT (character_id) DO UPDATE SET
                    current_activity = EXCLUDED.current_activity,
                    current_location = EXCLUDED.current_location,
                    activity_started = CASE
                        WHEN character_state.current_activity != EXCLUDED.current_activity
                        THEN NOW()
                        ELSE character_state.activity_started
                    END,
                    updated_at = NOW()
            """, (character_id, activity, location))
        else:
            cursor.execute(f"""
                INSERT INTO character_state (character_id, current_activity, current_location, activity_started, updated_at)
                VALUES ({ph}, {ph}, {ph}, datetime('now','localtime'), datetime('now','localtime'))
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
        self.commit()

    def insert_character_activity_log(self, character_id: str, tick_id: int,
                                       activity: str, time_period: str,
                                       weather_type: str):
        """写入角色活动日志。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"INSERT INTO character_activity_log (character_id, tick_id, activity, time_period, weather_type) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
            (character_id, tick_id, activity, time_period, weather_type)
        )
        self.commit()

    def get_all_characters(self) -> list:
        """获取所有角色 ID 列表。"""
        cursor = self._pg_cursor()
        cursor.execute("SELECT character_id, current_activity, current_location FROM character_state")
        return self._fetchall(cursor)

    def get_recent_world_states(self, limit: int = 10) -> list:
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(f"SELECT * FROM world_state ORDER BY tick_id DESC LIMIT {ph}", (limit,))
        return self._fetchall(cursor)

    def get_recent_world_events(self, limit: int = 50) -> list:
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(f"SELECT * FROM world_events ORDER BY tick_id DESC LIMIT {ph}", (limit,))
        return self._fetchall(cursor)

    # ──────── Phase 2: 自主决策 ────────

    def insert_autonomy_decision(self, tick_id: int, character_id: str,
                                  action_type: str, probability: float,
                                  decision: str, reason: str = None):
        """写入自主决策记录。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"INSERT INTO autonomy_decisions (tick_id, character_id, action_type, probability, decision, reason) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            (tick_id, character_id, action_type, probability, decision, reason)
        )
        self.commit()

    def get_last_autonomy_decision(self, character_id: str) -> dict:
        """获取角色最近一次自主决策。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"SELECT * FROM autonomy_decisions WHERE character_id = {ph} ORDER BY tick_id DESC LIMIT 1",
            (character_id,)
        )
        return self._fetchone(cursor)

    # ──────── Phase 2: 情绪压力 ────────

    def insert_mood_pressure_log(self, tick_id: int, character_id: str,
                                  emotion_type: str, pressure_before: float,
                                  pressure_after: float, delta: float,
                                  trigger: str = "tick"):
        """写入情绪压力日志。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"INSERT INTO mood_pressure_log (tick_id, character_id, emotion_type, pressure_before, pressure_after, delta, trigger) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            (tick_id, character_id, emotion_type, pressure_before, pressure_after, delta, trigger)
        )
        self.commit()

    def get_character_pressures(self, character_id: str) -> dict:
        """获取角色当前所有情绪压力值。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(f"""
            SELECT emotion_type, pressure_after FROM mood_pressure_log
            WHERE character_id = {ph}
            AND id IN (
                SELECT MAX(id) FROM mood_pressure_log
                WHERE character_id = {ph}
                GROUP BY emotion_type
            )
        """, (character_id, character_id))
        return {row["emotion_type"]: row["pressure_after"] for row in cursor.fetchall()}

    # ──────── Phase 2: 缺席 ────────

    def insert_absence_log(self, tick_id: int, inactive_minutes: int,
                            absence_stage: str, effect_summary: str = None):
        """写入缺席记录。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"INSERT INTO absence_log (tick_id, inactive_minutes, absence_stage, effect_summary) VALUES ({ph}, {ph}, {ph}, {ph})",
            (tick_id, inactive_minutes, absence_stage, effect_summary)
        )
        self.commit()

    def get_last_absence_log(self) -> dict:
        """获取最近一次缺席记录。"""
        cursor = self._pg_cursor()
        cursor.execute("SELECT * FROM absence_log ORDER BY tick_id DESC LIMIT 1")
        return self._fetchone(cursor)

    # ──────── Phase 2: 反馈事件 ────────

    def insert_feedback_event(self, tick_id: int = None, character_id: str = None,
                               action_type: str = None, action_target: str = "user",
                               intent: str = None, confidence: float = 0.0,
                               priority: int = 0, execution_status: str = "executed",
                               user_response: str = "none",
                               emotion_delta: dict = None, relationship_delta: dict = None,
                               emotion_delta_json: str = "{}",
                               relationship_delta_json: str = "{}",
                               memory_entry: str = None, score: float = None,
                               memory_record: str = None, world_affect: dict = None):
        """写入反馈事件记录。

        兼容两套调用方式：
        - FeedbackLoop：传 tick_id=None（自动获取），emotion_delta/relationship_delta dict
        - 原始调用：传 emotion_delta_json/relationship_delta_json 字符串
        """
        if tick_id is None:
            tick_id = self.get_tick_id()

        if emotion_delta is not None:
            emotion_delta_json = json.dumps(emotion_delta, ensure_ascii=False)
        if relationship_delta is not None:
            relationship_delta_json = json.dumps(relationship_delta, ensure_ascii=False)

        effective_confidence = confidence if score is None else score / 100.0
        effective_memory = memory_entry or memory_record

        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(f"""
            INSERT INTO feedback_events
                (tick_id, character_id, action_type, action_target, intent,
                 confidence, priority, execution_status, user_response,
                 emotion_delta_json, relationship_delta_json, memory_entry)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (tick_id, character_id, action_type, action_target, intent,
              effective_confidence, priority, execution_status, user_response,
              emotion_delta_json, relationship_delta_json, effective_memory))
        self.commit()

    def get_recent_feedback_events(self, character_id: str = None,
                                    limit: int = 50) -> list:
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        if character_id:
            cursor.execute(
                f"SELECT * FROM feedback_events WHERE character_id = {ph} ORDER BY tick_id DESC LIMIT {ph}",
                (character_id, limit)
            )
        else:
            cursor.execute(f"SELECT * FROM feedback_events ORDER BY tick_id DESC LIMIT {ph}", (limit,))
        return self._fetchall(cursor)

    def get_action_last_occurrence(self, character_id: str,
                                    action_type: str) -> str:
        """获取角色某行为类型最后一次发生的时间。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"SELECT created_at FROM feedback_events WHERE character_id = {ph} AND action_type = {ph} ORDER BY created_at DESC LIMIT 1",
            (character_id, action_type)
        )
        row = self._fetchone(cursor)
        return row["created_at"] if row else None

    # ══════════════════════════════════════════════════
    # V4 新增 — Emotion Snapshots
    # ══════════════════════════════════════════════════

    def insert_emotion_snapshot(self, character_id: str, tick_id: int,
                                 emotions: dict, pressures: dict,
                                 dominant: str = "calm",
                                 absence_hours: float = 0.0):
        """写入情绪快照。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        json_args = (
            json.dumps(emotions, ensure_ascii=False),
            json.dumps(pressures, ensure_ascii=False),
        )
        cursor.execute(f"""
            INSERT INTO emotion_snapshots
                (character_id, tick_id, emotions_json, pressures_json, dominant, absence_hours)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (character_id, tick_id, *json_args, dominant, absence_hours))
        self.commit()

    def get_latest_emotion_snapshot(self, character_id: str) -> dict:
        """获取角色最近一次情绪快照。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"SELECT * FROM emotion_snapshots WHERE character_id = {ph} ORDER BY tick_id DESC LIMIT 1",
            (character_id,)
        )
        return self._fetchone(cursor)

    # ══════════════════════════════════════════════════
    # V4 新增 — Relationship Snapshots
    # ══════════════════════════════════════════════════

    def insert_relationship_snapshot(self, character_id: str, tick_id: int,
                                      attachment: float = 0, trust: float = 50,
                                      intimacy: float = 0, warmth: float = 50):
        """写入关系快照。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(f"""
            INSERT INTO relationship_snapshots
                (character_id, tick_id, attachment, trust, intimacy, warmth)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (character_id, tick_id, attachment, trust, intimacy, warmth))
        self.commit()

    def get_latest_relationship_snapshot(self, character_id: str) -> dict:
        """获取角色最近一次关系快照。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"SELECT * FROM relationship_snapshots WHERE character_id = {ph} ORDER BY tick_id DESC LIMIT 1",
            (character_id,)
        )
        return self._fetchone(cursor)

    # ══════════════════════════════════════════════════
    # V4 新增 — Memory Items (8 types)
    # ══════════════════════════════════════════════════

    def insert_memory_item(self, character_id: str, user_id: str = "default_user",
                            memory_type: str = "short", content: str = "",
                            summary: str = "", emotion_tags: list = None,
                            importance: float = 0.5, intensity: float = 0.5,
                            source: str = "system", metadata: dict = None) -> int:
        """插入记忆条目，返回 id。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        ph = "%s" if pg else "?"

        tags = json.dumps(emotion_tags or [], ensure_ascii=False)
        meta = json.dumps(metadata or {}, ensure_ascii=False)

        if pg:
            cursor.execute(f"""
                INSERT INTO memory_items
                    (character_id, user_id, memory_type, content, summary,
                     emotion_tags, importance, intensity, source, metadata_json)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                RETURNING id
            """, (character_id, user_id, memory_type, content, summary,
                  tags, importance, intensity, source, meta))
            item_id = cursor.fetchone()["id"]
        else:
            cursor.execute(f"""
                INSERT INTO memory_items
                    (character_id, user_id, memory_type, content, summary,
                     emotion_tags, importance, intensity, source, metadata_json)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (character_id, user_id, memory_type, content, summary,
                  tags, importance, intensity, source, meta))
            item_id = cursor.lastrowid
        self.commit()
        return item_id

    def get_memories_by_character(self, character_id: str,
                                   memory_type: str = None,
                                   limit: int = 50) -> list:
        """获取角色记忆。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        if memory_type:
            cursor.execute(f"""
                SELECT * FROM memory_items
                WHERE character_id = {ph} AND memory_type = {ph}
                ORDER BY importance DESC, created_at DESC
                LIMIT {ph}
            """, (character_id, memory_type, limit))
        else:
            cursor.execute(f"""
                SELECT * FROM memory_items
                WHERE character_id = {ph}
                ORDER BY importance DESC, created_at DESC
                LIMIT {ph}
            """, (character_id, limit))
        return self._fetchall(cursor)

    def search_memories(self, character_id: str, keywords: list = None,
                         emotion_tags: list = None, limit: int = 20) -> list:
        """关键词/情绪标签搜索记忆。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        conditions = [f"character_id = {ph}"]
        params = [character_id]

        if keywords:
            for kw in keywords:
                conditions.append(f"content LIKE {ph}")
                params.append(f"%{kw}%")

        if emotion_tags:
            for tag in emotion_tags:
                conditions.append(f"emotion_tags LIKE {ph}")
                params.append(f"%{tag}%")

        where = " AND ".join(conditions)
        cursor.execute(f"""
            SELECT * FROM memory_items WHERE {where}
            ORDER BY importance DESC, created_at DESC LIMIT {ph}
        """, (*params, limit))
        return self._fetchall(cursor)

    def update_memory_access(self, memory_id: int):
        """更新记忆访问计数和访问时间。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        ph = "%s" if pg else "?"
        now_expr = "NOW()" if pg else "datetime('now','localtime')"
        cursor.execute(f"""
            UPDATE memory_items SET access_count = access_count + 1,
            last_accessed = {now_expr} WHERE id = {ph}
        """, (memory_id,))
        self.commit()

    def delete_low_importance_memories(self, character_id: str,
                                        threshold: float = 0.1,
                                        older_than_days: int = 30):
        """清理低重要性旧记忆。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        ph = "%s" if pg else "?"
        if pg:
            cursor.execute(f"""
                DELETE FROM memory_items
                WHERE character_id = {ph}
                  AND importance < {ph}
                  AND memory_type = 'short'
                  AND created_at < NOW() - INTERVAL '{older_than_days} days'
            """, (character_id, threshold))
        else:
            cursor.execute(f"""
                DELETE FROM memory_items
                WHERE character_id = {ph}
                  AND importance < {ph}
                  AND memory_type = 'short'
                  AND created_at < datetime('now', 'localtime', '-{older_than_days} days')
            """, (character_id, threshold))
        self.commit()

    # ══════════════════════════════════════════════════
    # V4 新增 — Diary Entries
    # ══════════════════════════════════════════════════

    def insert_diary_entry(self, character_id: str, entry_date: str,
                            title: str, content: str, mood: str = "neutral",
                            weather: str = None, key_events: list = None):
        """写入日记条目。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        events = json.dumps(key_events or [], ensure_ascii=False)
        cursor.execute(f"""
            INSERT INTO diary_entries (character_id, entry_date, title, content, mood, weather, key_events)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (character_id, entry_date, title, content, mood, weather, events))
        self.commit()

    def get_diary_entries(self, character_id: str = None,
                            limit: int = 30) -> list:
        """获取日记条目。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        if character_id:
            cursor.execute(f"""
                SELECT * FROM diary_entries WHERE character_id = {ph}
                ORDER BY entry_date DESC LIMIT {ph}
            """, (character_id, limit))
        else:
            cursor.execute(f"SELECT * FROM diary_entries ORDER BY entry_date DESC LIMIT {ph}", (limit,))
        return self._fetchall(cursor)

    # ══════════════════════════════════════════════════
    # V4 新增 — Calendar Events
    # ══════════════════════════════════════════════════

    def insert_calendar_event(self, character_id: str, event_type: str,
                               event_name: str, event_date: str,
                               repeat_yearly: bool = False,
                               emotional_impact: dict = None):
        """插入日历事件（节日/纪念日）。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        impact = json.dumps(emotional_impact or {}, ensure_ascii=False)
        cursor.execute(f"""
            INSERT INTO calendar_events (character_id, event_type, event_name, event_date, repeat_yearly, emotional_impact)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (character_id, event_type, event_name, event_date, 1 if repeat_yearly else 0, impact))
        self.commit()

    def get_anniversaries_for_date(self, target_date) -> list:
        """获取指定日期的周年事件。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        date_str = str(target_date)
        cursor.execute(f"""
            SELECT * FROM calendar_events
            WHERE event_date = {ph} OR (repeat_yearly = 1 AND substr(event_date, 6) = substr({ph}, 6))
        """, (date_str, date_str))
        return self._fetchall(cursor)

    def get_upcoming_calendar_events(self, days: int = 7) -> list:
        """获取近期日历事件。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        if pg:
            cursor.execute(f"""
                SELECT * FROM calendar_events
                WHERE event_date BETWEEN CURRENT_DATE::text AND (CURRENT_DATE + INTERVAL '%s days')::text
                ORDER BY event_date
            """, (days,))
        else:
            cursor.execute(f"""
                SELECT * FROM calendar_events
                WHERE event_date BETWEEN date('now', 'localtime') AND date('now', 'localtime', '+{days} days')
                ORDER BY event_date
            """)
        return self._fetchall(cursor)
