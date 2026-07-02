"""StructLogger — 结构化日志包装器。

为现有 logger 添加上下文感知能力，自动添加组件名、方法名、
状态等上下文信息，便于过滤和分析日志。

使用方式：
    log = StructLogger("RulerOverlay")
    log.state_change("drawing", False, True)
    log.coord_transform("viewport", "image", (100, 200), (50, 100))
"""

from __future__ import annotations

from core.logger import logger


class StructLogger:
    """结构化日志包装器。"""

    def __init__(self, component: str, logger_instance=None):
        self._component = component
        self._logger = logger_instance or logger

    def state_change(self, entity: str, old_state, new_state, **ctx) -> None:
        """记录状态变化（关键排查信息）"""
        ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else ""
        msg = f"[{self._component}] {entity}: {old_state} → {new_state}"
        if ctx_str:
            msg += f" ({ctx_str})"
        self._logger.info(msg)

    def event_received(self, event_name: str, **ctx) -> None:
        """记录事件接收"""
        ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else ""
        msg = f"[{self._component}] ← {event_name}"
        if ctx_str:
            msg += f" ({ctx_str})"
        self._logger.debug(msg)

    def event_emitted(self, event_name: str, **ctx) -> None:
        """记录事件发射"""
        ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else ""
        msg = f"[{self._component}] → {event_name}"
        if ctx_str:
            msg += f" ({ctx_str})"
        self._logger.debug(msg)

    def coord_transform(
        self, from_sys: str, to_sys: str, from_pos, to_pos
    ) -> None:
        """记录坐标转换（排查坐标问题的关键）"""
        self._logger.debug(
            f"[{self._component}] {from_sys}{from_pos} → {to_sys}{to_pos}"
        )

    def action(self, action_name: str, **ctx) -> None:
        """记录用户动作"""
        ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else ""
        msg = f"[{self._component}] {action_name}"
        if ctx_str:
            msg += f" ({ctx_str})"
        self._logger.debug(msg)

    def error(self, message: str, **ctx) -> None:
        """记录错误"""
        ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else ""
        msg = f"[{self._component}] ERROR: {message}"
        if ctx_str:
            msg += f" ({ctx_str})"
        self._logger.error(msg)
