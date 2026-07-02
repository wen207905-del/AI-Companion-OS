"""
V3 全局配置文件

所有可调参数集中管理，方便后续调参和实验。
Phase 2 完整配置：评分模型权重 / 行为阈值 / 仲裁规则 / 情绪压力 / 缺席系统 / 反馈闭环。
"""

import os

# =============================================================================
# 路径配置
# =============================================================================

# V3 数据库路径
V3_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v3_data.db")

# V2 角色配置目录（personas YAML 文件）
V2_PERSONAS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "personas"
)

# V2 数据库路径（用于读取已有角色数据）
V2_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "companion.db"
)

# =============================================================================
# World Tick 配置
# =============================================================================

# 世界主循环 tick 间隔（秒），默认 5 分钟
TICK_INTERVAL_SECONDS = 300

# 模拟时间加速倍率（1 = 真实时间，0 = 跟随系统时间）
TIME_ACCELERATION_RATIO = 0

# 世界事件最大保留数量
MAX_WORLD_EVENTS = 1000

# =============================================================================
# 时间段定义
# =============================================================================

TIME_PERIODS = {
    "early_morning": {"start": "05:00", "end": "07:59", "label": "凌晨"},
    "morning":       {"start": "08:00", "end": "10:59", "label": "上午"},
    "noon":          {"start": "11:00", "end": "13:59", "label": "中午"},
    "afternoon":     {"start": "14:00", "end": "17:59", "label": "下午"},
    "evening":       {"start": "18:00", "end": "21:59", "label": "傍晚"},
    "night":         {"start": "22:00", "end": "23:59", "label": "夜晚"},
    "late_night":    {"start": "00:00", "end": "04:59", "label": "深夜"},
}

# 每个时间段的默认角色活动
DEFAULT_ACTIVITIES_BY_PERIOD = {
    "early_morning": ["起床", "洗漱", "做早餐", "晨练", "听音乐"],
    "morning":       ["工作", "学习", "看书", "画画", "散步"],
    "noon":          ["吃午饭", "午休", "看剧", "听音乐", "逛街"],
    "afternoon":     ["工作", "学习", "看书", "画画", "喝下午茶"],
    "evening":       ["做晚饭", "看剧", "运动", "和朋友聊天", "写日记"],
    "night":         ["洗漱", "看书", "听音乐", "看手机", "写日记"],
    "late_night":    ["睡觉", "失眠看手机", "听歌发呆", "刷视频"],
}

# 时间段对主动聊天的概率修正
PERIOD_CHAT_BIAS = {
    "early_morning": 0.10,
    "morning":       0.08,
    "noon":          0.10,
    "afternoon":     0.12,
    "evening":       0.18,
    "night":         0.22,
    "late_night":    0.20,
}

# =============================================================================
# 天气系统配置
# =============================================================================

WEATHER_TYPES = {
    "sunny":           {"mood_bias": "happy",     "temperature_range": (20, 35), "label": "晴天"},
    "cloudy":          {"mood_bias": "neutral",   "temperature_range": (15, 28), "label": "多云"},
    "overcast":        {"mood_bias": "calm",      "temperature_range": (12, 25), "label": "阴天"},
    "rainy":           {"mood_bias": "melancholic","temperature_range": (10, 22), "label": "雨天"},
    "heavy_rain":      {"mood_bias": "melancholic","temperature_range": (8, 18),  "label": "大雨"},
    "stormy":          {"mood_bias": "restless",  "temperature_range": (5, 18),   "label": "暴风雨"},
    "foggy":           {"mood_bias": "quiet",     "temperature_range": (8, 20),   "label": "雾天"},
    "snowy":           {"mood_bias": "romantic",  "temperature_range": (-5, 5),   "label": "雪天"},
}

WEATHER_TRANSITION_PROBABILITY = 0.15

