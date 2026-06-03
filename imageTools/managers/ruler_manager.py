# -*- coding: utf-8 -*-
"""尺子管理器 —— 测量工具状态 + 绘制 + 距离计算。"""
import math
from PySide6.QtCore import QObject, Signal, QPointF
from ..canvas_items import RulerItem


class RulerManager(QObject):
    """管理尺子测量工具。"""

    updated = Signal()

    def __init__(self, canvas, calibration_manager=None, parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._calib = calibration_manager
        self._item = None
        self._p1 = None
        self._p2 = None

    # ── 属性 ──
    @property
    def is_active(self) -> bool:
        return self._p1 is not None and self._p2 is not None

    @property
    def pixel_distance(self) -> float:
        return self._calc()[0]

    @property
    def world_distance(self) -> float:
        return self._calc()[1]

    # ── 事件处理 ──
    def on_start(self, sp: QPointF):
        self._p1 = sp
        self._p2 = None
        self._clear()

    def on_move(self, sp: QPointF):
        if self._p1 is None:
            return
        self._p2 = sp
        self._redraw()

    def on_end(self, sp: QPointF):
        if self._p1 is None:
            return
        self._p2 = sp
        self._redraw()
        self.updated.emit()

    def clear(self):
        self._p1 = None
        self._p2 = None
        self._clear()

    # ── 内部 ──
    def _calc(self):
        if self._p1 is None or self._p2 is None:
            return 0.0, 0.0
        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        px = math.sqrt(dx * dx + dy * dy)
        wd = 0.0
        if self._calib and self._calib.is_loaded:
            w1 = self._calib.img_to_phys((self._p1.x(), self._p1.y()))
            w2 = self._calib.img_to_phys((self._p2.x(), self._p2.y()))
            if w1 and w2:
                wd = math.sqrt((w2[0] - w1[0]) ** 2 + (w2[1] - w1[1]) ** 2)
        return px, wd

    def _redraw(self):
        self._clear()
        if self._p1 is None or self._p2 is None:
            return
        px, wd = self._calc()
        self._item = RulerItem(self._p1, self._p2, px, wd)
        self._canvas.scene_obj.addItem(self._item)

    def _clear(self):
        if self._item:
            self._canvas.scene_obj.removeItem(self._item)
            self._item = None
