"""ROIOverlay — ROI 绘图叠加层。

叠加在 QGraphicsView 的 viewport 上，允许用户在图像上绘制 ROI 形状。
形状数据存储在图像坐标系中，绘制时通过 CoordinateMapper 转换为视口坐标，
自动跟随图像缩放/平移。

参考 RulerOverlay 的集成模式。
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtWidgets import QWidget

from core.logger import logger
from core.roi.editor.interactions import InteractionMode
from core.roi.editor.hit_test import HitTestEngine
from core.roi.editor.shapes.base import Shape
from core.roi.editor.shapes.rectangle import RectangleShape
from core.roi.editor.shapes.circle import CircleShape
from core.roi.editor.shapes.polygon import PolygonShape

if TYPE_CHECKING:
    from ui.widgets.coordinate_mapper import CoordinateMapper


class ROIOverlay(QWidget):
    """ROI 绘图叠加层。

    叠加在 QGraphicsView.viewport() 上，支持在图像上绘制矩形、圆形、多边形。
    形状存储在图像坐标系中，绘制时实时转换为视口坐标，自动跟随缩放/平移。

    信号：
        shape_created(Shape): 新增形状时发射
        shape_selected(Shape, str): 选择形状时发射，str = hit_type
        shape_changed(Shape): 形状移动/调整/旋转时发射
        shape_deleted(dict): 形状删除时发射，携带 state_dict
        log_message(str): 日志消息
    """

    shape_created = Signal(object)
    shape_selected = Signal(object, str)
    shape_changed = Signal(object)
    shape_deleted = Signal(dict)
    log_message = Signal(str)

    def __init__(self, parent: QWidget, mapper: CoordinateMapper):
        super().__init__(parent)
        self._mapper = mapper
        # 直接引用 QGraphicsView，绕过 CoordinateMapper 的整数截断
        self._gv = mapper._gv

        # 形状列表（存储在图像坐标系中）
        self._shapes: list[Shape] = []
        self._selected_shape: Shape | None = None
        self._current_tool = "select"
        self._mode = InteractionMode.IDLE

        # 命中测试引擎
        self._hit_engine = HitTestEngine()

        # 拖拽状态
        self._drag_start_img: QPointF | None = None
        self._drag_prev_img: QPointF | None = None
        self._drag_offset: QPointF | None = None
        self._resize_edge: str | None = None
        self._resize_corner: int = -1
        self._drawing_shape: Shape | None = None
        self._rotation_prev_dir: QPointF | None = None

        # ID 计数器
        self._last_shape_id = 0

        # 设置透明背景和鼠标追踪
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def shapes(self) -> list[Shape]:
        return list(self._shapes)

    @property
    def selected_shape(self) -> Shape | None:
        return self._selected_shape

    @property
    def command_api(self):
        from core.roi.editor.command_api import CommandAPI
        return CommandAPI(self)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_tool(self, tool: str):
        """设置当前工具 (select/rect/circle/polygon)。"""
        self._current_tool = tool
        self._log(f"Tool: {tool}")

    def add_shape(self, shape: Shape):
        """添加形状（图像坐标）。"""
        self._last_shape_id += 1
        shape._id = self._last_shape_id
        self._shapes.append(shape)
        self.shape_created.emit(shape)
        self._log(f"Created {shape.shape_type} #{shape._id}")
        self.update()

    def remove_shape(self, shape: Shape):
        """移除形状。"""
        if shape in self._shapes:
            if self._selected_shape is shape:
                self._selected_shape = None
            self._shapes.remove(shape)
            self.shape_deleted.emit(shape.get_state_dict())
            self._log(f"Deleted {shape.shape_type} #{getattr(shape, '_id', '?')}")
            self.update()

    def select_shape(self, shape: Shape, hit_type: str = "api"):
        """选择形状。"""
        if self._selected_shape:
            self._selected_shape.selected = False
        self._selected_shape = shape
        if shape:
            shape.selected = True
            self.shape_selected.emit(shape, hit_type)
            self._log(f"Selected {shape.shape_type} #{getattr(shape, '_id', '?')} ({hit_type})")
        self.update()

    def delete_selected(self) -> bool:
        """删除选中的形状。"""
        if self._selected_shape:
            state = self._selected_shape.get_state_dict()
            self.remove_shape(self._selected_shape)
            return True
        return False

    def clear_all(self):
        """清除所有形状。"""
        self._shapes.clear()
        self._selected_shape = None
        self._drawing_shape = None
        self._mode = InteractionMode.IDLE
        self._log("Cleared all shapes")
        self.update()

    # ------------------------------------------------------------------
    # 坐标转换辅助（直接用 QGraphicsView）
    # ------------------------------------------------------------------

    def _vp_to_img(self, vp_x: float, vp_y: float) -> QPointF:
        """视口坐标 → 图像/场景坐标。"""
        sp = self._gv.mapToScene(int(vp_x), int(vp_y))
        return QPointF(sp.x(), sp.y())

    def _img_to_vp(self, img_x: float, img_y: float) -> QPointF:
        """图像/场景坐标 → 视口坐标。"""
        vp = self._gv.mapFromScene(QPointF(img_x, img_y))
        return QPointF(vp)

    # ------------------------------------------------------------------
    # 鼠标事件
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        vp_pos = event.position()
        img_pos = self._vp_to_img(vp_pos.x(), vp_pos.y())

        if self._mode == InteractionMode.DRAWING_POLYGON:
            self._add_polygon_vertex(img_pos)
            return

        if self._mode == InteractionMode.IDLE:
            # 命中测试
            shape, hit_type = self._hit_engine.hit_test(img_pos, self._shapes)
            if shape:
                self.select_shape(shape, hit_type)
                self._start_interaction(img_pos, hit_type)
            else:
                # 点击空白区域，开始绘制新形状
                if self._current_tool != "select":
                    self._start_drawing(img_pos)
                else:
                    # 取消选择
                    if self._selected_shape:
                        self._selected_shape.selected = False
                        self._selected_shape = None
                        self.update()

    def mouseMoveEvent(self, event):
        vp_pos = event.position()
        img_pos = self._vp_to_img(vp_pos.x(), vp_pos.y())

        if self._mode == InteractionMode.DRAWING_RECT:
            if img_pos and self._drawing_shape:
                self._drawing_shape.update_from_drag(self._drag_start_img, img_pos)
                self.update()
            return

        if self._mode == InteractionMode.DRAWING_CIRCLE:
            if img_pos and self._drawing_shape:
                self._drawing_shape.update_from_drag(self._drag_start_img, img_pos)
                self.update()
            return

        if self._mode == InteractionMode.DRAWING_POLYGON:
            if img_pos and self._drawing_shape:
                self._drawing_shape.set_preview_point(img_pos)
                self.update()
            return

        if self._mode == InteractionMode.MOVING:
            if img_pos and self._selected_shape:
                dx = img_pos.x() - self._drag_prev_img.x()
                dy = img_pos.y() - self._drag_prev_img.y()
                self._selected_shape.move(dx, dy)
                self._drag_prev_img = img_pos
                self.shape_changed.emit(self._selected_shape)
                self.update()
            return

        if self._mode == InteractionMode.RESIZING_CORNER:
            if img_pos and self._selected_shape:
                self._selected_shape.resize_by_control(self._resize_corner, img_pos)
                self.shape_changed.emit(self._selected_shape)
                self.update()
            return

        if self._mode == InteractionMode.RESIZING_EDGE:
            if img_pos and self._selected_shape and self._drag_prev_img:
                dx = img_pos.x() - self._drag_prev_img.x()
                dy = img_pos.y() - self._drag_prev_img.y()
                if isinstance(self._selected_shape, RectangleShape):
                    self._selected_shape.resize_edge(self._resize_edge, dx, dy)
                self._drag_prev_img = img_pos
                self.shape_changed.emit(self._selected_shape)
                self.update()
            return

        if self._mode == InteractionMode.ROTATING:
            if img_pos and self._selected_shape:
                center = self._selected_shape.center()
                cur_dir = QPointF(img_pos.x() - center.x(), img_pos.y() - center.y())
                if self._rotation_prev_dir:
                    cross = (self._rotation_prev_dir.x() * cur_dir.y() -
                             self._rotation_prev_dir.y() * cur_dir.x())
                    dot = (self._rotation_prev_dir.x() * cur_dir.x() +
                           self._rotation_prev_dir.y() * cur_dir.y())
                    if abs(dot) > 0.001 or abs(cross) > 0.001:
                        angle = math.degrees(math.atan2(cross, dot))
                        self._selected_shape.rotate_by(angle)
                        self._rotation_prev_dir = cur_dir
                        self.shape_changed.emit(self._selected_shape)
                        self.update()
            return

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        if self._mode in (InteractionMode.DRAWING_RECT, InteractionMode.DRAWING_CIRCLE):
            self._finish_drawing()
            return

        if self._mode in (InteractionMode.MOVING, InteractionMode.RESIZING_EDGE,
                          InteractionMode.RESIZING_CORNER, InteractionMode.ROTATING):
            self._mode = InteractionMode.IDLE
            self._log(f"Finished {self._mode.name}")
            return

    def mouseDoubleClickEvent(self, event):
        if self._mode == InteractionMode.DRAWING_POLYGON:
            self._finish_polygon_drawing()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if self._mode == InteractionMode.DRAWING_POLYGON:
                self._finish_polygon_drawing()
        elif event.key() == Qt.Key.Key_Escape:
            if self._mode == InteractionMode.DRAWING_POLYGON:
                self._cancel_polygon_drawing()

    # ------------------------------------------------------------------
    # 绘制流程
    # ------------------------------------------------------------------

    def _start_drawing(self, img_pos: QPointF):
        if self._current_tool == "rect":
            self._mode = InteractionMode.DRAWING_RECT
            self._drawing_shape = RectangleShape(QRectF(img_pos, img_pos))
        elif self._current_tool == "circle":
            self._mode = InteractionMode.DRAWING_CIRCLE
            self._drawing_shape = CircleShape(img_pos, 0)
        elif self._current_tool == "polygon":
            self._mode = InteractionMode.DRAWING_POLYGON
            self._drawing_shape = PolygonShape()
            self._drawing_shape.add_vertex(img_pos)

        self._drag_start_img = img_pos
        self._log(f"Start drawing {self._current_tool}")

    def _finish_drawing(self):
        if self._drawing_shape:
            # 验证最小尺寸
            bbox = self._drawing_shape.bounding_rect()
            if bbox.width() > 5 or bbox.height() > 5:
                self.add_shape(self._drawing_shape)
            else:
                self._log("Shape too small, discarded")
        self._drawing_shape = None
        self._mode = InteractionMode.IDLE

    def _add_polygon_vertex(self, img_pos: QPointF):
        if self._drawing_shape:
            self._drawing_shape.add_vertex(img_pos)
            self._log(f"Polygon vertex #{self._drawing_shape.vertex_count}")
            self.update()

    def _finish_polygon_drawing(self):
        if self._drawing_shape and self._drawing_shape.vertex_count >= 3:
            self.add_shape(self._drawing_shape)
        else:
            self._log("Polygon needs >= 3 vertices, discarded")
        self._drawing_shape = None
        self._mode = InteractionMode.IDLE

    def _cancel_polygon_drawing(self):
        self._drawing_shape = None
        self._mode = InteractionMode.IDLE
        self._log("Polygon drawing cancelled")

    # ------------------------------------------------------------------
    # 交互流程
    # ------------------------------------------------------------------

    def _start_interaction(self, img_pos: QPointF, hit_type: str):
        if hit_type == "rotation_handle":
            self._mode = InteractionMode.ROTATING
            center = self._selected_shape.center()
            self._rotation_prev_dir = QPointF(img_pos.x() - center.x(), img_pos.y() - center.y())
            return

        if hit_type.startswith("control_point:"):
            idx = int(hit_type.split(":")[1])
            self._mode = InteractionMode.RESIZING_CORNER
            self._resize_corner = idx
            return

        if hit_type.startswith("edge:"):
            self._mode = InteractionMode.RESIZING_EDGE
            self._resize_edge = hit_type.split(":")[1]
            self._drag_prev_img = img_pos
            return

        if hit_type == "fill":
            self._mode = InteractionMode.MOVING
            self._drag_prev_img = img_pos
            return

    # ------------------------------------------------------------------
    # 绘制（图像坐标 → 视口坐标转换后绘制）
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for shape in self._shapes:
            self._paint_shape(painter, shape)

        if self._drawing_shape:
            self._paint_shape(painter, self._drawing_shape)

        painter.end()

    def _paint_shape(self, painter: QPainter, shape: Shape):
        """绘制单个形状（将图像坐标转为视口坐标后绘制）。

        核心思路：Shape 的 paint 方法直接用内部坐标绘制。
        我们通过 QPainter 的坐标变换将图像坐标系映射到视口坐标系。
        变换公式：vp = origin_vp + img * scale
        """
        # 计算缩放比例（图像坐标到视口坐标）
        origin_vp = self._img_to_vp(0, 0)
        ref_vp = self._img_to_vp(100, 0)
        dx_vp = ref_vp.x() - origin_vp.x()
        scale = dx_vp / 100.0 if abs(dx_vp) > 0.001 else 1.0

        # 保存 painter 状态
        painter.save()

        # translate + scale：先缩放图像坐标，再平移到视口原点
        painter.translate(origin_vp)
        painter.scale(scale, scale)

        # 用图像坐标绘制
        shape.paint(painter)

        # 恢复 painter 状态
        painter.restore()

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        logger.info(f"[ROI] {msg}")
        self.log_message.emit(msg)
