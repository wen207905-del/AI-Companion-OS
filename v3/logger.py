"""
日志系统

按模块分文件，支持日志轮转、统一格式。
使用方式: from v3.logger import get_logger; logger = get_logger("模块名")
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict

from .config import LOG_DIR, LOG_LEVEL, LOG_FORMAT, LOG_MAX_BYTES, LOG_BACKUP_COUNT

# ── 日志模块映射：模块名 → 日志文件 ──
_MODULE_FILES = {
    "world": "world.log",
    "world_tick": "world.log",
    "world_engine": "world.log",
    "time_engine": "world.log",
    "weather_engine": "world.log",
    "mood_pressure": "world.log",
    "absence_system": "world.log",
    "autonomy": "autonomy.log",
    "autonomy_engine": "autonomy.log",
    "decision_factors": "autonomy.log",
    "action_policy": "autonomy.log",
    "action_dispatcher": "autonomy.log",
    "feedback_loop": "autonomy.log",
    "brain": "autonomy.log",
    "central_brain": "autonomy.log",
    "state_arbiter": "autonomy.log",
    "scene_classifier": "autonomy.log",
    "visual": "visual.log",
    "api": "api.log",
    "main": "api.log",
    "websocket": "api.log",
}

# 已创建的 logger 缓存
_loggers: Dict[str, logging.Logger] = {}
_handlers_initialized = False


def _ensure_log_dir():
    """确保日志目录存在。"""
    os.makedirs(LOG_DIR, exist_ok=True)


def _init_handlers():
    """为每类日志文件创建 RotatingFileHandler 并注册到 root logger。"""
    global _handlers_initialized
    if _handlers_initialized:
        return

    _ensure_log_dir()

    # 收集所有唯一的日志文件名
    log_files = set(_MODULE_FILES.values())

    # 为每个日志文件创建一个 handler
    for log_file in log_files:
        filepath = os.path.join(LOG_DIR, log_file)
        handler = RotatingFileHandler(
            filepath,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

        formatter = logging.Formatter(
            LOG_FORMAT,
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        # 注册到 root logger
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)  # root 接受所有级别，由 handler 过滤
        root.addHandler(handler)

    # 开发模式下也输出到控制台
    from .config import ENV
    if ENV == "development":
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(logging.Formatter(
            LOG_FORMAT,
            datefmt="%H:%M:%S",
        ))
        root = logging.getLogger()
        root.addHandler(console)

    _handlers_initialized = True


def get_logger(name: str) -> logging.Logger:
    """获取模块专用 logger。

    自动路由到对应的日志文件，支持 RotatingFileHandler 轮转。

    Args:
        name: 模块名称（如 "world", "autonomy", "api"）

    Returns:
        配置好的 logger 实例

    Example::

        from v3.logger import get_logger
        logger = get_logger("world")
        logger.info("World tick completed")
    """
    global _handlers_initialized
    if not _handlers_initialized:
        _init_handlers()

    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(f"v3.{name}")

    # 确定该模块对应的日志文件名
    log_file = _MODULE_FILES.get(name)
    if log_file:
        filepath = os.path.join(LOG_DIR, log_file)

        # 创建模块专属 handler（如果还没注册）
        handler_exists = any(
            hasattr(h, "baseFilename") and
            os.path.abspath(getattr(h, "baseFilename", "")) == os.path.abspath(filepath)
            for h in logger.handlers
        )

        if not handler_exists:
            handler = RotatingFileHandler(
                filepath,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
            handler.setFormatter(logging.Formatter(
                LOG_FORMAT,
                datefmt="%Y-%m-%d %H:%M:%S",
            ))
            logger.addHandler(handler)

    logger.setLevel(logging.DEBUG)
    logger.propagate = True

    _loggers[name] = logger
    return logger


# ── 便捷别名 ──
def setup_logging():
    """初始化全局日志系统。

    应在应用启动时调用一次，确保日志目录和 handler 就绪。
    """
    _ensure_log_dir()
    if not _handlers_initialized:
        _init_handlers()
    get_logger("api").info("日志系统初始化完成")
