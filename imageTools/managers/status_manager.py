# -*- coding: utf-8 -*-
"""状态栏管理器 —— 鼠标追踪 → 像素信息 + 尺子距离显示。"""
from PySide6.QtCore import QObject, QPointF


class StatusManager(QObject):
    """管理状态栏的像素信息和尺子距离显示。"""

    def __init__(self, window, image_manager, calibration_manager=None,
                 ruler_manager=None, parent=None):
        super().__init__(parent)
        self._window = window
        self._img = image_manager
        self._calib = calibration_manager
        self._ruler = ruler_manager

    def on_mouse_move(self, scene_pos: QPointF):
        """鼠标移动 → 读取像素 → 更新状态栏右侧。"""
        px, py = int(scene_pos.x()), int(scene_pos.y())
        w, h = self._img._canvas.img_width, self._img._canvas.img_height

        if 0 <= px < w and 0 <= py < h:
            color_text = self._img.get_pixel(px, py)
            world_text = ""
            if self._calib and self._calib.is_loaded:
                wxy = self._calib.img_to_phys((px, py))
                if wxy:
                    world_text = f"({wxy[0]:.3f}, {wxy[1]:.3f}) mm"
            self._window.update_status_info(f"({px}, {py})", color_text, world_text)

            if self._ruler and self._ruler.is_active:
                self._update_ruler_status()
            else:
                self._window.set_status("")
        else:
            self._window.update_status_info("--", "--", "")

    def _update_ruler_status(self):
        if self._ruler is None:
            return
        px = self._ruler.pixel_distance
        t = f"测量距离: {px:.1f} px"
        if self._ruler.world_distance > 0:
            t += f"  |  {self._ruler.world_distance:.3f} mm"
        self._window.set_status(t)

    def set_status(self, text: str):
        self._window.set_status(text)
