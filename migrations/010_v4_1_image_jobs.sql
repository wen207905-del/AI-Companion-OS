-- V4.1: 生图任务状态扩展

ALTER TABLE image_albums ADD COLUMN updated_at REAL;
ALTER TABLE image_albums ADD COLUMN progress_text TEXT DEFAULT '';
ALTER TABLE image_albums ADD COLUMN trigger_type TEXT DEFAULT '';
ALTER TABLE image_albums ADD COLUMN attempt_count INTEGER DEFAULT 0;
ALTER TABLE image_albums ADD COLUMN error_message TEXT DEFAULT '';

UPDATE image_albums SET updated_at = created_at WHERE updated_at IS NULL;
