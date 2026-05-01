"""
日志系统 — 基于 Loguru，同时支持控制台彩色输出和文件滚动日志
"""
import sys
from pathlib import Path
from loguru import logger

from app.core.config import settings


def setup_logger() -> None:
    """初始化日志配置"""
    # 移除默认的 sink
    logger.remove()

    log_level = "DEBUG" if settings.DEBUG else "INFO"

    # 控制台输出（带颜色）
    logger.add(
        sys.stdout,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=settings.DEBUG,
    )

    # 文件日志（滚动，保留 30 天）
    log_dir = settings.log_path
    logger.add(
        log_dir / "nastool_{time:YYYY-MM-DD}.log",
        level=log_level,
        rotation="00:00",       # 每天零点轮转
        retention="30 days",    # 保留 30 天
        compression="gz",       # 压缩旧日志
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{line} — {message}"
        ),
        backtrace=True,
        diagnose=False,
    )

    # 错误专用日志
    logger.add(
        log_dir / "error.log",
        level="ERROR",
        rotation="10 MB",
        retention="90 days",
        compression="gz",
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
    )

    logger.info(f"日志系统初始化完成，级别: {log_level}，路径: {log_dir}")


# 导出 logger 供全项目使用
__all__ = ["logger", "setup_logger"]
