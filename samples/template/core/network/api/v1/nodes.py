from pydantic import BaseModel
from fastapi import APIRouter
from core.network.bridge import bridge

router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])


class CreateNodeRequest(BaseModel):
    node_id: str
    pos: list[float] = [0, 0]
    name: str | None = None


class SetParamsRequest(BaseModel):
    params: dict


@router.get("")
def list_nodes():
    request_id = bridge.send_command("list_nodes")
    result = bridge.wait_result(request_id)
    return result


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
