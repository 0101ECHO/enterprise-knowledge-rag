"""
结构化日志 - 基于 Loguru
支持文件轮转、JSON 格式、请求追踪
"""

import sys
from loguru import logger

from app.core.config import settings


def setup_logging():
    """初始化日志配置"""

    # 移除默认 handler
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    json_format = (
        '{{"time":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
        '"level":"{level}",'
        '"module":"{name}",'
        '"func":"{function}",'
        '"line":{line},'
        '"message":"{message}"}}'
    )

    # 控制台输出
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=settings.APP_DEBUG,
    )

    # 文件输出 - 按天轮转
    logger.add(
        f"{settings.LOG_DIR}/app_{{time:YYYY-MM-DD}}.log",
        format=json_format if settings.is_production else log_format,
        level=settings.LOG_LEVEL,
        rotation="00:00",          # 每天轮转
        retention="30 days",       # 保留30天
        compression="zip",         # 压缩旧日志
        encoding="utf-8",
        backtrace=True,
        diagnose=settings.APP_DEBUG,
    )

    # 错误日志单独文件
    logger.add(
        f"{settings.LOG_DIR}/error_{{time:YYYY-MM-DD}}.log",
        format=log_format,
        level="ERROR",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    return logger


# 全局 logger 实例
log = setup_logging()
