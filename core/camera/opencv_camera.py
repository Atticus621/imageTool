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

    def grab_frame(self) -> "np.ndarray | None":
        if not self.is_connected():
            return None
        ret, frame = self._cap.read()
        if ret and frame is not None:
            return frame
        return None
