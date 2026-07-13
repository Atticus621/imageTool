"""EventTracer — 事件传播追踪器。

记录事件的发射和接收，形成完整的事件传播链，
便于排查事件丢失、异常传播或时序问题。

使用方式：
    # 在 EventEmitter.emit 中调用
    EventTracer.trace_emit("on_measurement_added", (result,))

    # 在事件处理器中调用
    EventTracer.trace_receive("on_measurement_added", "ImageViewerWidget._on_ruler_measurement")

    # 查询历史
    history = EventTracer.get_history(50)
"""

from __future__ import annotations

import time
from collections import deque

from core.logger import logger


class EventTracer:
    """事件传播追踪器。"""

    _history: deque = deque(maxlen=200)
    _enabled: bool = True

    @classmethod
    def enable(cls) -> None:
        """启用追踪。"""
        cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        """禁用追踪。"""
        cls._enabled = False

    @classmethod
    def trace_emit(cls, emitter_name: str, args: tuple = ()) -> None:
        """记录事件发射。

        Args:
            emitter_name: 发射器名称
            args: 发射参数
        """
        if not cls._enabled:
            return

        entry = {
            "time": time.time(),
            "type": "emit",
            "emitter": emitter_name,
            "args": str(args)[:200],
        }
        cls._history.append(entry)
        args_str = ", ".join(str(a)[:50] for a in args)
        logger.debug(f"[EventTrace] → {emitter_name}({args_str})")

    @classmethod
    def trace_receive(cls, emitter_name: str, handler_name: str) -> None:
        """记录事件接收。

        Args:
            emitter_name: 发射器名称
            handler_name: 处理器名称
        """
        if not cls._enabled:
            return

        entry = {
            "time": time.time(),
            "type": "receive",
            "emitter": emitter_name,
            "handler": handler_name,
        }
        cls._history.append(entry)
        logger.debug(f"[EventTrace] {emitter_name} → {handler_name}")

    @classmethod
    def trace_connect(cls, emitter_name: str, callback_name: str) -> None:
        """记录事件连接。

        Args:
            emitter_name: 发射器名称
            callback_name: 回调函数名称
        """
        if not cls._enabled:
            return

        logger.debug(f"[EventTrace] {emitter_name} ← {callback_name}")

    @classmethod
    def get_history(cls, count: int = 50) -> list[dict]:
        """获取事件历史。

        Args:
            count: 返回的记录数

        Returns:
            事件记录列表
        """
        return list(cls._history)[-count:]

    @classmethod
    def clear(cls) -> None:
        """清空事件历史。"""
        cls._history.clear()
