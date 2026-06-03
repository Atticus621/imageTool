# -*- coding: utf-8 -*-
"""画布覆盖层 items —— RulerItem, ROIRectItem, ROICircleItem 等。"""

import math
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter, QPainterPath, QPolygonF,
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsItemGroup,
    QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsTextItem,
    QGraphicsObject,
)


# ── 辅助 (延迟创建，避免 QApplication 前初始化) ──
def _bold_font():
    return QFont("Consolas", 10, QFont.Bold)

def _small_font():
    return QFont("Consolas", 9)


def _make_pen(color_str: str, width: float = 2.0,
              dash: tuple = None, style=Qt.SolidLine) -> QPen:
    pen = QPen(QColor(color_str), width, style)
    if dash:
        pen.setDashPattern(dash)
    return pen


# ══════════════════════════════════════════════════════════════════════
# RulerItem
# ══════════════════════════════════════════════════════════════════════
class RulerItem(QGraphicsItemGroup):
    """尺子测量覆盖层。"""

    def __init__(self, p1: QPointF, p2: QPointF,
                 pixel_dist: float, world_dist: float = 0.0, parent=None):
        super().__init__(parent)

        color = QColor("#e74c3c")
        pen = QPen(color, 2)

        line = QGraphicsLineItem(p1.x(), p1.y(), p2.x(), p2.y())
        line.setPen(pen)
        self.addToGroup(line)

        r = 5
        for pt in (p1, p2):
            circle = QGraphicsEllipseItem(pt.x() - r, pt.y() - r, r * 2, r * 2)
            circle.setPen(QPen(Qt.white, 2))
            circle.setBrush(QBrush(color))
            self.addToGroup(circle)

        mid_x = (p1.x() + p2.x()) / 2.0
        mid_y = (p1.y() + p2.y()) / 2.0
        text_px = QGraphicsTextItem(f"{pixel_dist:.1f} px")
        text_px.setDefaultTextColor(color)
        text_px.setFont(_bold_font())
        tw = text_px.boundingRect().width()
        text_px.setPos(mid_x - tw / 2.0, mid_y - 32)
        self.addToGroup(text_px)

        if world_dist > 0:
            text_mm = QGraphicsTextItem(f"{world_dist:.3f} mm")
            text_mm.setDefaultTextColor(QColor("#3498db"))
            text_mm.setFont(_small_font())
            tw2 = text_mm.boundingRect().width()
            text_mm.setPos(mid_x - tw2 / 2.0, mid_y - 50)
            self.addToGroup(text_mm)


# ══════════════════════════════════════════════════════════════════════
# RotationHandleItem —— 旋转手柄 (ROIRectItem 的子 item)
# ══════════════════════════════════════════════════════════════════════
class RotationHandleItem(QGraphicsEllipseItem):
    """矩形 ROI 的旋转手柄 —— 可拖拽旋转。"""

    rotation_dragged = Signal(float)  # 新的角度值

    def __init__(self, radius=6, parent=None):
        super().__init__(-radius, -radius, radius * 2, radius * 2, parent)
        self._radius = radius
        self._dragging = False
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor("#ffffff")))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(QColor("#f0f0f0")))
        super().hoverLeaveEvent(event)


