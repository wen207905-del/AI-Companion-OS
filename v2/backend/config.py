"""
全局配置管理：加载环境变量、角色YAML、数据库初始化
"""
import os
import yaml
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
PERSONA_DIR = CONFIG_DIR / "personas"
USER_PROFILE_PATH = CONFIG_DIR / "user.yaml"
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "companion.db"

APP_VERSION = "2.3.0"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv(
    "QWEN_BASE_URL",
    "https://ws-hzh7mdnpcm0fjcrc.cn-beijing.maas.aliyuncs.com",
)
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3.7-plus")

# LLM 路由：main=私聊主对话，aux=群聊决策/内心独白等辅助任务
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").lower()
LLM_MODEL = os.getenv("LLM_MODEL", DEEPSEEK_MODEL)
LLM_AUX_PROVIDER = os.getenv("LLM_AUX_PROVIDER", "deepseek").lower()
LLM_AUX_MODEL = os.getenv("LLM_AUX_MODEL", "deepseek-chat")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.85"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))
# 私聊自适应长度预算；明确场景展开可再单独提高
LLM_PRIVATE_MAX_TOKENS = int(os.getenv("LLM_PRIVATE_MAX_TOKENS", "1536"))
STYLE_REFERENCE_ENABLED = os.getenv("STYLE_REFERENCE_ENABLED", "false").lower() in ("1", "true", "yes")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))
LLM_STREAM = os.getenv("LLM_STREAM", "true").lower() in ("1", "true", "yes")

# standard=默认安全提示；unrestricted=私聊无审查角色扮演
CONTENT_MODE = os.getenv("CONTENT_MODE", "unrestricted").lower()

# 内心独白（第二次 LLM 调用；默认关闭以降低延迟）
LLM_INNER_THOUGHT = os.getenv("LLM_INNER_THOUGHT", "false").lower() in ("1", "true", "yes")

# 用户可见聊天/叙述模式切换；关闭后忽略持久化模式，仅兼容旧客户端显式 mode 字段
ENABLE_MANUAL_MODE = os.getenv("ENABLE_MANUAL_MODE", "false").lower() in ("1", "true", "yes")

# V4.2 P0 群聊止血开关（默认偏止血开启，可用环境变量逐项回退）
def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


GROUP_SKIP_EXPAND = _env_bool("GROUP_SKIP_EXPAND", "true")
PRIVATE_SKIP_EXPAND = _env_bool("PRIVATE_SKIP_EXPAND", "true")
GROUP_MAX_RESPONDERS = max(1, int(os.getenv("GROUP_MAX_RESPONDERS", "1")))
GROUP_CHAIN_ENABLED = _env_bool("GROUP_CHAIN_ENABLED", "false")
GROUP_PRIVATE_BRIDGE_ENABLED = _env_bool("GROUP_PRIVATE_BRIDGE_ENABLED", "false")
GROUP_PRIVATE_MEMORY_IN_PROMPT = _env_bool("GROUP_PRIVATE_MEMORY_IN_PROMPT", "false")
# 只告诉角色“近期私聊发生过、延续当前态度”，绝不注入私聊正文
GROUP_PRIVATE_CONTINUITY_ENABLED = _env_bool("GROUP_PRIVATE_CONTINUITY_ENABLED", "true")
GROUP_MAX_REPLY_CHARS = int(os.getenv("GROUP_MAX_REPLY_CHARS", "450"))
GROUP_MAX_TOKENS = int(os.getenv("GROUP_MAX_TOKENS", "700"))
GROUP_TEMPERATURE = float(os.getenv("GROUP_TEMPERATURE", "0.75"))

# CORS：非空时按逗号分隔白名单；空则保持 allow_origins=["*"]
_cors_raw = (os.getenv("CORS_ALLOW_ORIGINS") or "").strip()
CORS_ALLOW_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else []

SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# 确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_user_profile() -> dict:
    """加载用户档案 YAML（config/user.yaml）。"""
    if not USER_PROFILE_PATH.exists():
        return {}
    with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


_user_profile = load_user_profile()
USER_NAME = os.getenv("USER_NAME") or _user_profile.get("name") or "许汉文"
USER_NICKNAME = os.getenv("USER_NICKNAME") or _user_profile.get("nickname") or USER_NAME


def load_all_personas():
    """加载所有角色 YAML 配置"""
    personas = {}
    if not PERSONA_DIR.exists():
        return personas
    for yaml_file in PERSONA_DIR.glob("*.yaml"):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            personas[data["id"]] = data
    return personas


