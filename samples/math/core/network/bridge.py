from __future__ import annotations
import uuid
import time
from PySide6.QtCore import QObject, Signal
from core.logger import logger


class NetworkBridge(QObject):
    command_received = Signal(str, dict)
    result_ready = Signal(str, dict)

    def __init__(self):
        super().__init__()
        self._pending: dict[str, dict] = {}

    def send_command(self, action: str, params: dict = None) -> str:
        request_id = str(uuid.uuid4())[:8]
        self._pending[request_id] = {"status": "pending"}
        logger.info(f"[Bridge] Command: {action} (id={request_id})")
        self.command_received.emit(action, {"request_id": request_id, **(params or {})})
        return request_id

    def resolve(self, request_id: str, result: dict):
        if request_id in self._pending:
            self._pending[request_id] = result
        self.result_ready.emit(request_id, result)

    def get_result(self, request_id: str) -> dict | None:
        entry = self._pending.get(request_id)
        if entry and entry.get("status") != "pending":
            return entry
        return None

    def wait_result(self, request_id: str, timeout_ms: int = 5000) -> dict:
        deadline = time.time() + timeout_ms / 1000
        while time.time() < deadline:
            result = self.get_result(request_id)
            if result:
                return result
            time.sleep(0.01)
        return {"success": False, "error": "Timeout"}


bridge = NetworkBridge()