# ══════════════════════════════════════════════════════════════════════
# ROIRectItem —— 矩形 ROI (支持旋转)
# ══════════════════════════════════════════════════════════════════════
class ROIRectItem(QGraphicsObject):
    """矩形 ROI 区域 —— 支持旋转角度。"""

    roi_selected = Signal(int)  # roi_number

    def __init__(self, roi_data: dict, parent=None):
        super().__init__(parent)
        self._number = roi_data["number"]
        self._color = QColor(roi_data["color"])
        self._x, self._y, self._w, self._h = roi_data["coords"]
        self._angle = roi_data.get("angle", 0.0)

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

        # 子 item: 旋转手柄
        self._handle = RotationHandleItem(6, self)
        self._handle.setPen(QPen(self._color, 2))
        self._handle.setBrush(QBrush(QColor("#f0f0f0")))
        self._update_handle_pos()

    # ── 属性 ──
    @property
    def roi_number(self):
        return self._number

    @property
    def angle(self):
        return self._angle

    def set_angle(self, deg: float):
        self._angle = deg
        self.prepareGeometryChange()
        self._update_handle_pos()
        self.update()

    def coords(self):
        return (self._x, self._y, self._w, self._h)

    # ── Qt overrides ──
    def boundingRect(self):
        # 包含旋转后的区域 + 手柄
        extra = 40
        return QRectF(-self._w / 2 - extra, -self._h / 2 - extra,
                       self._w + extra * 2, self._h + extra * 2)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)

        # 变换到矩形中心
        cx, cy = self._x + self._w / 2.0, self._y + self._h / 2.0
        painter.translate(cx, cy)
        if abs(self._angle) > 0.01:
            painter.rotate(self._angle)

        w, h = self._w, self._h

        # 矩形边框 (虚线)
        pen = QPen(self._color, 2, Qt.DashLine)
        pen.setDashPattern([6, 4])
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(-w / 2, -h / 2, w, h))

        # 标签
        painter.setPen(QPen(self._color, 1))
        painter.setFont(_bold_font())
        painter.drawText(QPointF(-w / 2 + 4, -h / 2 + 14), f"ROI #{self._number}")

        # 手柄连接线 (虚线)
        hh = h / 2
        handle_offset = 18  # scene pixels above rect
        pen2 = QPen(self._color, 1, Qt.DashLine)
        pen2.setDashPattern([3, 3])
        painter.setPen(pen2)
        painter.drawLine(QPointF(0, 0), QPointF(0, -hh - handle_offset))

    def _update_handle_pos(self):
        cx, cy = self._x + self._w / 2.0, self._y + self._h / 2.0
        hh = self._h / 2.0
        handle_offset = 18.0

        # 手柄在矩形上方 (旋转后)
        rad = math.radians(-self._angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        hx = cx - sin_a * (hh + handle_offset)
        hy = cy - cos_a * (hh + handle_offset)

        self._handle.setPos(hx - self._x - self._w / 2.0,
                            hy - self._y - self._h / 2.0)

    def shape(self):
        """精确命中区域。"""
        path = QPainterPath()
        path.addRect(QRectF(-self._w / 2, -self._h / 2, self._w, self._h))
        return path

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange and value:
            self.roi_selected.emit(self._number)
        return super().itemChange(change, value)


# ══════════════════════════════════════════════════════════════════════
# ROICircleItem —— 圆形 ROI (支持扇形)
# ══════════════════════════════════════════════════════════════════════
class ROICircleItem(QGraphicsObject):
    """圆形 ROI 区域 —— 支持环形带和扇形。"""

    roi_selected = Signal(int)

    def __init__(self, roi_data: dict, parent=None):
        super().__init__(parent)
        self._number = roi_data["number"]
        self._color = QColor(roi_data["color"])
        self._cx, self._cy, self._r = roi_data["coords"]
        self._inner_ratio = roi_data.get("inner_ratio", 0.5)
        self._start_angle = roi_data.get("start_angle", 0.0)
        self._end_angle = roi_data.get("end_angle", 360.0)

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    @property
    def roi_number(self):
        return self._number

    def set_params(self, key: str, value: float):
        if key == "inner_ratio":
            self._inner_ratio = value
        elif key == "start_angle":
            self._start_angle = value
        elif key == "end_angle":
            self._end_angle = value
        self.prepareGeometryChange()
        self.update()

    def boundingRect(self):
        r = self._r + 5
        return QRectF(self._cx - r, self._cy - r, r * 2, r * 2)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)

        r = self._r
        cx, cy = self._cx, self._cy
        inner_r = r * self._inner_ratio

        # 外圆
        pen_outer = QPen(self._color, 2)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # 内圆 (虚线)
        if inner_r > 3:
            pen_inner = QPen(self._color, 1, Qt.DashLine)
            pen_inner.setDashPattern([4, 4])
            painter.setPen(pen_inner)
            painter.drawEllipse(QPointF(cx, cy), inner_r, inner_r)

        # 扇形角度线
        sa, ea = self._start_angle, self._end_angle
        if ea - sa < 359.5:
            for angle_deg in (sa, ea):
                rad = math.radians(90 - angle_deg)
                dx = r * math.cos(rad)
                dy = -r * math.sin(rad)
                pen_ang = QPen(self._color, 2, Qt.DashLine)
                pen_ang.setDashPattern([3, 3])
                painter.setPen(pen_ang)
                painter.drawLine(QPointF(cx, cy), QPointF(cx + dx, cy + dy))

            # 扇形填充 (半透明)
            start_16th = int(-ea * 16 / 360)  # Qt: 1/16 度单位, 顺时针
            span_16th = int((ea - sa) * 16 / 360)
            fill_color = QColor(self._color)
            fill_color.setAlpha(50)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(fill_color))
            painter.drawPie(QRectF(cx - r, cy - r, r * 2, r * 2),
                            start_16th, span_16th)

            # 内圆镂空
            if inner_r > 3:
                painter.setBrush(QBrush(QColor("#ecf0f1")))
                painter.drawEllipse(QPointF(cx, cy), inner_r, inner_r)

        # 标签
        painter.setPen(QPen(self._color, 1))
        painter.setFont(_bold_font())
        label_rad = math.radians(90 - sa - 10)
        lx = cx + r * 0.85 * math.cos(label_rad)
        ly = cy - r * 0.85 * math.sin(label_rad)
        painter.drawText(QPointF(lx - 10, ly + 4), f"#{self._number}")

    def shape(self):
        path = QPainterPath()
        path.addEllipse(QPointF(self._cx, self._cy), self._r, self._r)
        return path

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange and value:
            self.roi_selected.emit(self._number)
        return super().itemChange(change, value)


