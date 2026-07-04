"""V3 database schema creation."""


class SchemaMixin:
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

