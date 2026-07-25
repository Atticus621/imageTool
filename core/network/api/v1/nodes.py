from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query
from core.network.bridge import bridge
from core.node_base.registry import node_registry
from core.diagnostic.node_tracker import NodeExecutionTracker

router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])


class CreateNodeRequest(BaseModel):
    node_id: str
    pos: list[float] = [0, 0]
    name: str | None = None


class SetParamsRequest(BaseModel):
    params: dict


@router.get("")
def list_nodes():
    """列出所有已注册节点"""
    nodes = []
    for meta in node_registry.get_all_meta():
        nodes.append({
            "id": meta.id,
            "name": meta.name,
            "description": getattr(meta, "description", ""),
        })
    return {
        "success": True,
        "data": {
            "total": len(nodes),
            "nodes": nodes,
        },
    }


# --- 执行状态端点 ---

@router.get("/execution/summary")
def get_execution_summary():
    """获取所有节点的执行摘要"""
    return {
        "success": True,
        "data": NodeExecutionTracker.get_summary(),
    }


@router.get("/execution/all-status")
def get_all_node_statuses():
    """获取所有节点的当前状态"""
    return {
        "success": True,
        "data": NodeExecutionTracker.get_all_statuses(),
    }


@router.get("/execution/status")
def get_node_status(name: str = Query(..., description="节点 ID，如 detection/yolo/yolo_detect")):
    """获取指定节点的执行状态（使用查询参数避免路径斜杠问题）"""
    status = NodeExecutionTracker.get_status(name)
    if status is None:
        # 检查节点是否存在
        meta = node_registry.get_meta(name)
        if meta is None:
            raise HTTPException(
                status_code=404,
                detail=f"Node '{name}' not found in registry",
            )
        # 节点存在但还没有执行记录
        return {
            "success": True,
            "data": {
                "name": name,
                "state": "idle",
                "total_executions": 0,
                "success_count": 0,
                "error_count": 0,
                "success_rate": 0,
                "last_execution": None,
                "last_error": "",
            },
        }
    return {"success": True, "data": status}


@router.get("/execution/history")
def get_node_history(
    name: str = Query(..., description="节点 ID，如 detection/yolo/yolo_detect"),
    count: int = Query(20, description="返回记录数"),
):
    """获取指定节点的执行历史记录（使用查询参数避免路径斜杠问题）"""
    # 检查节点是否存在
    meta = node_registry.get_meta(name)
    if meta is None:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{name}' not found in registry",
        )

    history = NodeExecutionTracker.get_history(name, count)
    return {
        "success": True,
        "data": {
            "node_name": name,
            "total_records": len(history),
            "records": history,
        },
    }


@router.post("")
def create_node(req: CreateNodeRequest):
    request_id = bridge.send_command("create_node", {
        "node_id": req.node_id,
        "pos": req.pos,
        "name": req.name,
    })
    result = bridge.wait_result(request_id)
    return result


@router.delete("/{node_name}")
def delete_node(node_name: str):
    request_id = bridge.send_command("delete_node", {"node_name": node_name})
    result = bridge.wait_result(request_id)
    return result


@router.post("/{node_name}/params")
def set_params(node_name: str, req: SetParamsRequest):
    request_id = bridge.send_command("set_params", {
        "node_name": node_name,
        "params": req.params,
    })
    result = bridge.wait_result(request_id)
    return result
