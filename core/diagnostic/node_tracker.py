"""NodeExecutionTracker — 节点执行状态和历史记录追踪器。

记录每个节点的：
- 当前状态 (idle/running/success/error)
- 最近执行次数和成功率
- 最近执行记录（时间、耗时、成功/失败、错误信息）

使用方式：
    NodeExecutionTracker.on_node_started("node_name")
    NodeExecutionTracker.on_node_finished("node_name", success=True, duration=0.5)
    NodeExecutionTracker.on_node_error("node_name", "Error message")

    status = NodeExecutionTracker.get_status("node_name")
    history = NodeExecutionTracker.get_history("node_name", count=10)
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from core.logger import logger


@dataclass
class NodeExecutionRecord:
    """单次执行记录"""
    timestamp: float
    duration: float
    success: bool
    error_message: str = ""
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "duration_ms": round(self.duration * 1000, 2),
            "success": self.success,
            "error_message": self.error_message,
            "params": self.params,
        }


@dataclass
class NodeStatus:
    """节点当前状态"""
    name: str
    state: str  # idle/running/success/error
    total_executions: int = 0
    success_count: int = 0
    error_count: int = 0
    last_execution: NodeExecutionRecord | None = None
    last_error: str = ""

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.success_count / self.total_executions

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "total_executions": self.total_executions,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": round(self.success_rate * 100, 1),
            "last_execution": self.last_execution.to_dict() if self.last_execution else None,
            "last_error": self.last_error,
        }


class NodeExecutionTracker:
    """节点执行追踪器（单例）"""

    _statuses: dict[str, NodeStatus] = {}
    _histories: dict[str, deque[NodeExecutionRecord]] = {}
    _max_history: int = 50  # 每个节点最多保留 50 条记录

    @classmethod
    def on_node_started(cls, name: str, params: dict = None) -> None:
        """节点开始执行"""
        status = cls._get_or_create(name)
        status.state = "running"
        logger.debug(f"[NodeTracker] {name} started")

    @classmethod
    def on_node_finished(cls, name: str, success: bool, duration: float = 0.0, error_message: str = "") -> None:
        """节点执行完成"""
        status = cls._get_or_create(name)
        record = NodeExecutionRecord(
            timestamp=time.time(),
            duration=duration,
            success=success,
            error_message=error_message,
        )

        # 更新状态
        status.total_executions += 1
        if success:
            status.success_count += 1
            status.state = "success"
        else:
            status.error_count += 1
            status.state = "error"
            status.last_error = error_message

        status.last_execution = record

        # 添加到历史
        history = cls._get_history(name)
        history.append(record)

        logger.debug(f"[NodeTracker] {name} finished: {'success' if success else 'error'} ({duration*1000:.1f}ms)")

    @classmethod
    def on_node_error(cls, name: str, error_message: str) -> None:
        """节点执行出错"""
        cls.on_node_finished(name, success=False, error_message=error_message)

    @classmethod
    def reset(cls, name: str = None) -> None:
        """重置节点状态"""
        if name:
            if name in cls._statuses:
                cls._statuses[name].state = "idle"
        else:
            for status in cls._statuses.values():
                status.state = "idle"

    @classmethod
    def get_status(cls, name: str) -> dict | None:
        """获取节点当前状态"""
        status = cls._statuses.get(name)
        if status is None:
            return None
        return status.to_dict()

    @classmethod
    def get_all_statuses(cls) -> dict[str, dict]:
        """获取所有节点状态"""
        return {name: status.to_dict() for name, status in cls._statuses.items()}

    @classmethod
    def get_history(cls, name: str, count: int = 20) -> list[dict]:
        """获取节点执行历史"""
        history = cls._histories.get(name)
        if history is None:
            return []
        records = list(history)[-count:]
        return [r.to_dict() for r in records]

    @classmethod
    def get_summary(cls) -> dict:
        """获取所有节点执行摘要"""
        total_executions = sum(s.total_executions for s in cls._statuses.values())
        total_success = sum(s.success_count for s in cls._statuses.values())
        total_errors = sum(s.error_count for s in cls._statuses.values())

        return {
            "total_nodes": len(cls._statuses),
            "total_executions": total_executions,
            "total_success": total_success,
            "total_errors": total_errors,
            "overall_success_rate": round(total_success / total_executions * 100, 1) if total_executions > 0 else 0,
        }

    @classmethod
    def _get_or_create(cls, name: str) -> NodeStatus:
        if name not in cls._statuses:
            cls._statuses[name] = NodeStatus(name=name, state="idle")
        return cls._statuses[name]

    @classmethod
    def _get_history(cls, name: str) -> deque[NodeExecutionRecord]:
        if name not in cls._histories:
            cls._histories[name] = deque(maxlen=cls._max_history)
        return cls._histories[name]