def get_db():
    """获取 SQLite 连接（WAL 模式，允许多线程访问）"""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn):
    """初始化数据库表"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS event_log (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            timestamp REAL NOT NULL,
            participants TEXT NOT NULL,
            raw_input TEXT,
            analysis_result TEXT NOT NULL,
            memory_snapshot TEXT,
            weight INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS relationship_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            love REAL DEFAULT 0, trust REAL DEFAULT 0, attachment REAL DEFAULT 0,
            respect REAL DEFAULT 0, security REAL DEFAULT 0,
            possessiveness REAL DEFAULT 0, jealousy REAL DEFAULT 0,
            intimacy_emotional REAL DEFAULT 0, intimacy_physical REAL DEFAULT 0,
            stage INTEGER DEFAULT 1,
            timestamp REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS emotion_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT NOT NULL,
            event_id TEXT,
            happy REAL DEFAULT 50, calm REAL DEFAULT 50, stressed REAL DEFAULT 20,
            tired REAL DEFAULT 20, lonely REAL DEFAULT 15, excited REAL DEFAULT 10,
            embarrassed REAL DEFAULT 0, shy REAL DEFAULT 20, suspicious REAL DEFAULT 5,
            sad REAL DEFAULT 5, angry REAL DEFAULT 5, fearful REAL DEFAULT 5,
            miss_user REAL DEFAULT 20, jealous REAL DEFAULT 0,
            activity TEXT DEFAULT '', delta_json TEXT DEFAULT '',
            timestamp REAL NOT NULL
        );

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

        CREATE TABLE IF NOT EXISTS group_chats (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            type TEXT DEFAULT 'custom', created_at REAL NOT NULL,
            mode TEXT DEFAULT 'free', archived INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS group_chat_members (
            chat_id TEXT NOT NULL, character_id TEXT NOT NULL,
            joined_at REAL NOT NULL, PRIMARY KEY (chat_id, character_id)
        );

        CREATE TABLE IF NOT EXISTS group_messages (
            id TEXT PRIMARY KEY, chat_id TEXT NOT NULL,
            sender_type TEXT NOT NULL, sender_id TEXT NOT NULL,
            content TEXT NOT NULL, action TEXT, inner_thought TEXT,
            content_type TEXT DEFAULT 'text', timestamp REAL NOT NULL,
            edited INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS private_messages (
            id TEXT PRIMARY KEY, character_id TEXT NOT NULL,
            sender_type TEXT NOT NULL, content TEXT NOT NULL,
            action TEXT, inner_thought TEXT,
            content_type TEXT DEFAULT 'text', timestamp REAL NOT NULL,
            edited INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS diary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT NOT NULL, date TEXT NOT NULL,
            content TEXT NOT NULL, mood TEXT, timestamp REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS timeline_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT NOT NULL, event_name TEXT NOT NULL,
            description TEXT, event_date TEXT NOT NULL,
            event_type TEXT, timestamp REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_event_character ON event_log(participants);
        CREATE INDEX IF NOT EXISTS idx_relation_character ON relationship_snapshot(character_id);
        CREATE INDEX IF NOT EXISTS idx_emotion_character ON emotion_snapshot(character_id);
        CREATE INDEX IF NOT EXISTS idx_group_msgs ON group_messages(chat_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_private_msgs ON private_messages(character_id, timestamp);

        CREATE TABLE IF NOT EXISTS character_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT NOT NULL,
            scope TEXT NOT NULL DEFAULT 'private',
            scope_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            memory_type TEXT DEFAULT 'episodic',
            intensity REAL DEFAULT 50,
            timestamp REAL NOT NULL,
            event_id TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_char_memories
            ON character_memories(character_id, scope, scope_id, timestamp);

        CREATE TABLE IF NOT EXISTS character_growth (
            character_id TEXT PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            milestones TEXT DEFAULT '[]',
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS image_albums (
            job_id TEXT PRIMARY KEY,
            character_id TEXT NOT NULL,
            url TEXT NOT NULL DEFAULT '',
            prompt TEXT NOT NULL,
            model TEXT NOT NULL,
            scene TEXT DEFAULT '',
            style TEXT DEFAULT '',
            status TEXT DEFAULT 'queued',
            meta TEXT DEFAULT '{}',
            created_at REAL NOT NULL,
            updated_at REAL,
            progress_text TEXT DEFAULT '',
            trigger_type TEXT DEFAULT '',
            attempt_count INTEGER DEFAULT 0,
            error_message TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_image_albums_char
            ON image_albums(character_id, created_at DESC);

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

        CREATE TABLE IF NOT EXISTS user_runtime_settings (
            user_id TEXT PRIMARY KEY DEFAULT 'default',
            current_mode TEXT NOT NULL DEFAULT 'chat',
            active_character_id TEXT,
            scene_style TEXT DEFAULT '',
            updated_at REAL NOT NULL
        );

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

        CREATE TABLE IF NOT EXISTS character_dm_messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            speaker_id TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_dm_msg_conv
            ON character_dm_messages(conversation_id, timestamp ASC);

        CREATE TABLE IF NOT EXISTS game_sessions (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            game_type TEXT NOT NULL,
            rules_version TEXT NOT NULL DEFAULT '1.0',
            status TEXT NOT NULL DEFAULT 'running',
            round_no INTEGER NOT NULL DEFAULT 1,
            current_turn_index INTEGER NOT NULL DEFAULT 0,
            state_version INTEGER NOT NULL DEFAULT 1,
            settings_json TEXT NOT NULL DEFAULT '{}',
            public_state_json TEXT NOT NULL DEFAULT '{}',
            winner_json TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            finished_at REAL
        );

        CREATE INDEX IF NOT EXISTS idx_game_session_group
            ON game_sessions(group_id, updated_at DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_one_running_game_per_group
            ON game_sessions(group_id) WHERE status = 'running';

        CREATE TABLE IF NOT EXISTS game_participants (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            participant_type TEXT NOT NULL,
            participant_ref_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            seat_no INTEGER NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            UNIQUE(session_id, participant_ref_id),
            UNIQUE(session_id, seat_no)
        );

        CREATE INDEX IF NOT EXISTS idx_game_participant_session
            ON game_participants(session_id, seat_no ASC);

        CREATE TABLE IF NOT EXISTS game_events (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            sequence_no INTEGER NOT NULL,
            actor_ref_id TEXT,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            state_version_after INTEGER NOT NULL,
            idempotency_key TEXT,
            created_at REAL NOT NULL,
            UNIQUE(session_id, sequence_no),
            UNIQUE(session_id, idempotency_key)
        );

        CREATE INDEX IF NOT EXISTS idx_game_event_session
            ON game_events(session_id, sequence_no ASC);
    """)
    conn.commit()
