"""ROITracer — ROI 数据流全链路追踪器。

每个 ROI 从创建到使用都有日志记录。
出错时可通过 trace_id 查询完整调用链。
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.logger import logger


@dataclass
class TraceEntry:
    """单条追踪记录。"""

    trace_id: str
    timestamp: datetime
    operation: str  # BEGIN, STEP, WARN, ERROR, END
    detail: str = ""
    source: str = ""
    extra: dict = field(default_factory=dict)

    def __str__(self):
        parts = [f"[{self.trace_id}]"]
        if self.source:
            parts.append(f"src={self.source}")
        parts.append(self.operation)
        if self.detail:
            parts.append(self.detail)
        return " ".join(parts)


class ROITracer:
    """ROI 数据流追踪器（单例）。

    使用方式：
        tracer = ROITracer.instance()
        trace_id = tracer.begin("circle_detect", "circle")
        tracer.step(trace_id, "to_mask", "size=(1920,1080)")
        tracer.end(trace_id, "created")

        # 出错时查询
        entries = tracer.query(trace_id)
    """

    _instance: ROITracer | None = None

    def __init__(self):
        self._entries: dict[str, list[TraceEntry]] = defaultdict(list)
        self._active_sources: dict[str, str] = {}  # trace_id -> source

    @classmethod
    def instance(cls) -> ROITracer:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例（仅用于测试）。"""
        if cls._instance is not None:
            cls._instance._entries.clear()
            cls._instance._active_sources.clear()
        cls._instance = None

    def begin(self, source: str, roi_type: str) -> str:
        """开始追踪，返回 trace_id。"""
        trace_id = f"roi_{uuid.uuid4().hex[:8]}"
        entry = TraceEntry(
            trace_id=trace_id,
            timestamp=datetime.now(),
            operation="BEGIN",
            detail=f"type={roi_type}",
            source=source,
        )
        self._entries[trace_id].append(entry)
        self._active_sources[trace_id] = source
        logger.debug(f"[ROITracer] {entry}")
        return trace_id

    def step(self, trace_id: str, operation: str, detail: str = "") -> None:
        """记录中间步骤。"""
        entry = TraceEntry(
            trace_id=trace_id,
            timestamp=datetime.now(),
            operation=operation,
            detail=detail,
            source=self._active_sources.get(trace_id, ""),
        )
        self._entries[trace_id].append(entry)
        logger.debug(f"[ROITracer] {entry}")

    def warn(self, trace_id: str, message: str) -> None:
        """记录警告。"""
        entry = TraceEntry(
            trace_id=trace_id,
            timestamp=datetime.now(),
            operation="WARN",
            detail=message,
            source=self._active_sources.get(trace_id, ""),
        )
        self._entries[trace_id].append(entry)
        logger.warning(f"[ROITracer] {entry}")

    def error(self, trace_id: str, message: str, exc: Exception | None = None) -> None:
        """记录错误。"""
        detail = message
        if exc:
            detail += f" | {type(exc).__name__}: {exc}"
        entry = TraceEntry(
            trace_id=trace_id,
            timestamp=datetime.now(),
            operation="ERROR",
            detail=detail,
            source=self._active_sources.get(trace_id, ""),
        )
        self._entries[trace_id].append(entry)
        logger.error(f"[ROITracer] {entry}")

    def end(self, trace_id: str, status: str = "ok") -> None:
        """结束追踪。"""
        entry = TraceEntry(
            trace_id=trace_id,
            timestamp=datetime.now(),
            operation="END",
            detail=f"status={status}",
            source=self._active_sources.get(trace_id, ""),
        )
        self._entries[trace_id].append(entry)
        self._active_sources.pop(trace_id, None)
        logger.debug(f"[ROITracer] {entry}")

    def query(self, trace_id: str) -> list[TraceEntry]:
        """查询某个 trace_id 的完整生命周期。"""
        return list(self._entries.get(trace_id, []))

    def query_by_source(self, source: str) -> list[TraceEntry]:
        """查询来自指定来源的所有追踪记录。"""
        results = []
        for entries in self._entries.values():
            for entry in entries:
                if entry.source == source:
                    results.append(entry)
        return results

    def dump_active(self) -> str:
        """输出当前活跃（未结束）的追踪摘要。"""
        lines = []
        for trace_id, entries in self._entries.items():
            if not entries or entries[-1].operation != "END":
                last = entries[-1] if entries else None
                src = self._active_sources.get(trace_id, "?")
                lines.append(f"  {trace_id} (source={src}, last={last})")
        if not lines:
            return "No active ROI traces."
        return "Active ROI traces:\n" + "\n".join(lines)
