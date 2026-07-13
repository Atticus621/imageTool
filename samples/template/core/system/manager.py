from __future__ import annotations
from typing import Callable
from core.logger import logger


class SystemManager:
    def __init__(self):
        self._tasks: list[tuple[str, Callable]] = []

    def add_task(self, name: str, func: Callable):
        self._tasks.append((name, func))

    def run(self, splash=None):
        total = len(self._tasks)
        for i, (name, func) in enumerate(self._tasks):
            if splash:
                splash.set_progress(name, i, total)
            logger.info(f"[Init] {name}...")
            try:
                func()
            except Exception as e:
                logger.error(f"[Init] {name} failed: {e}")
                raise
        if splash:
            splash.set_progress("完成", total, total)
        logger.info(f"[Init] All {total} tasks completed")
