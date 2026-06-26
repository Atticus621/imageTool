import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath

try:
    from .base import Shape
    from .registry import ShapeRegistry
    from ..utils import distance, shapely_centroid, shapely_contains, rotate_point
except ImportError:
    from shapes.base import Shape
    from shapes.registry import ShapeRegistry
    from utils import distance, shapely_centroid, shapely_contains, rotate_point


class CurveShape(Shape):
    shape_type = "curve"
    tool_label = "Curve"
    draw_mode = "click_add"
    has_edges = False

    def __init__(self):
        super().__init__()
        self._anchors: list[QPointF] = []
        self._handles_out: list[QPointF] = []
        self._handles_in: list[QPointF] = []
        self._preview_point: QPointF | None = None
        self._has_rotation = True
        self._handle_radius = 4.0

    def _get_vertices_for_rotation(self) -> list:
        return self._get_all_points()

    def _set_vertices_after_rotation(self, vertices: list):
        n = len(self._anchors)
        if len(vertices) < n:
            return
        self._anchors = vertices[:n]
        for i in range(n):
            base = self._anchors[i]
            hi_idx = n + i * 2
            ho_idx = n + i * 2 + 1
            if hi_idx < len(vertices):
                self._handles_in[i] = QPointF(vertices[hi_idx].x() - base.x(),
                                              vertices[hi_idx].y() - base.y())
            if ho_idx < len(vertices):
                self._handles_out[i] = QPointF(vertices[ho_idx].x() - base.x(),
                                               vertices[ho_idx].y() - base.y())

    def _get_all_points(self) -> list:
        points = list(self._anchors)
        for i in range(len(self._anchors)):
            points.append(QPointF(self._anchors[i].x() + self._handles_in[i].x(),
                                  self._anchors[i].y() + self._handles_in[i].y()))
            points.append(QPointF(self._anchors[i].x() + self._handles_out[i].x(),
                                  self._anchors[i].y() + self._handles_out[i].y()))
        return points

    def center(self) -> QPointF:
        if not self._anchors:
            return QPointF(0, 0)
        return shapely_centroid(self._anchors)

    @property
    def vertices(self) -> list:
        return list(self._anchors)

    @property
    def vertex_count(self) -> int:
        return len(self._anchors)

    def add_vertex(self, point: QPointF):
        self._anchors.append(QPointF(point))
        self._handles_in.append(QPointF(0, 0))
        self._handles_out.append(QPointF(0, 0))
        if len(self._anchors) >= 2:
            self._auto_compute_handles()
        if len(self._anchors) == 2:
            self._init_axis_from_vertices(self._anchors)

    def _auto_compute_handles(self):
        n = len(self._anchors)
        if n < 2:
            return
        tension = 0.3
        for i in range(n):
            if i == 0:
                dx = self._anchors[1].x() - self._anchors[0].x()
                dy = self._anchors[1].y() - self._anchors[0].y()
            elif i == n - 1:
                dx = self._anchors[n - 1].x() - self._anchors[n - 2].x()
                dy = self._anchors[n - 1].y() - self._anchors[n - 2].y()
            else:
                dx = self._anchors[i + 1].x() - self._anchors[i - 1].x()
                dy = self._anchors[i + 1].y() - self._anchors[i - 1].y()
            self._handles_in[i] = QPointF(-dx * tension, -dy * tension)
            self._handles_out[i] = QPointF(dx * tension, dy * tension)

    def set_preview_point(self, point: QPointF | None):
        self._preview_point = point

    def bounding_rect(self) -> QRectF:
        if not self._anchors:
            return QRectF()
        all_pts = self._get_all_points()
        xs = [p.x() for p in all_pts]
        ys = [p.y() for p in all_pts]
        return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    def _sample_curve(self, steps: int = 20) -> list:
        points = []
        n = len(self._anchors)
        if n < 2:
            return [QPointF(a) for a in self._anchors]
        for seg in range(n - 1):
            p0 = self._anchors[seg]
            p1 = QPointF(p0.x() + self._handles_out[seg].x(),
                         p0.y() + self._handles_out[seg].y())
            p2 = QPointF(self._anchors[seg + 1].x() + self._handles_in[seg + 1].x(),
                         self._anchors[seg + 1].y() + self._handles_in[seg + 1].y())
            p3 = self._anchors[seg + 1]
            for t_i in range(steps + (1 if seg == 0 else 0)):
                t = t_i / steps if seg == 0 else (t_i + 1) / steps
                if seg > 0 and t_i == 0:
                    continue
                mt = 1 - t
                x = mt ** 3 * p0.x() + 3 * mt ** 2 * t * p1.x() + 3 * mt * t ** 2 * p2.x() + t ** 3 * p3.x()
                y = mt ** 3 * p0.y() + 3 * mt ** 2 * t * p1.y() + 3 * mt * t ** 2 * p2.y() + t ** 3 * p3.y()
                points.append(QPointF(x, y))
        return points

    def contains_point(self, point: QPointF) -> bool:
        sampled = self._sample_curve()
        if len(sampled) < 3:
            return False
        return shapely_contains(sampled, point)

    def control_points(self) -> list:
        if not self.selected:
            return list(self._anchors)
        pts = list(self._anchors)
        for i in range(len(self._anchors)):
            hi = QPointF(self._anchors[i].x() + self._handles_in[i].x(),
                         self._anchors[i].y() + self._handles_in[i].y())
            ho = QPointF(self._anchors[i].x() + self._handles_out[i].x(),
                         self._anchors[i].y() + self._handles_out[i].y())
            if distance(hi, self._anchors[i]) > 1:
                pts.append(hi)
            if distance(ho, self._anchors[i]) > 1:
                pts.append(ho)
        return pts

    def edge_rects(self) -> dict:
        return {}

    def move(self, dx: float, dy: float):
        for i in range(len(self._anchors)):
            self._anchors[i] = QPointF(self._anchors[i].x() + dx, self._anchors[i].y() + dy)

    def resize_by_control(self, index: int, pos: QPointF):
        n = len(self._anchors)
        if index < n:
            old = self._anchors[index]
            dx = pos.x() - old.x()
            dy = pos.y() - old.y()
            self._anchors[index] = QPointF(pos)
            return
        flat_idx = index - n
        anchor_idx = flat_idx // 2
        is_out = flat_idx % 2 == 1
        if 0 <= anchor_idx < n:
            anchor = self._anchors[anchor_idx]
            rel = QPointF(pos.x() - anchor.x(), pos.y() - anchor.y())
            if is_out:
                self._handles_out[anchor_idx] = rel
            else:
                self._handles_in[anchor_idx] = rel

    def paint(self, painter: QPainter):
        if len(self._anchors) < 2:
            self._paint_anchors_only(painter)
            return
        c = self.center()
        path = self._build_path()
        if self.selected:
            painter.setPen(QPen(self.selected_border_color, 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
        else:
            painter.setPen(QPen(self.border_color, 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        self.paint_center_cross(painter, c)
        if self.selected:
            self._paint_handles(painter)
        self.paint_control_points(painter)
        self.paint_rotation_handle(painter, c)
        if self._preview_point and self._anchors:
            last = self._anchors[-1]
            painter.setPen(QPen(QColor(200, 200, 200, 150), 1, Qt.PenStyle.DashLine))
            painter.drawLine(last, self._preview_point)

    def _build_path(self) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(self._anchors[0])
        n = len(self._anchors)
        for seg in range(n - 1):
            p0 = self._anchors[seg]
            p1 = QPointF(p0.x() + self._handles_out[seg].x(),
                         p0.y() + self._handles_out[seg].y())
            p2 = QPointF(self._anchors[seg + 1].x() + self._handles_in[seg + 1].x(),
                         self._anchors[seg + 1].y() + self._handles_in[seg + 1].y())
            p3 = self._anchors[seg + 1]
            path.cubicTo(p1, p2, p3)
        return path

    def _paint_handles(self, painter: QPainter):
        n = len(self._anchors)
        for i in range(n):
            anchor = self._anchors[i]
            hi = QPointF(anchor.x() + self._handles_in[i].x(),
                         anchor.y() + self._handles_in[i].y())
            ho = QPointF(anchor.x() + self._handles_out[i].x(),
                         anchor.y() + self._handles_out[i].y())
            has_in = distance(hi, anchor) > 1
            has_out = distance(ho, anchor) > 1
            if has_in or has_out:
                painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.PenStyle.DashLine))
                if has_in:
                    painter.drawLine(anchor, hi)
                if has_out:
                    painter.drawLine(anchor, ho)
                painter.setPen(QPen(QColor(0, 180, 255), 1.5))
                painter.setBrush(QBrush(QColor(0, 180, 255, 120)))
                if has_in:
                    painter.drawEllipse(hi, self._handle_radius, self._handle_radius)
                if has_out:
                    painter.drawEllipse(ho, self._handle_radius, self._handle_radius)

    def _paint_anchors_only(self, painter: QPainter):
        for a in self._anchors:
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(a, 4, 4)

    def get_state_dict(self) -> dict:
        c = self.center()
        handle = self.rotation_handle_pos()
        return {
            "type": "curve",
            "center": (round(c.x(), 2), round(c.y(), 2)),
            "anchor_count": len(self._anchors),
            "anchors": [(round(a.x(), 2), round(a.y(), 2)) for a in self._anchors],
            "handles_in": [(round(h.x(), 2), round(h.y(), 2)) for h in self._handles_in],
            "handles_out": [(round(h.x(), 2), round(h.y(), 2)) for h in self._handles_out],
            "rotation_handle": (round(handle.x(), 2), round(handle.y(), 2)),
        }


ShapeRegistry.register(CurveShape)
