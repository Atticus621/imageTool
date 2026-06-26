import logging
import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

_initialized = False


class DailyFileHandler(logging.Handler):
    def __init__(self, log_dir: str, encoding: str = "utf-8"):
        super().__init__()
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._encoding = encoding
        self._current_date = None
        self._file = None

    def _get_log_path(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        return self._log_dir / f"{today}.log"

    def _open_file(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self._current_date != today:
            if self._file:
                self._file.close()
            self._current_date = today
            log_path = self._get_log_path()
            self._file = open(log_path, "a", encoding=self._encoding)

    def emit(self, record):
        try:
            self._open_file()
            if self._file and not self._file.closed:
                msg = self.format(record)
                self._file.write(msg + "\n")
                self._file.flush()
        except Exception:
            pass

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
        traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)


def setup_logger(name: str = "imageTools", log_dir: str = None) -> logging.Logger:
    global _initialized

    logger = logging.getLogger(name)

    if _initialized:
        return logger

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
        "[%(asctime)s] %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt_short)

    file_handler = DailyFileHandler(log_dir, encoding="utf-8")
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
