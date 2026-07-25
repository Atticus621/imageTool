"""ROITcpServer — 轻量 TCP 服务器，用于 ROI 编辑器远程调试。

每个命令新建连接，发送 JSON，接收 JSON，关闭连接。
端口 9527。
"""

from __future__ import annotations

import json
import socket
import threading
from typing import TYPE_CHECKING

from core.logger import logger

if TYPE_CHECKING:
    from core.roi.editor.overlay import ROIOverlay


class ROITcpServer:
    """TCP 服务器，用于远程调试 ROI 编辑器。"""

    def __init__(self, overlay: ROIOverlay, host: str = "127.0.0.1", port: int = 9527):
        self._overlay = overlay
        self._host = host
        self._port = port
        self._server_socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self):
        """启动 TCP 服务器（后台线程）。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"[ROI TCP] Server started on {self._host}:{self._port}")

    def stop(self):
        """停止 TCP 服务器。"""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        logger.info("[ROI TCP] Server stopped")

    def _run(self):
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.settimeout(1.0)
            self._server_socket.bind((self._host, self._port))
            self._server_socket.listen(5)

            while self._running:
                try:
                    client, addr = self._server_socket.accept()
                    threading.Thread(
                        target=self._handle_client,
                        args=(client,),
                        daemon=True
                    ).start()
                except socket.timeout:
                    continue
                except OSError:
                    break
        except Exception as e:
            logger.error(f"[ROI TCP] Server error: {e}")
        finally:
            if self._server_socket:
                try:
                    self._server_socket.close()
                except Exception:
                    pass

    def _handle_client(self, client: socket.socket):
        try:
            client.settimeout(5.0)
            data = client.recv(65536)
            if not data:
                return

            command = json.loads(data.decode("utf-8"))
            logger.debug(f"[ROI TCP] Received: {command}")

            api = self._overlay.command_api
            result = api.execute(command)

            response = json.dumps(result, ensure_ascii=False).encode("utf-8")
            client.sendall(response)
        except json.JSONDecodeError as e:
            error_resp = json.dumps({"status": "error", "error": f"Invalid JSON: {e}"}).encode("utf-8")
            client.sendall(error_resp)
        except Exception as e:
            logger.error(f"[ROI TCP] Client error: {e}")
        finally:
            client.close()
