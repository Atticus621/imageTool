from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.logger import logger

router = APIRouter(tags=["websocket"])

ws_clients: list[WebSocket] = []


@router.websocket("/ws/events")
async def websocket_events(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    logger.info(f"[WS] Client connected ({len(ws_clients)} total)")
    try:
        while True:
            data = await ws.receive_json()
            logger.info(f"[WS] Received: {data}")
            await ws.send_json({"echo": data})
    except WebSocketDisconnect:
        ws_clients.remove(ws)
        logger.info(f"[WS] Client disconnected ({len(ws_clients)} total)")


async def broadcast(event_type: str, data: dict):
    msg = {"type": event_type, "data": data}
    for ws in ws_clients[:]:
        try:
            await ws.send_json(msg)
        except Exception:
            ws_clients.remove(ws)
