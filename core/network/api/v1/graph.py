from pydantic import BaseModel
from fastapi import APIRouter
from core.network.bridge import bridge

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


class ConnectRequest(BaseModel):
    from_node: str
    from_port: str
    to_node: str
    to_port: str


@router.post("/run")
def run_graph():
    request_id = bridge.send_command("run")
    result = bridge.wait_result(request_id)
    return result


@router.post("/stop")
def stop_graph():
    request_id = bridge.send_command("stop")
    result = bridge.wait_result(request_id)
    return result


@router.post("/connect")
def connect_nodes(req: ConnectRequest):
    request_id = bridge.send_command("connect", {
        "from_node": req.from_node,
        "from_port": req.from_port,
        "to_node": req.to_node,
        "to_port": req.to_port,
    })
    result = bridge.wait_result(request_id)
    return result


@router.post("/clear")
def clear_graph():
    request_id = bridge.send_command("clear")
    result = bridge.wait_result(request_id)
    return result


@router.post("/loop/on")
def loop_on():
    request_id = bridge.send_command("loop_on")
    result = bridge.wait_result(request_id)
    return result


@router.post("/loop/off")
def loop_off():
    request_id = bridge.send_command("loop_off")
    result = bridge.wait_result(request_id)
    return result
