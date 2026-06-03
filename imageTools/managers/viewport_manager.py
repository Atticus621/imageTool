# -*- coding: utf-8 -*-
"""视口管理器 —— 平移、缩放、适应窗口。"""
from PySide6.QtCore import Qt, QObject


class ViewportManager(QObject):
    """管理画布视口变换。"""

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self._canvas = canvas

    def fit_to_window(self):
        if self._canvas.pixmap_item.pixmap().isNull():
            return
        self._canvas.fitInView(self._canvas.scene_obj.sceneRect(),
                                Qt.KeepAspectRatio)

    def pan(self, dx: float, dy: float):
        hb = self._canvas.horizontalScrollBar()
        vb = self._canvas.verticalScrollBar()
        if hb:
            hb.setValue(hb.value() - int(dx))
        if vb:
            vb.setValue(vb.value() - int(dy))

    def zoom(self, cx: float, cy: float, factor: float):
        self._canvas.scale(factor, factor)
