"""
日志工具模块

使用 loguru 提供结构化日志功能
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "1 day",
    retention: str = "7 days",
    format_type: str = "standard"
) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径
        rotation: 日志轮转周期
        retention: 日志保留时间
        format_type: 格式类型 (standard, json)
    """
    # 移除默认处理器
    logger.remove()

    # 定义日志格式
    if format_type == "json":
        log_format = (
            "{{"
            '"time":"{time:YYYY-MM-DD HH:mm:ss.SSS}",'
            '"level":"{level}",'
            '"module":"{module}",'
            '"function":"{function}",'
            '"line":{line},'
            '"message":"{message}"'
            "}}"
        )
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # 添加控制台处理器
    logger.add(
        sys.stderr,
        format=log_format,
        level=level,
        colorize=format_type != "json"
    )

    # 添加文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format=log_format,
            level=level,
            rotation=rotation,
            retention=retention,
            compression="gz"
        )


def get_logger(name: str = "manus"):
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logger: loguru日志记录器
    """
    return logger.bind(name=name)


# 便捷函数
def debug(message: str, **kwargs):
    """记录调试日志"""
    logger.debug(message, **kwargs)


def info(message: str, **kwargs):
    """记录信息日志"""
    logger.info(message, **kwargs)


def warning(message: str, **kwargs):
    """记录警告日志"""
    logger.warning(message, **kwargs)


def error(message: str, **kwargs):
    """记录错误日志"""
    logger.error(message, **kwargs)


def exception(message: str, **kwargs):
    """记录异常日志（包含堆栈跟踪）"""
    logger.exception(message, **kwargs)


# 初始化默认日志配置
setup_logging()