WEATHER_TRANSITION_WEIGHTS = {
    "sunny":      {"cloudy": 30, "overcast": 10, "rainy": 5, "foggy": 5},
    "cloudy":     {"sunny": 30, "overcast": 20, "rainy": 15, "foggy": 10},
    "overcast":   {"cloudy": 20, "rainy": 25, "foggy": 15, "sunny": 10},
    "rainy":      {"overcast": 25, "cloudy": 20, "heavy_rain": 15, "sunny": 10},
    "heavy_rain": {"rainy": 30, "overcast": 20, "stormy": 15, "cloudy": 10},
    "stormy":     {"heavy_rain": 25, "rainy": 25, "overcast": 15, "cloudy": 10},
    "foggy":      {"sunny": 25, "cloudy": 25, "overcast": 15, "rainy": 10},
    "snowy":      {"cloudy": 30, "overcast": 20, "sunny": 15, "foggy": 10},
}

WEATHER_EMOTION_EFFECTS = {
    "sunny":      {"happy": 8, "activity_level": 10, "lonely": -5},
    "cloudy":     {"calm": 5, "happy": 2, "activity_level": 2},
    "overcast":   {"calm": 8, "sleepy": 5, "happy": -3},
    "rainy":      {"lonely": 5, "calm": 8, "desire_to_chat": 10, "sleepy": 5},
    "heavy_rain": {"lonely": 10, "calm": 10, "anxiety": 5, "desire_to_chat": 15},
    "stormy":     {"anxiety": 10, "lonely": 10, "restless": 10},
    "foggy":      {"calm": 10, "sleepy": 10, "mysterious": 5},
    "snowy":      {"romantic": 10, "happy": 5, "calm": 5, "lonely": 3},
}

WEATHER_SELFIE_BIAS = {
    "sunny":      0.05,
    "cloudy":     0.00,
    "overcast":   0.02,
    "rainy":      0.15,
    "heavy_rain": 0.12,
    "stormy":     0.03,
    "foggy":      0.05,
    "snowy":      0.10,
}

# =============================================================================
# 环境 / 季节定义
# =============================================================================

SEASONS = {
    "spring": {"months": [3, 4, 5],  "base_temperature": 18, "label": "春天"},
    "summer": {"months": [6, 7, 8],  "base_temperature": 30, "label": "夏天"},
    "autumn": {"months": [9, 10, 11],"base_temperature": 20, "label": "秋天"},
    "winter": {"months": [12, 1, 2], "base_temperature": 5,  "label": "冬天"},
}

# =============================================================================
# Phase 2: 自主行为引擎配置
# =============================================================================

# ── 评分模型权重 ──
# score = emotion.lonely*0.25 + relationship.attachment*0.2
#       + world.night_factor*0.15 + user.inactive_time*0.2
#       + personality.initiative*0.1 + memory.triggers*0.1
PHASE2_SCORE_WEIGHTS = {
    "emotion_lonely":         0.25,
    "relationship_attachment": 0.20,
    "world_night_factor":     0.15,
    "user_inactive_time":     0.20,
    "personality_initiative": 0.10,
    "memory_triggers":        0.10,
}

# ── 行为阈值区间 ──
PHASE2_THRESHOLD_RANGES = {
    "silence":            {"min": 0,   "max": 30,  "action": "SILENCE"},
    "low_chance_message": {"min": 30,  "max": 60,  "action": "SEND_MESSAGE", "probability": 0.3},
    "message_or_diary":   {"min": 60,  "max": 80,  "action": "SEND_MESSAGE | WRITE_DIARY"},
    "message_with_image": {"min": 80,  "max": 90,  "action": "SEND_MESSAGE", "allow_image": True},
    "proactive_event":    {"min": 90,  "max": 100, "action": "RELATIONSHIP_EVENT | GROUP_INTERACTION"},
}

# ── Phase 2 行为类型 ──
PHASE2_ACTION_TYPES = [
    "SEND_MESSAGE",
    "SEND_IMAGE",
    "WRITE_DIARY",
    "UPDATE_MEMORY",
    "RELATIONSHIP_EVENT",
    "GROUP_INTERACTION",
    "SILENCE",
]