# ══════════════════════════════════════════════════════════════════════
# ROIPreviewItem —— 拖拽预览
# ══════════════════════════════════════════════════════════════════════
class ROIPreviewItem(QGraphicsItem):
    """ROI 拖拽中的临时预览 —— 轻量，无信号。"""

    def __init__(self, start: QPointF, end: QPointF, shape: str, parent=None):
        super().__init__(parent)
        self._start = start
        self._end = end
        self._shape = shape  # "rect" or "circle"
        self._color = QColor("#e67e22")
        self._pen = QPen(self._color, 2, Qt.DashLine)
        self._pen.setDashPattern([4, 4])

    def update_end(self, end: QPointF):
        self._end = end
        self.prepareGeometryChange()
        self.update()

    def boundingRect(self):
        x0 = min(self._start.x(), self._end.x())
        y0 = min(self._start.y(), self._end.y())
        x1 = max(self._start.x(), self._end.x())
        y1 = max(self._start.y(), self._end.y())
        return QRectF(x0 - 2, y0 - 2, x1 - x0 + 4, y1 - y0 + 4)

    def paint(self, painter, option, widget):
        painter.setPen(self._pen)
        painter.setBrush(Qt.NoBrush)

        if self._shape == "rect":
            x0 = min(self._start.x(), self._end.x())
            y0 = min(self._start.y(), self._end.y())
            w = abs(self._end.x() - self._start.x())
            h = abs(self._end.y() - self._start.y())
            painter.drawRect(QRectF(x0, y0, w, h))
        elif self._shape == "circle":
            cx, cy = self._start.x(), self._start.y()
            r = math.sqrt((self._end.x() - cx) ** 2 + (self._end.y() - cy) ** 2)
            painter.drawEllipse(QPointF(cx, cy), r, r)
