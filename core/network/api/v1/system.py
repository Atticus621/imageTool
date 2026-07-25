import os
import sys
import platform
from fastapi import APIRouter
from core.error.bus import error_bus
from core.node_base.registry import node_registry
from core.config import config

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/status")
def get_status():
    """系统状态概览 — 返回关键运行指标"""
    return {
        "success": True,
        "data": {
            "app": config.get("app.name", "ImageTools"),
            "version": config.get("app.version", "0.1.0"),
            "python": sys.version,
            "platform": platform.platform(),
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "nodes_registered": len(node_registry),
            "node_categories": list(node_registry.get_categories().keys()),
            "error_count": len(error_bus.get_recent(1000)),
            "env": {
                "QT_API": os.environ.get("QT_API", "not set"),
                "PATH": os.environ.get("PATH", "")[:200],
            },
        },
    }


@router.get("/errors")
def get_errors(count: int = 50):
    """错误历史 — 返回最近的错误记录"""
    errors = error_bus.get_recent(count)
    return {
        "success": True,
        "data": {
            "total": len(errors),
            "errors": errors,
            "summary": _summarize_errors(errors),
        },
    }


def _summarize_errors(errors: list[dict]) -> dict:
    """统计错误类型分布"""
    by_code = {}
    for e in errors:
        code = e.get("code", "unknown")
        by_code[code] = by_code.get(code, 0) + 1
    return {"by_code": by_code, "unique_codes": list(by_code.keys())}


@router.get("/nodes")
def list_nodes():
    """节点注册表 — 返回所有已注册节点的元数据"""
    nodes = []
    for meta in node_registry.get_all_meta():
        nodes.append({
            "id": meta.id,
            "name": meta.name,
            "description": getattr(meta, "description", ""),
            "category": node_registry.get_category(meta.id),
            "subcategory": node_registry.get_subcategory(meta.id),
        })
    return {
        "success": True,
        "data": {
            "total": len(nodes),
            "categories": node_registry.get_categories(),
            "nodes": nodes,
        },
    }


@router.get("/config")
def get_config():
    """配置信息 — 返回当前应用配置"""
    return {
        "success": True,
        "data": {
            "app_name": config.get("app.name", "ImageTools"),
            "ui": {
                "window_title": config.get("ui.window_title", "ImageTools"),
                "window_width": config.get("ui.window_width", 1600),
                "window_height": config.get("ui.window_height", 900),
            },
            "project": {
                "autosave_interval": config.get("project.autosave_interval", 60),
            },
            "all_keys": list(config._data.keys()) if hasattr(config, '_data') else [],
        },
    }
