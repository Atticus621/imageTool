# -*- coding: utf-8 -*-
"""日志模块 —— 统一配置控制台 + 文件日志。

用法:
    from .logger import setup_logging, get_logger
    setup_logging()                         # 应用启动时调用一次
    logger = get_logger(__name__)           # 各模块获取 logger
    logger.info("图片已加载: %s", path)
"""
import logging
import os
import sys
from datetime import datetime

# 日志文件路径：项目根目录下
_LOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG_FILE = os.path.join(_LOG_DIR, "imageTool.log")

# ANSI 颜色映射 (仅控制台)
_COLORS = {
    "DEBUG":    "\033[36m",   # 青色
    "INFO":     "\033[32m",   # 绿色
    "WARNING":  "\033[33m",   # 黄色
    "ERROR":    "\033[31m",   # 红色
    "CRITICAL": "\033[35m",   # 紫色
}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    """控制台带颜色的 Formatter。"""

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)

    def format(self, record):
        color = _COLORS.get(record.levelname, "")
        record.color_start = color
        record.color_end = _RESET
        return super().format(record)


_root_configured = False


def setup_logging(level=logging.DEBUG, console=True, file=True):
    """初始化根 logger。应用启动时调用一次。

    Args:
        level:      全局最低日志级别 (默认 DEBUG)
        console:    是否输出到控制台
        file:       是否输出到文件
    """
    global _root_configured
    if _root_configured:
        return
    _root_configured = True

    root = logging.getLogger()
    root.setLevel(level)

    fmt_file = "[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s"
    fmt_console = "%(color_start)s[%(levelname)-7s]%(color_end)s [%(name)s] %(message)s"
    datefmt = "%H:%M:%S"

    if console:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(_ColorFormatter(fmt_console, datefmt))
        root.addHandler(ch)

    if file:
        try:
            fh = logging.FileHandler(_LOG_FILE, mode="w", encoding="utf-8")
            fh.setLevel(level)
            fh.setFormatter(logging.Formatter(fmt_file, datefmt))
            root.addHandler(fh)
        except OSError as e:
            # 文件打不开时只用控制台
            logging.warning("无法创建日志文件 %s: %s", _LOG_FILE, e)


def get_logger(name: str) -> logging.Logger:
    """获取子 logger。name 通常传 __name__。"""
    return logging.getLogger(name)
