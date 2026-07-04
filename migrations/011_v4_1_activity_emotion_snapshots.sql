-- V4.1: 扩展情绪快照 + 活动/增量记录

ALTER TABLE emotion_snapshot ADD COLUMN miss_user REAL DEFAULT 20;
ALTER TABLE emotion_snapshot ADD COLUMN jealous REAL DEFAULT 0;
ALTER TABLE emotion_snapshot ADD COLUMN activity TEXT DEFAULT '';
ALTER TABLE emotion_snapshot ADD COLUMN delta_json TEXT DEFAULT '';

CREATE TABLE IF NOT EXISTS activity_emotion_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id TEXT NOT NULL,
    activity TEXT DEFAULT '',
    happy REAL DEFAULT 50,
    lonely REAL DEFAULT 15,
    miss_user REAL DEFAULT 20,
    primary_mood TEXT DEFAULT '平静',
    delta_json TEXT DEFAULT '{}',
    timestamp REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_activity_emotion_char
    ON activity_emotion_snapshots(character_id, timestamp DESC);