# ── Phase 2 行为冷却时间（秒） ──
PHASE2_ACTION_COOLDOWNS = {
    "SEND_MESSAGE":        1800,
    "SEND_IMAGE":          5400,
    "WRITE_DIARY":         7200,
    "UPDATE_MEMORY":       3600,
    "RELATIONSHIP_EVENT": 14400,
    "GROUP_INTERACTION":  10800,
    "SILENCE":               0,
}

# ── 行为优先级权重 ──
PHASE2_ACTION_PRIORITY = {
    "SEND_MESSAGE":        60,
    "SEND_IMAGE":          60,
    "WRITE_DIARY":         40,
    "UPDATE_MEMORY":       30,
    "RELATIONSHIP_EVENT":  80,
    "GROUP_INTERACTION":   50,
    "SILENCE":              0,
}

# =============================================================================
# Phase 2: 中央大脑仲裁配置
# =============================================================================

CENTRAL_BRAIN_RULES = {
    "sleepiness_override": {
        "threshold": 80,
        "override_action": "SILENCE",
        "reason": "sleepiness > 80 → silence"
    },
    "jealousy_override": {
        "threshold": 70,
        "override_action": "SEND_MESSAGE",
        "reason": "jealousy > 70 → emotional message only"
    },
    "lonely_attachment_boost": {
        "lonely_threshold": 60,
        "attachment_threshold": 55,
        "boost_factor": 1.3,
        "reason": "loneliness + attachment high → boost proactive"
    },
}

ARBITRATION_BLOCK_RULES = {
    "late_night_silence": {
        "condition": {"time_period": "late_night", "sleepiness_min": 60},
        "block": ["GROUP_INTERACTION", "RELATIONSHIP_EVENT"],
    },
    "angry_no_intimate": {
        "condition": {"emotion": "angry", "threshold": 70},
        "block": ["SEND_IMAGE"],
        "tone": "cold",
    },
}

SCENE_OVERRIDES = [
    {
        "scene_pattern": "*_rainy_*",
        "allow_image": True,
        "boost_image_probability": 0.25,
        "description": "雨夜/雨日凌晨 → 发图片概率 +25%"
    },
    {
        "scene_pattern": "late_night_*_lonely",
        "allow_image": True,
        "boost_image_probability": 0.20,
        "description": "深夜+孤独 → 发图片概率 +20%"
    },
    {
        "scene_pattern": "morning_sunny_happy",
        "max_probability_boost": 0.15,
        "description": "晴天早上+开心 → 主动概率 +15%"
    },
]

# 别名：scene_classifier 使用 PHASE2_SCENE_OVERRIDES
PHASE2_SCENE_OVERRIDES = SCENE_OVERRIDES

# =============================================================================
# Phase 2: 情绪压力系统配置
# =============================================================================

PRESSURE_ACCUMULATION_RATES = {
    "lonely":      0.05,
    "jealous":     0.02,
    "attachment":  0.03,
    "sad":         0.02,
    "anxious":     0.03,
}

PRESSURE_RELEASE_ON_INTERACTION = {
    "lonely":     -0.30,
    "jealous":    -0.10,
    "attachment": -0.05,
    "sad":        -0.15,
    "anxious":    -0.20,
}

PRESSURE_BURST_THRESHOLD = {
    "lonely":     80,
    "jealous":    70,
    "attachment": 85,
    "sad":        75,
    "anxious":    80,
}

# =============================================================================
# Phase 2: 缺席系统配置
# =============================================================================

