from fastapi import APIRouter
from core.network.api.v1.system import router as system_router
from core.network.api.v1.nodes import router as nodes_router
from core.network.api.v1.graph import router as graph_router
from core.network.api.v1.simulation import router as simulation_router
from core.network.api.v1.diagnostic import router as diagnostic_router
from core.network.api.ws import router as ws_router

router = APIRouter()
router.include_router(system_router)
router.include_router(nodes_router)
router.include_router(graph_router)
router.include_router(simulation_router)
router.include_router(diagnostic_router)
router.include_router(ws_router)
