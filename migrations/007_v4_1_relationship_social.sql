-- V4.1: 用户与角色社会关系 + 好感等级（与 relationship_snapshot 并存）

CREATE TABLE IF NOT EXISTS character_user_relation (
    character_id TEXT PRIMARY KEY,
    social_relation_type TEXT NOT NULL,
    social_relation_label TEXT NOT NULL,
    affection_score REAL NOT NULL,
    affection_grade TEXT NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'romance',
    current_activity TEXT DEFAULT '日常',
    current_addressing_style TEXT DEFAULT '',
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_char_user_relation_grade
    ON character_user_relation(affection_grade);
