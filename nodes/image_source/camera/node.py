from core.logger import logger
from core.node_base.node import NodeBase, NodeState
from core.camera.opencv_camera import OpenCVCamera

_camera_instance = None


def _get_camera() -> OpenCVCamera:
    global _camera_instance
    if _camera_instance is None:
        _camera_instance = OpenCVCamera()
    return _camera_instance


class CameraSourceNode(NodeBase):
    def execute(self) -> bool:
        device_id = self.params.get("device_id", 0)
        camera = _get_camera()

        if not camera.is_connected():
            if not camera.connect(device_id):
                logger.error(f"[{self.meta.name}] Cannot connect camera {device_id}")
                self.set_state(NodeState.ERROR)
                return False

        frame = camera.grab_frame()
        if frame is None:
            logger.error(f"[{self.meta.name}] Failed to grab frame")
            self.set_state(NodeState.ERROR)
            return False

        self._set_output_images("images", [frame])
        logger.info(f"[{self.meta.name}] Captured 1 frame from camera {device_id}")
        self.set_state(NodeState.SUCCESS)
        return True
