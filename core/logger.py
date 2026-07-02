import logging
import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

_initialized = False


class DailyFileHandler(logging.Handler):
    """按天滚动的文件日志处理器。

    线程安全（由 logging.Handler 内置的 RLock 保证）。
    写文件异常时输出到 stderr 兜底，避免静默丢日志。
    """

    def __init__(self, log_dir: str, encoding: str = "utf-8"):
        super().__init__()
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._encoding = encoding
        self._current_date = None
        self._file = None
        self._error_count = 0  # 追踪连续写入失败次数

    def _get_log_path(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        return self._log_dir / f"{today}.log"

    def _open_file(self):
        """确保文件已打开且有效。

        日期变更时自动切换新文件。如果文件句柄意外丢失（如外部关闭），
        也会重新打开。
        """
        today = datetime.now().strftime("%Y-%m-%d")

        need_reopen = (
            self._current_date != today
            or self._file is None
            or self._file.closed
        )

        if not need_reopen:
            return

        if self._file and not self._file.closed:
            self._file.close()

        self._current_date = today
        log_path = self._get_log_path()
        try:
            self._file = open(log_path, "a", encoding=self._encoding)
        except OSError as e:
            print(
                f"[DailyFileHandler] 无法打开日志文件 {log_path}: {e}",
                file=sys.stderr,
            )
            self._file = None

    def emit(self, record):
        """写入一条日志。异常时输出到 stderr 兜底。"""
        try:
            self._open_file()
            if self._file is None or self._file.closed:
                # 文件打不开，兜底到 stderr
                msg = self.format(record)
                print(msg, file=sys.stderr)
                return

            msg = self.format(record)
            self._file.write(msg + "\n")
            self._file.flush()
            self._error_count = 0

        except Exception:
            self._error_count += 1
            # 前几次错误输出到 stderr 便于排查，之后避免刷屏
            if self._error_count <= 3:
                print(
                    f"[DailyFileHandler] emit 失败 (连续 {self._error_count} 次)，"
                    f"记录: {getattr(record, 'message', '?')}",
                    file=sys.stderr,
                )
                traceback.print_exc(file=sys.stderr)

    def close(self):
        if self._file:
            self._file.close()
            self._file = None
        super().close()


def _global_exception_hook(exc_type, exc_value, exc_tb):
    if exc_type is KeyboardInterrupt:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    try:
        lgr = logging.getLogger("imageTools")
        lgr.critical(
            "未捕获异常",
            exc_info=(exc_type, exc_value, exc_tb),
        )
    except Exception:
        traceback.print_exception(exc_type, exc_value, exc_tb)


def _thread_exception_hook(args):
    try:
        lgr = logging.getLogger("imageTools")
        lgr.critical(
            f"线程异常: {args.thread.name}",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
    except Exception:
        traceback.print_exception(
            args.exc_type, args.exc_value, args.exc_traceback
        )


def setup_logger(name: str = "imageTools", log_dir: str = None) -> logging.Logger:
    """初始化全局日志系统。

    - 控制台：INFO 级别，短格式
    - 文件：  DEBUG 级别，完整格式（按天滚动）
    - 异常兜底：emit 失败时写 stderr
    """
    global _initialized

    logger = logging.getLogger(name)

    if _initialized:
        return logger

    # 与 root logger 隔离，防止 uvicorn 等库重配置 root 时影响我们
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    if log_dir is None:
        log_dir = Path(__file__).parent.parent / "logs"
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s.%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fmt_short = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(threadName)-12s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt_short)

    file_handler = DailyFileHandler(str(log_dir), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    sys.excepthook = _global_exception_hook
    threading.excepthook = _thread_exception_hook

    _initialized = True
    logger.info("Logger initialized")
    return logger


logger = setup_logger()