ABSENCE_STAGES = {
    "early":      {"min_minutes": 0,    "max_minutes": 30,   "label": "刚离开",       "effect": "neutral"},
    "short":      {"min_minutes": 30,   "max_minutes": 120,  "label": "短期缺席",     "effect": "miss_you"},
    "medium":     {"min_minutes": 120,  "max_minutes": 360,  "label": "中期缺席",     "effect": "lonely + worried"},
    "long":       {"min_minutes": 360,  "max_minutes": 1440, "label": "长期缺席",     "effect": "sad + memory_recall"},
    "extreme":    {"min_minutes": 1440, "max_minutes": 999999,"label": "极端缺席",     "effect": "extreme_lonely + diary"},
}

ABSENCE_FACTOR_BONUS = {
    "early":   {"lonely": 0.05, "initiative": 0.02},
    "short":   {"lonely": 0.15, "initiative": 0.08, "attachment": 0.05},
    "medium":  {"lonely": 0.30, "initiative": 0.15, "attachment": 0.10, "sad": 0.10},
    "long":    {"lonely": 0.50, "initiative": 0.25, "attachment": 0.20, "sad": 0.20, "memory": 0.15},
    "extreme": {"lonely": 0.70, "initiative": 0.35, "attachment": 0.30, "sad": 0.35, "memory": 0.30},
}

# =============================================================================
# Phase 2: 反馈闭环配置
# =============================================================================

FEEDBACK_EMOTION_EFFECTS = {
    "SEND_MESSAGE": {
        "user_replied":     {"lonely": -10, "happy": 5,   "attachment": 3},
        "user_ignored":     {"lonely": 8,   "sad": 5,     "attachment": -2},
        "user_positive":    {"happy": 10,   "lonely": -15, "attachment": 5},
        "user_negative":    {"sad": 8,      "lonely": 5,  "attachment": -5},
    },
    "SEND_IMAGE": {
        "user_reacted":     {"happy": 5,    "lonely": -5,  "attachment": 3},
        "user_ignored":     {"lonely": 10,  "sad": 8,      "attachment": 2},
        "user_compliment":  {"happy": 12,   "lonely": -10, "attachment": 5},
    },
    "WRITE_DIARY": {
        "default":          {"calm": 5,     "lonely": -3},
    },
    "RELATIONSHIP_EVENT": {
        "user_engaged":     {"happy": 8,    "lonely": -8,  "attachment": 5},
        "user_ignored":     {"sad": 10,     "lonely": 5,   "attachment": -3},
    },
    "SILENCE": {
        "default":          {"lonely": 2,   "calm": 1},
    },
}

FEEDBACK_MEMORY_TRIGGERS = {
    "always_record":    ["RELATIONSHIP_EVENT", "WRITE_DIARY"],
    "on_user_reaction": ["SEND_MESSAGE", "SEND_IMAGE"],
    "threshold_based":  True,
}

# =============================================================================
# 生产环境配置
# =============================================================================

# ── 环境变量 ──
ENV = os.environ.get("ENV", "development")

# ── 数据库类型 ──
DB_TYPE = os.environ.get("DB_TYPE", "sqlite")  # sqlite / postgres
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_USER = os.environ.get("DB_USER", "ai")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "ai123")
DB_NAME = os.environ.get("DB_NAME", "companion")

# ── APScheduler 配置 ──
SCHEDULER_INTERVAL = int(os.environ.get("SCHEDULER_INTERVAL", str(TICK_INTERVAL_SECONDS)))
SCHEDULER_TIMEZONE = os.environ.get("SCHEDULER_TZ", "Asia/Shanghai")
SCHEDULER_MISFIRE_GRACE_TIME = int(os.environ.get("SCHEDULER_MISFIRE", "30"))

# ── FastAPI 配置 ──
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))
API_WORKERS = int(os.environ.get("API_WORKERS", "1"))
WEBSOCKET_PING_INTERVAL = int(os.environ.get("WS_PING_INTERVAL", "25"))
WEBSOCKET_PING_TIMEOUT = int(os.environ.get("WS_PING_TIMEOUT", "60"))

# ── 日志系统配置 ──
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG" if ENV == "development" else "INFO")
LOG_FORMAT = "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"
LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10 MB
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", "5"))

# ── Redis 配置 ──
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
