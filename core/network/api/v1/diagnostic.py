"""Diagnostic API — 运行时状态查询和诊断。

提供组件状态快照、事件历史、日志查询等端点，
形成完整的远程错误排查能力。
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

from core.diagnostic.state_tracker import StateTracker
from core.diagnostic.event_tracer import EventTracer
from core.logger import logger

router = APIRouter(prefix="/api/v1/diagnostic", tags=["diagnostic"])


@router.get("/health")
def health_check():
    """健康检查 — 快速判断系统是否正常运行"""
    components = StateTracker.list_components()
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "timestamp": time.time(),
            "components_registered": len(components),
            "components": components,
        },
    }


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
    """列出所有已注册的组件名及其状态"""
    components = StateTracker.list_components()
    result = {}
    for name in components:
        state = StateTracker.get(name)
        result[name] = {
            "registered": True,
            "state": state,
        }
    return {"success": True, "data": result}


@router.get("/events")
def get_events(count: int = 100, event_type: str = None):
    """查询事件传播历史。

    Args:
        count: 返回的记录数（默认 100，最大 500）
        event_type: 可选，过滤事件类型（emit/receive/connect）

    Returns:
        事件记录列表
    """
    count = min(count, 500)
    history = EventTracer.get_history(count)

    if event_type:
        history = [e for e in history if e.get("type") == event_type]

    return {
        "success": True,
        "data": {
            "total": len(history),
            "events": history,
            "summary": _summarize_events(history),
        },
    }


def _summarize_events(events: list[dict]) -> dict:
    """统计事件类型分布"""
    by_type = {}
    by_emitter = {}
    for e in events:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        emitter = e.get("emitter", "unknown")
        by_emitter[emitter] = by_emitter.get(emitter, 0) + 1
    return {"by_type": by_type, "by_emitter": by_emitter}


@router.post("/events/clear")
def clear_events():
    """清空事件历史。"""
    EventTracer.clear()
    return {"success": True}


@router.get("/log")
def get_log(lines: int = 100, level: str = "DEBUG", search: str = None):
    """查询最近日志。

    Args:
        lines: 返回的日志行数（默认 100，最大 500）
        level: 最低日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        search: 可选，搜索关键词

    Returns:
        日志行列表
    """
    log_dir = Path("logs")
    if not log_dir.exists():
        return {"success": True, "data": [], "message": "No log directory found"}

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

        # Filter by search keyword
        if search:
            all_lines = [l for l in all_lines if search.lower() in l.lower()]

        lines = min(lines, 500)
        return {
            "success": True,
            "data": {
                "total_matching": len(all_lines),
                "lines": all_lines[-lines:],
                "log_file": str(log_file),
            },
        }
    except Exception as e:
        logger.error(f"Failed to read log file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
