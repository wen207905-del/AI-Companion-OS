-- V4.1: 角色私聊 + 角色间关系

CREATE TABLE IF NOT EXISTS character_character_relation (
    from_character_id TEXT NOT NULL,
    to_character_id TEXT NOT NULL,
    relation_label TEXT DEFAULT '熟识',
    familiarity REAL DEFAULT 50,
    trust REAL DEFAULT 50,
    affinity REAL DEFAULT 50,
    rivalry REAL DEFAULT 0,
    jealousy REAL DEFAULT 0,
    respect REAL DEFAULT 50,
    protectiveness REAL DEFAULT 30,
    last_dm_at REAL DEFAULT 0,
    updated_at REAL NOT NULL,
    PRIMARY KEY (from_character_id, to_character_id)
);

CREATE TABLE IF NOT EXISTS character_dm_conversation (
    id TEXT PRIMARY KEY,
    character_a TEXT NOT NULL,
    character_b TEXT NOT NULL,
    initiator_id TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    trigger_reason TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    last_message_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dm_conv_updated
    ON character_dm_conversation(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_dm_conv_status
    ON character_dm_conversation(status, last_message_at DESC);

CREATE TABLE IF NOT EXISTS character_dm_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    speaker_id TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dm_msg_conv
    ON character_dm_messages(conversation_id, timestamp ASC);
