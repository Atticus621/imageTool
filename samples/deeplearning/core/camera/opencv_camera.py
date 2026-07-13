import cv2
import numpy as np
from core.logger import logger
from .base import ICamera


class OpenCVCamera(ICamera):
    def __init__(self):
        self._cap = None
        self._device_id = -1

    def connect(self, device_id: int = 0) -> bool:
        if self._cap is not None and self._device_id == device_id:
            return True
        self.disconnect()
        try:
            self._cap = cv2.VideoCapture(device_id)
            if self._cap.isOpened():
                self._device_id = device_id
                logger.info(f"Camera connected: device {device_id}")
                return True
            else:
                self._cap = None
                logger.warning(f"Camera connect failed: device {device_id}")
                return False
        except Exception as e:
            logger.error(f"Camera connect error: {e}")
            self._cap = None
            return False

    def disconnect(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            self._device_id = -1
            logger.info("Camera disconnected")

    def is_connected(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def set_fps(self, fps: float) -> bool:
        """设置相机帧率。

        Args:
            fps: 目标帧率（如 30.0）

        Returns:
            是否设置成功
        """
        if not self.is_connected():
            return False
        try:
            self._cap.set(cv2.CAP_PROP_FPS, fps)
            actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
            logger.info(f"Camera FPS set: requested={fps}, actual={actual_fps}")
            return True
        except Exception as e:
            logger.error(f"Failed to set FPS: {e}")
            return False

    def get_fps(self) -> float:
        """获取当前帧率。"""
        if not self.is_connected():
            return 0.0
        return self._cap.get(cv2.CAP_PROP_FPS)

    def set_resolution(self, width: int, height: int) -> bool:
        """设置相机分辨率。"""
        if not self.is_connected():
            return False
        try:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"Camera resolution set: requested={width}x{height}, actual={actual_w}x{actual_h}")
            return True
        except Exception as e:
            logger.error(f"Failed to set resolution: {e}")
            return False

    def get_resolution(self) -> tuple[int, int]:
        """获取当前分辨率 (width, height)。"""
        if not self.is_connected():
            return (0, 0)
        return (
            int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    def grab_frame(self) -> "np.ndarray | None":
        """读取一帧。不预检 is_connected()——cap.read() 断开时自己
        返回 (False, None)，且 isOpened() 在 MSMF 后端耗时/副作用
        会拉大帧间隔导致 LED 闪烁。"""
        if self._cap is None:
            return None
        ret, frame = self._cap.read()
        if ret and frame is not None:
            return frame
        return None
