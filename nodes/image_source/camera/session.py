"""CameraSession — 相机生命周期管理器。

封装「连接 → 后台采集 → 帧缓冲 → 断开」的完整生命周期。
所有线程安全细节内聚在类内部，外部只需 start/stop/get_latest_frame。

用法:
    session = CameraSession()
    session.start(device_id=0)
    frame = session.get_latest_frame(timeout=1.0)
    session.stop()
"""

from __future__ import annotations

import threading

import numpy as np
from core.logger import logger
from core.camera.opencv_camera import OpenCVCamera


class CameraSession:
    """持续采集相机会话。

    线程模型:
      采集线程 — 拥有 _camera 对象，创建/连接/读帧/断开
      调用线程 — 通过 get_latest_frame() 取最新帧（线程安全）
    """

    def __init__(self):
        self._camera: OpenCVCamera | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._frame_ready = threading.Event()
        self._latest_frame: np.ndarray | None = None
        self._frame_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, device_id: int) -> bool:
        """连接相机并启动后台采集线程。幂等 — 已运行则直接返回 True。"""
        if self._thread is not None and self._thread.is_alive():
            return True

        self._stop_event.clear()
        self._frame_ready.clear()
        self._latest_frame = None
        self._frame_count = 0

        self._thread = threading.Thread(
            target=self._loop,
            args=(device_id,),
            daemon=True,
            name="camera-capture-loop",
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        """设停止信号、等待采集线程退出并释放相机。

        相机由采集线程在退出前自行断开，消除跨线程竞态。
        """
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                logger.warning("[CameraSession] Thread did not stop after 2s")
            self._thread = None

    def get_latest_frame(self, timeout: float = 1.0) -> np.ndarray | None:
        """获取采集线程最新写入的帧（线程安全）。

        首次调用会等待首帧到达，后续调用立即返回最新帧。
        """
        if not self._frame_ready.wait(timeout=timeout):
            return None
        with self._lock:
            return self._latest_frame

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def frame_count(self) -> int:
        return self._frame_count

    # ------------------------------------------------------------------
    # 后台采集循环
    # ------------------------------------------------------------------

    def _loop(self, device_id: int) -> None:
        """后台采集 — 三个阶段:
          1) 连接相机（一次）
          2) 持续读帧（永不因空帧退出）
          3) 收到停止信号 → 断开相机 → 退出
        """
        # ---- Phase 1: 连接 ----
        camera = OpenCVCamera()
        try:
            logger.info("[CameraSession] Connecting to device %d ...", device_id)
            if not camera.connect(device_id):
                logger.error("[CameraSession] Connect failed for device %d", device_id)
                return
            self._camera = camera
            w, h = camera.get_resolution()
            logger.info(
                "[CameraSession] Connected device %d, resolution=%dx%d",
                device_id, w, h,
            )
        except Exception:
            logger.exception("[CameraSession] Connect error for device %d", device_id)
            return

        # ---- Phase 2: 持续采集 ----
        empty_streak = 0
        WARN_EVERY = 100
        HEALTH_CHECK_EVERY = 500
        HEARTBEAT_EVERY = 100

        logger.info("[CameraSession] Entering capture loop")

        while not self._stop_event.is_set():
            frame = camera.grab_frame()

            if frame is not None:
                if empty_streak > 0:
                    logger.info(
                        "[CameraSession] Recovered after %d empty frames (total: %d)",
                        empty_streak, self._frame_count + 1,
                    )
                empty_streak = 0
                self._frame_count += 1
                with self._lock:
                    self._latest_frame = frame
                self._frame_ready.set()

                if self._frame_count % HEARTBEAT_EVERY == 0:
                    logger.debug(
                        "[CameraSession] Heartbeat: %d frames, LED on",
                        self._frame_count,
                    )
            else:
                empty_streak += 1
                if empty_streak % WARN_EVERY == 0:
                    logger.warning(
                        "[CameraSession] %d consecutive empty frames", empty_streak,
                    )
                self._stop_event.wait(timeout=0.002)

                if empty_streak % HEALTH_CHECK_EVERY == 0:
                    if not camera.is_connected():
                        logger.warning("[CameraSession] Disconnected, attempting reconnect")
                        try:
                            camera.disconnect()
                            if camera.connect(device_id):
                                self._camera = camera
                                logger.info("[CameraSession] Reconnected")
                                empty_streak = 0
                            else:
                                logger.warning("[CameraSession] Reconnect failed")
                        except Exception:
                            logger.exception("[CameraSession] Reconnect error")

        # ---- Phase 3: 清理 ----
        logger.info(
            "[CameraSession] Stopping (%d frames captured)", self._frame_count,
        )
        camera.disconnect()
        self._camera = None
        with self._lock:
            self._latest_frame = None
        self._frame_ready.clear()
        logger.info("[CameraSession] Exited cleanly")
