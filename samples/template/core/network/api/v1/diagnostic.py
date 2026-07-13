"""Diagnostic API — 运行时状态查询和诊断。

提供组件状态快照、事件历史、日志查询等端点，
形成完整的远程错误排查能力。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from core.diagnostic.state_tracker import StateTracker
from core.diagnostic.event_tracer import EventTracer
from core.logger import logger

router = APIRouter(prefix="/api/v1/diagnostic", tags=["diagnostic"])


@router.get("/state")
def get_state(component: str = None):
    """查询组件状态快照。

    Args:
        component: 可选，指定组件名。不指定则返回所有组件状态。

    Returns:
        组件状态字典
    """
    if component:
        state = StateTracker.get(component)
        if state is None:
            raise HTTPException(
                status_code=404,
                detail=f"Component '{component}' not registered. "
                       f"Available: {StateTracker.list_components()}",
            )
        return {"success": True, "data": {component: state}}
    return {"success": True, "data": StateTracker.snapshot()}


@router.get("/components")
def list_components():
    """列出所有已注册的组件名。"""
    return {"success": True, "data": StateTracker.list_components()}


@router.get("/events")
def get_events(count: int = 50):
    """查询事件传播历史。

    Args:
        count: 返回的记录数（默认 50，最大 200）

    Returns:
        事件记录列表
    """
    count = min(count, 200)
    return {"success": True, "data": EventTracer.get_history(count)}


@router.post("/events/clear")
def clear_events():
    """清空事件历史。"""
    EventTracer.clear()
    return {"success": True}


@router.get("/log")
def get_log(lines: int = 100, level: str = "DEBUG"):
    """查询最近日志。

    Args:
        lines: 返回的日志行数（默认 100）
        level: 最低日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）

    Returns:
        日志行列表
    """
    log_dir = Path("logs")
    if not log_dir.exists():
        return {"success": True, "data": [], "message": "No log directory found"}

    # Find the most recent log file
    log_files = sorted(log_dir.glob("*.log"), reverse=True)
    if not log_files:
        return {"success": True, "data": [], "message": "No log files found"}

    log_file = log_files[0]
    try:
        all_lines = log_file.read_text(encoding="utf-8").splitlines()

        # Filter by level
        level_upper = level.upper()
        level_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level_upper in level_order:
            min_idx = level_order.index(level_upper)
            filtered = []
            for line in all_lines:
                for i, lvl in enumerate(level_order):
                    if lvl in line and i >= min_idx:
                        filtered.append(line)
                        break
            all_lines = filtered

        return {"success": True, "data": all_lines[-lines:]}
    except Exception as e:
        logger.error(f"Failed to read log file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
