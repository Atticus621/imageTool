"""Core diagnostic — 诊断工具集。

提供结构化日志、组件状态快照、事件传播追踪等能力，
形成完整的错误排查链路。
"""

from core.diagnostic.struct_logger import StructLogger
from core.diagnostic.state_tracker import StateTracker
from core.diagnostic.event_tracer import EventTracer

__all__ = ["StructLogger", "StateTracker", "EventTracer"]
