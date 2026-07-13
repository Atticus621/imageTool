from __future__ import annotations
import threading
from fastapi import FastAPI
from core.logger import logger
from core.network.api.router import router


class NetworkServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, app_name: str = "ImageTools"):
        self._host = host
        self._port = port
        self._app = FastAPI(title=f"{app_name} API", version="0.1.0")
        self._app.include_router(router)
        self._thread: threading.Thread | None = None

    @property
    def app(self) -> FastAPI:
        return self._app

    def start(self):
        if self._thread and self._thread.is_alive():
            logger.warning("Network server already running")
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Network server started on {self._host}:{self._port}")

    def _run(self):
        try:
            import uvicorn
        except ModuleNotFoundError:
            logger.error(
                "uvicorn is not installed; network server cannot start. "
                "Install uvicorn or disable the API service."
            )
            return

        uvicorn.run(
            self._app,
            host=self._host,
            port=self._port,
            log_level="warning",
        )

    def stop(self):
        logger.info("Network server stop requested (daemon thread will exit)")
