from fastapi import APIRouter
from core.error.bus import error_bus
from core.node_base.registry import node_registry

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/status")
def get_status():
    return {
        "success": True,
        "data": {
            "app": "ImageTools",
            "version": "0.1.0",
            "nodes_registered": len(node_registry),
        },
    }


@router.get("/errors")
def get_errors(count: int = 10):
    return {
        "success": True,
        "data": error_bus.get_recent(count),
    }
