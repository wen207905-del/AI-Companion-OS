-- V4.1: 用户运行时模式（聊天 / 叙述）

CREATE TABLE IF NOT EXISTS user_runtime_settings (
    user_id TEXT PRIMARY KEY DEFAULT 'default',
    current_mode TEXT NOT NULL DEFAULT 'chat',
    active_character_id TEXT,
    scene_style TEXT DEFAULT '',
    updated_at REAL NOT NULL
);

INSERT OR IGNORE INTO user_runtime_settings (user_id, current_mode, updated_at)
VALUES ('default', 'chat', unixepoch());
