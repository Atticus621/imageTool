# -*- coding: utf-8 -*-
"""画布控制器 —— 工具状态机 + 鼠标/键盘事件处理。"""

import math
from PySide6.QtCore import Qt, Signal, QObject, QPointF
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QGraphicsItem

from .canvas_items import RotationHandleItem


class CanvasController(QObject):
    """处理 ImageCanvas 上的所有交互事件。"""

    TOOL_HAND = "hand"
    TOOL_RULER = "ruler"
    TOOL_ROI = "roi"

    # ── 信号 ──
    tool_changed = Signal(str)

    panned = Signal(float, float)
    zoomed = Signal(float, float, float)
    mouse_moved = Signal(QPointF)

    ruler_started = Signal(QPointF)
    ruler_moved = Signal(QPointF)
    ruler_ended = Signal(QPointF)

    roi_started = Signal(QPointF)
    roi_moved = Signal(QPointF)
    roi_ended = Signal(QPointF)
    roi_rotate_requested = Signal(float)
    roi_rotate_absolute = Signal(int, float)        # roi_number, new_angle

    canvas_resized = Signal()

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self._view = view

        self._current_tool = self.TOOL_HAND

        # 拖动
        self._dragging = False
        self._drag_start_scene = QPointF()

        # 尺子
        self._ruler_dragging = False

        # ROI 绘制
        self._roi_dragging = False
        self._roi_shape = "rect"

        # ROI 旋转拖拽
        self._rotating = False
        self._rot_roi_number = None
        self._rot_start_angle = 0.0
        self._rot_start_mouse_angle = 0.0
        self._rot_center = QPointF()

        # 设置视图回调
        self._view.set_controller(self)

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------
    def set_tool(self, tool: str):
        self._current_tool = tool
        self.tool_changed.emit(tool)
        cursors = {
            self.TOOL_HAND: Qt.OpenHandCursor,
            self.TOOL_RULER: Qt.CrossCursor,
            self.TOOL_ROI: Qt.CrossCursor,
        }
        self._view.setCursor(QCursor(cursors.get(tool, Qt.ArrowCursor)))

    def set_roi_shape(self, shape: str):
        self._roi_shape = shape

    def current_tool(self):
        return self._current_tool

    # ------------------------------------------------------------------
    # 鼠标
    # ------------------------------------------------------------------
    def handle_press(self, scene_pos: QPointF, screen_pos):
        if self._view.pixmap_item.pixmap().isNull():
            return

        self._dragging = True
        self._drag_start_scene = scene_pos

        if self._current_tool == self.TOOL_RULER:
            self._ruler_dragging = True
            self.ruler_started.emit(scene_pos)

        elif self._current_tool == self.TOOL_ROI:
            # 检测旋转手柄
            items = self._view.scene_obj.items(scene_pos)
            for item in items:
                if isinstance(item, RotationHandleItem):
                    parent_roi = item.parentItem()
                    from .canvas_items import ROIRectItem
                    if isinstance(parent_roi, ROIRectItem):
                        self._rotating = True
                        self._rot_roi_number = parent_roi.roi_number
                        self._rot_start_angle = parent_roi.angle
                        self._rot_center = QPointF(
                            parent_roi.coords()[0] + parent_roi.coords()[2] / 2.0,
                            parent_roi.coords()[1] + parent_roi.coords()[3] / 2.0)
                        dx = scene_pos.x() - self._rot_center.x()
                        dy = scene_pos.y() - self._rot_center.y()
                        self._rot_start_mouse_angle = math.atan2(dy, dx)
                        return

            # 普通 ROI 绘制
            self._roi_dragging = True
            self.roi_started.emit(scene_pos)

    def handle_move(self, scene_pos: QPointF, screen_pos):
        if not self._dragging:
            return

        if self._rotating:
            cx, cy = self._rot_center.x(), self._rot_center.y()
            dx = scene_pos.x() - cx
            dy = scene_pos.y() - cy
            cur_angle = math.atan2(dy, dx)
            delta = math.atan2(math.sin(cur_angle - self._rot_start_mouse_angle),
                               math.cos(cur_angle - self._rot_start_mouse_angle))
            new_angle = self._rot_start_angle - math.degrees(delta)
            while new_angle > 180:
                new_angle -= 360
            while new_angle <= -180:
                new_angle += 360
            self.roi_rotate_absolute.emit(self._rot_roi_number, new_angle)
            return

        if self._current_tool == self.TOOL_HAND:
            old = self._drag_start_scene
            dx = scene_pos.x() - old.x()
            dy = scene_pos.y() - old.y()
            self.panned.emit(dx, dy)
            self._drag_start_scene = scene_pos

        elif self._current_tool == self.TOOL_RULER and self._ruler_dragging:
            self.ruler_moved.emit(scene_pos)

        elif self._current_tool == self.TOOL_ROI and self._roi_dragging:
            self.roi_moved.emit(scene_pos)

    def handle_release(self, scene_pos: QPointF, screen_pos):
        if not self._dragging:
            return

        if self._rotating:
            self._rotating = False
            self._rot_roi_number = None
            self._dragging = False
            return

        if self._current_tool == self.TOOL_RULER and self._ruler_dragging:
            self.ruler_ended.emit(scene_pos)
            self._ruler_dragging = False

        elif self._current_tool == self.TOOL_ROI and self._roi_dragging:
            self.roi_ended.emit(scene_pos)
            self._roi_dragging = False

        self._dragging = False

    def handle_mouse_move(self, scene_pos: QPointF):
        self.mouse_moved.emit(scene_pos)

    def handle_wheel(self, scene_pos: QPointF, angle_delta_y: int):
        factor = 1.15 if angle_delta_y > 0 else 1 / 1.15
        self.zoomed.emit(scene_pos.x(), scene_pos.y(), factor)

    def handle_resize(self):
        self.canvas_resized.emit()

    def handle_key(self, key: int):
        if key == Qt.Key_BracketLeft:
            self.roi_rotate_requested.emit(-5.0)
        elif key == Qt.Key_BracketRight:
            self.roi_rotate_requested.emit(5.0)
