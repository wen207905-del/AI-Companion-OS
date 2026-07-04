"""V3 database repository operations."""

import json
from typing import Optional


class RepositoryMixin:
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

    # ══════════════════════════════════════════════════
    # V4 新增 — Life Loop Ticks
    # ══════════════════════════════════════════════════

    def _create_v4_tables(self):
        """创建 V4 新增表（desires / intentions / social_relations / attachment_states
        / life_loop_ticks / visual_profiles / albums / world_events_v4）。"""
        self._execute("""
            CREATE TABLE IF NOT EXISTS life_loop_ticks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id         TEXT    NOT NULL,
                state           TEXT    DEFAULT 'running',
                tick_count      INTEGER DEFAULT 0,
                duration_ms     REAL    DEFAULT 0,
                error_count     INTEGER DEFAULT 0,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS desires (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                desire_to_connect   REAL DEFAULT 30,
                desire_to_express   REAL DEFAULT 20,
                desire_to_avoid     REAL DEFAULT 5,
                desire_to_comfort   REAL DEFAULT 15,
                desire_to_compete   REAL DEFAULT 5,
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS intentions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                intention_type  TEXT    NOT NULL,
                strength        REAL    DEFAULT 0.1,
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                UNIQUE(character_id, intention_type)
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS social_relations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id         TEXT    NOT NULL,
                to_id           TEXT    NOT NULL,
                value           REAL    DEFAULT 0,
                rel_type        TEXT    DEFAULT 'neutral',
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                UNIQUE(from_id, to_id)
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS attachment_states (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL UNIQUE,
                attachment_style TEXT   DEFAULT 'secure',
                attachment_level REAL   DEFAULT 30,
                trust_level     REAL    DEFAULT 40,
                jealousy_level  REAL    DEFAULT 0,
                last_interaction TEXT,
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS visual_profiles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL UNIQUE,
                profile_data    TEXT    NOT NULL DEFAULT '{}',
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS albums (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id    TEXT    NOT NULL,
                image_path      TEXT    NOT NULL,
                prompt          TEXT    DEFAULT '',
                style           TEXT    DEFAULT 'selfie',
                scene           TEXT    DEFAULT 'bedroom',
                emotion_tag     TEXT,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        self._execute("""
            CREATE TABLE IF NOT EXISTS world_events_v4 (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name      TEXT    NOT NULL,
                event_type      TEXT    NOT NULL,
                intensity       REAL    DEFAULT 0.5,
                emotion_bias_json TEXT   DEFAULT '{}',
                remaining_ticks INTEGER DEFAULT 0,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # 索引
        self._execute("CREATE INDEX IF NOT EXISTS idx_llt_tick ON life_loop_ticks(tick_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_des_char ON desires(character_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_int_char ON intentions(character_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_sr_from ON social_relations(from_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_sr_to ON social_relations(to_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_ast_char ON attachment_states(character_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_vp_char ON visual_profiles(character_id)")
        self._execute("CREATE INDEX IF NOT EXISTS idx_alb_char ON albums(character_id)")

        self.commit()

    # ── Desires CRUD ──

    def insert_desire_snapshot(self, character_id: str, desires: dict):
        """写入/更新欲望快照。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        ph = "%s" if pg else "?"
        now = "NOW()" if pg else "datetime('now','localtime')"
        if pg:
            cursor.execute(f"""
                INSERT INTO desires (character_id, desire_to_connect, desire_to_express,
                    desire_to_avoid, desire_to_comfort, desire_to_compete, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {now})
                ON CONFLICT (character_id) DO UPDATE SET
                    desire_to_connect = EXCLUDED.desire_to_connect,
                    desire_to_express = EXCLUDED.desire_to_express,
                    desire_to_avoid = EXCLUDED.desire_to_avoid,
                    desire_to_comfort = EXCLUDED.desire_to_comfort,
                    desire_to_compete = EXCLUDED.desire_to_compete,
                    updated_at = {now}
            """, (character_id, desires.get("desire_to_connect", 30),
                  desires.get("desire_to_express", 20), desires.get("desire_to_avoid", 5),
                  desires.get("desire_to_comfort", 15), desires.get("desire_to_compete", 5)))
        else:
            # SQLite UPSERT
            cursor.execute(f"""
                INSERT INTO desires (character_id, desire_to_connect, desire_to_express,
                    desire_to_avoid, desire_to_comfort, desire_to_compete, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {now})
                ON CONFLICT(character_id) DO UPDATE SET
                    desire_to_connect = excluded.desire_to_connect,
                    desire_to_express = excluded.desire_to_express,
                    desire_to_avoid = excluded.desire_to_avoid,
                    desire_to_comfort = excluded.desire_to_comfort,
                    desire_to_compete = excluded.desire_to_compete,
                    updated_at = {now}
            """, (character_id, desires.get("desire_to_connect", 30),
                  desires.get("desire_to_express", 20), desires.get("desire_to_avoid", 5),
                  desires.get("desire_to_comfort", 15), desires.get("desire_to_compete", 5)))
        self.commit()

    def get_desires(self, character_id: str) -> dict:
        """获取角色当前欲望。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"SELECT * FROM desires WHERE character_id = {ph} ORDER BY updated_at DESC LIMIT 1",
            (character_id,)
        )
        row = self._fetchone(cursor)
        if row:
            return {
                "desire_to_connect": row.get("desire_to_connect", 30),
                "desire_to_express": row.get("desire_to_express", 20),
                "desire_to_avoid": row.get("desire_to_avoid", 5),
                "desire_to_comfort": row.get("desire_to_comfort", 15),
                "desire_to_compete": row.get("desire_to_compete", 5),
            }
        return {}

    # ── Intentions CRUD ──

    def get_intentions(self, character_id: str) -> list:
        """获取角色所有意图。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"SELECT intention_type, strength, updated_at FROM intentions WHERE character_id = {ph}",
            (character_id,)
        )
        return self._fetchall(cursor)

    def upsert_intention(self, character_id: str, intention_type: str, strength: float):
        """写入或更新意图。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        ph = "%s" if pg else "?"
        now = "NOW()" if pg else "datetime('now','localtime')"
        if pg:
            cursor.execute(f"""
                INSERT INTO intentions (character_id, intention_type, strength, updated_at)
                VALUES ({ph}, {ph}, {ph}, {now})
                ON CONFLICT (character_id, intention_type) DO UPDATE SET
                    strength = EXCLUDED.strength, updated_at = {now}
            """, (character_id, intention_type, strength))
        else:
            cursor.execute(f"""
                INSERT INTO intentions (character_id, intention_type, strength, updated_at)
                VALUES ({ph}, {ph}, {ph}, {now})
                ON CONFLICT(character_id, intention_type) DO UPDATE SET
                    strength = excluded.strength, updated_at = {now}
            """, (character_id, intention_type, strength))
        self.commit()

    # ── Social Relations CRUD ──

    def upsert_social_relation(self, from_id: str, to_id: str,
                                value: float, rel_type: str = "neutral"):
        """写入或更新社交关系。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        ph = "%s" if pg else "?"
        now = "NOW()" if pg else "datetime('now','localtime')"
        if pg:
            cursor.execute(f"""
                INSERT INTO social_relations (from_id, to_id, value, rel_type, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {now})
                ON CONFLICT (from_id, to_id) DO UPDATE SET
                    value = EXCLUDED.value, rel_type = EXCLUDED.rel_type, updated_at = {now}
            """, (from_id, to_id, value, rel_type))
        else:
            cursor.execute(f"""
                INSERT INTO social_relations (from_id, to_id, value, rel_type, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {now})
                ON CONFLICT(from_id, to_id) DO UPDATE SET
                    value = excluded.value, rel_type = excluded.rel_type, updated_at = {now}
            """, (from_id, to_id, value, rel_type))
        self.commit()

    def get_social_relations(self, character_id: str = None) -> list:
        """获取社交关系。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        if character_id:
            cursor.execute(f"""
                SELECT from_id, to_id, value, rel_type FROM social_relations
                WHERE from_id = {ph} OR to_id = {ph}
                ORDER BY ABS(value) DESC
            """, (character_id, character_id))
        else:
            cursor.execute("SELECT from_id, to_id, value, rel_type FROM social_relations ORDER BY ABS(value) DESC")
        return self._fetchall(cursor)

    # ── Attachment States CRUD ──

    def upsert_attachment_state(self, character_id: str, style: str, state: dict):
        """写入或更新依恋状态。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        ph = "%s" if pg else "?"
        now = "NOW()" if pg else "datetime('now','localtime')"
        if pg:
            cursor.execute(f"""
                INSERT INTO attachment_states (character_id, attachment_style,
                    attachment_level, trust_level, jealousy_level, last_interaction, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {now})
                ON CONFLICT (character_id) DO UPDATE SET
                    attachment_style = EXCLUDED.attachment_style,
                    attachment_level = EXCLUDED.attachment_level,
                    trust_level = EXCLUDED.trust_level,
                    jealousy_level = EXCLUDED.jealousy_level,
                    last_interaction = EXCLUDED.last_interaction,
                    updated_at = {now}
            """, (character_id, style,
                  state.get("attachment_level", 30), state.get("trust_level", 40),
                  state.get("jealousy_level", 0), state.get("last_interaction", "")))
        else:
            cursor.execute(f"""
                INSERT INTO attachment_states (character_id, attachment_style,
                    attachment_level, trust_level, jealousy_level, last_interaction, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {now})
                ON CONFLICT(character_id) DO UPDATE SET
                    attachment_style = excluded.attachment_style,
                    attachment_level = excluded.attachment_level,
                    trust_level = excluded.trust_level,
                    jealousy_level = excluded.jealousy_level,
                    last_interaction = excluded.last_interaction,
                    updated_at = {now}
            """, (character_id, style,
                  state.get("attachment_level", 30), state.get("trust_level", 40),
                  state.get("jealousy_level", 0), state.get("last_interaction", "")))
        self.commit()

    def get_attachment_state(self, character_id: str) -> dict:
        """获取角色依恋状态。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"SELECT * FROM attachment_states WHERE character_id = {ph}",
            (character_id,)
        )
        return self._fetchone(cursor)

    # ── Visual Profiles CRUD ──

    def upsert_visual_profile(self, character_id: str, profile_data: str):
        """写入或更新角色视觉档案。"""
        cursor = self._pg_cursor()
        pg = self._db_type == "postgres"
        ph = "%s" if pg else "?"
        now = "NOW()" if pg else "datetime('now','localtime')"
        if pg:
            cursor.execute(f"""
                INSERT INTO visual_profiles (character_id, profile_data, updated_at)
                VALUES ({ph}, {ph}, {now})
                ON CONFLICT (character_id) DO UPDATE SET
                    profile_data = EXCLUDED.profile_data, updated_at = {now}
            """, (character_id, profile_data))
        else:
            cursor.execute(f"""
                INSERT INTO visual_profiles (character_id, profile_data, updated_at)
                VALUES ({ph}, {ph}, {now})
                ON CONFLICT(character_id) DO UPDATE SET
                    profile_data = excluded.profile_data, updated_at = {now}
            """, (character_id, profile_data))
        self.commit()

    def get_visual_profile(self, character_id: str) -> dict:
        """获取角色视觉档案。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(
            f"SELECT * FROM visual_profiles WHERE character_id = {ph}",
            (character_id,)
        )
        return self._fetchone(cursor)

    # ── Albums CRUD ──

    def insert_album_entry(self, character_id: str, image_path: str,
                            prompt: str = "", style: str = "selfie",
                            scene: str = "bedroom"):
        """插入相册条目。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(f"""
            INSERT INTO albums (character_id, image_path, prompt, style, scene)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
        """, (character_id, image_path, prompt, style, scene))
        self.commit()

    def get_album(self, character_id: str, limit: int = 20) -> list:
        """获取角色相册。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(f"""
            SELECT * FROM albums WHERE character_id = {ph}
            ORDER BY created_at DESC LIMIT {ph}
        """, (character_id, limit))
        return self._fetchall(cursor)

    # ── World Events V4 ──

    def insert_world_event_v4(self, event_name: str, event_type: str,
                               intensity: float = 0.5, emotion_bias: dict = None,
                               remaining_ticks: int = 0):
        """插入 V4 世界事件。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        bias_json = json.dumps(emotion_bias or {}, ensure_ascii=False)
        cursor.execute(f"""
            INSERT INTO world_events_v4 (event_name, event_type, intensity, emotion_bias_json, remaining_ticks)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
        """, (event_name, event_type, intensity, bias_json, remaining_ticks))
        self.commit()

    # ── Autonomy Decision (V4 兼容，无 tick_id) ──

    def insert_autonomy_decision_v4(self, character_id: str, decision: str,
                                     score: float, candidates_json: str = "[]"):
        """写入 V4 自主决策（无 tick_id 版本）。"""
        cursor = self._pg_cursor()
        ph = "%s" if self._db_type == "postgres" else "?"
        cursor.execute(f"""
            INSERT INTO autonomy_decisions (tick_id, character_id, action_type, probability, decision, reason)
            VALUES (0, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (character_id, decision, score / 100.0, candidates_json, decision))
        self.commit()
