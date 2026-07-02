"""相机源节点 — 从相机设备采集图像。

- 循环模式：后台持续采集（CameraSession），节点每次取最新帧
- 单次模式：打开 → 拍一张 → 关闭

循环模式的启停通过 SystemEventBus.loop_mode_changed 事件驱动，
不再由 MainWindow 直接调用模块函数。
"""

from __future__ import annotations

from core.logger import logger
from core.node_base.node import NodeBase, NodeState
from core.camera.opencv_camera import OpenCVCamera
from nodes.image_source.camera.session import CameraSession

# ------------------------------------------------------------------
# 模块级状态：只有 CameraSession 单例 + 事件订阅
# ------------------------------------------------------------------

_session: CameraSession | None = None


def _on_loop_mode_changed(enabled: bool) -> None:
    """订阅 SystemEventBus.loop_mode_changed。

    UI 切换循环模式时触发：创建或销毁 CameraSession。
    session 的实际启动（连接相机）延迟到第一次 execute()，
    因为此时才能拿到 device_id 参数。
    """
    global _session
    logger.info("[Camera] loop_mode_changed event: %s", enabled)

    if enabled:
        if _session is None:
            _session = CameraSession()
        # 不在此处 start() — device_id 还不确定，等 execute 第一次调用
    else:
        if _session is not None:
            _session.stop()
            _session = None


# 模块加载时订阅事件总线
from core.events import system_events  # noqa: E402
system_events.loop_mode_changed.connect(_on_loop_mode_changed)


# ------------------------------------------------------------------
# 节点
# ------------------------------------------------------------------

class CameraSourceNode(NodeBase):
    def execute(self) -> bool:
        global _session
        device_id = self.params.get("device_id", 0)

        # 循环模式：_session 由 loop_mode_changed 事件创建，
        # 第一次 execute 时补调 start(device_id)
        if _session is not None:
            if not _session.is_running:
                _session.start(device_id)

            frame = _session.get_latest_frame(timeout=2.0)
            if frame is None:
                logger.error(
                    "[%s] No frame from CameraSession (timeout 2s)",
                    self.meta.name,
                )
                self.set_state(NodeState.ERROR)
                return False

            self._set_output_images("images", [frame])
            logger.debug(
                "[%s] Pulled frame %dx%d from session",
                self.meta.name, frame.shape[1], frame.shape[0],
            )
            self.set_state(NodeState.SUCCESS)
            return True

        # 单次模式：打开 → 拍一张 → 关闭
        camera = OpenCVCamera()
        if not camera.connect(device_id):
            logger.error("[%s] Cannot connect camera %d", self.meta.name, device_id)
            self.set_state(NodeState.ERROR)
            return False

        frame = camera.grab_frame()
        if frame is None:
            logger.error("[%s] Failed to grab frame", self.meta.name)
            self.set_state(NodeState.ERROR)
            camera.disconnect()
            return False

        self._set_output_images("images", [frame])
        logger.info("[%s] Captured 1 frame from camera %d", self.meta.name, device_id)
        self.set_state(NodeState.SUCCESS)
        camera.disconnect()
        return True
