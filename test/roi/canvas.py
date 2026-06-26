import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QMouseEvent

try:
    from .shapes.base import Shape
    from .shapes.rectangle import RectangleShape
    from .shapes.circle import CircleShape
    from .shapes.polygon import PolygonShape
    from .interactions.state_machine import InteractionMode
    from .hit_test import HitTestEngine
    from .utils import distance
except ImportError:
    from shapes.base import Shape
    from shapes.rectangle import RectangleShape
    from shapes.circle import CircleShape
    from shapes.polygon import PolygonShape
    from interactions.state_machine import InteractionMode
    from hit_test import HitTestEngine
    from utils import distance


class ROICanvas(QWidget):
    shape_created = Signal(Shape)
    shape_selected = Signal(Shape, str)
    shape_changed = Signal(Shape)
    shape_deleted = Signal(dict)
    log_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shapes: list[Shape] = []
        self._mode = InteractionMode.IDLE
        self._current_tool = "rect"
        self._selected_shape: Shape | None = None
        self._hit_engine = HitTestEngine()
        self._drag_start = QPointF()
        self._drag_prev = QPointF()
        self._drag_offset = QPointF()
        self._resize_edge: str | None = None
        self._resize_corner: int = -1
        self._drawing_shape: Shape | None = None
        self._rotation_prev_dir: QPointF | None = None
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._last_shape_id = 0

    @property
    def shapes(self) -> list:
        return list(self._shapes)

    @property
    def selected_shape(self) -> Shape | None:
        return self._selected_shape

    def set_tool(self, tool: str):
        self._current_tool = tool

    def add_shape(self, shape: Shape):
        self._last_shape_id += 1
        shape._id = self._last_shape_id
        self._shapes.append(shape)
        self.shape_created.emit(shape)
        self.log_message.emit(f"CREATE {shape.get_state_dict()}")
        self._validate_shape(shape)
        self.update()

    def remove_shape(self, shape: Shape):
        if shape in self._shapes:
            state = shape.get_state_dict()
            self._shapes.remove(shape)
            if self._selected_shape is shape:
                self._selected_shape = None
                shape.selected = False
            self.shape_deleted.emit(state)
            self.log_message.emit(f"DELETE {state}")
            self.update()

    def select_shape(self, shape: Shape | None, hit_type: str = "api"):
        if self._selected_shape:
            self._selected_shape.selected = False
        self._selected_shape = shape
        if shape:
            shape.selected = True
            self.shape_selected.emit(shape, hit_type)
            self.log_message.emit(f"SELECT {shape.get_state_dict()} hit={hit_type}")
            self._validate_shape(shape)
        self.update()

    def delete_selected(self) -> bool:
        if self._selected_shape:
            state = self._selected_shape.get_state_dict()
            self.remove_shape(self._selected_shape)
            return True
        return False

    def clear_all(self):
        self._shapes.clear()
        self._selected_shape = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(45, 45, 48))
        for shape in self._shapes:
            shape.paint(painter)
        if self._drawing_shape:
            self._drawing_shape.paint(painter)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()

        if self._mode == InteractionMode.DRAWING_POLYGON:
            self._add_polygon_vertex(pos)
            return

        if self._mode == InteractionMode.IDLE:
            shape, hit_type = self._hit_engine.hit_test(pos, self._shapes)
            if shape is None:
                self._start_drawing(pos)
            else:
                self.select_shape(shape, hit_type)
                self._start_interaction(pos, shape, hit_type)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()

        if self._mode == InteractionMode.DRAWING_RECT or self._mode == InteractionMode.DRAWING_CIRCLE:
            self._update_drawing(pos)
        elif self._mode == InteractionMode.DRAWING_POLYGON:
            if self._drawing_shape and isinstance(self._drawing_shape, PolygonShape):
                self._drawing_shape.set_preview_point(pos)
                self.update()
        elif self._mode == InteractionMode.MOVING:
            self._do_move(pos)
        elif self._mode == InteractionMode.RESIZING_EDGE:
            self._do_resize_edge(pos)
        elif self._mode == InteractionMode.RESIZING_CORNER:
            self._do_resize_corner(pos)
        elif self._mode == InteractionMode.ROTATING:
            self._do_rotate(pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._mode in (InteractionMode.DRAWING_RECT, InteractionMode.DRAWING_CIRCLE):
            self._finish_drawing()

        if self._mode != InteractionMode.DRAWING_POLYGON:
            self._mode = InteractionMode.IDLE

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self._mode == InteractionMode.DRAWING_POLYGON:
            self._finish_polygon_drawing()
        else:
            super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._mode == InteractionMode.DRAWING_POLYGON:
                self._finish_polygon_drawing()
        elif event.key() == Qt.Key.Key_Escape:
            if self._mode == InteractionMode.DRAWING_POLYGON:
                self._cancel_polygon_drawing()
        else:
            super().keyPressEvent(event)

    def _start_drawing(self, pos: QPointF):
        if self._current_tool == "select":
            return
        if self._current_tool == "rect":
            self._mode = InteractionMode.DRAWING_RECT
            rect = QRectF(pos, pos)
            self._drawing_shape = RectangleShape(rect)
        elif self._current_tool == "circle":
            self._mode = InteractionMode.DRAWING_CIRCLE
            self._drawing_shape = CircleShape(pos, 0)
        elif self._current_tool == "polygon":
            self._mode = InteractionMode.DRAWING_POLYGON
            self._drawing_shape = PolygonShape()
            self._drawing_shape.add_vertex(pos)
        self._drag_start = pos

    def _update_drawing(self, pos: QPointF):
        if not self._drawing_shape:
            return
        if self._mode == InteractionMode.DRAWING_RECT:
            rect = QRectF(self._drag_start, pos).normalized()
            self._drawing_shape._corners = [
                QPointF(rect.left(), rect.top()),
                QPointF(rect.right(), rect.top()),
                QPointF(rect.right(), rect.bottom()),
                QPointF(rect.left(), rect.bottom()),
            ]
        elif self._mode == InteractionMode.DRAWING_CIRCLE:
            r = distance(pos, self._drag_start)
            self._drawing_shape._radius = r
        self.update()

    def _finish_drawing(self):
        if self._drawing_shape:
            min_size = 5
            is_valid = True
            if isinstance(self._drawing_shape, RectangleShape):
                br = self._drawing_shape.bounding_rect()
                if br.width() < min_size or br.height() < min_size:
                    is_valid = False
            elif isinstance(self._drawing_shape, CircleShape):
                if self._drawing_shape._radius < min_size:
                    is_valid = False
            if is_valid:
                self.add_shape(self._drawing_shape)
            self._drawing_shape = None

    def _add_polygon_vertex(self, pos: QPointF):
        if self._drawing_shape and isinstance(self._drawing_shape, PolygonShape):
            self._drawing_shape.add_vertex(pos)
            self.update()

    def _finish_polygon_drawing(self):
        if self._drawing_shape and isinstance(self._drawing_shape, PolygonShape):
            if self._drawing_shape.vertex_count >= 3:
                self._drawing_shape.set_preview_point(None)
                self.add_shape(self._drawing_shape)
            self._drawing_shape = None
            self._mode = InteractionMode.IDLE
            self.update()

    def _cancel_polygon_drawing(self):
        self._drawing_shape = None
        self._mode = InteractionMode.IDLE
        self.update()

    def _start_interaction(self, pos: QPointF, shape: Shape, hit_type: str):
        self._drag_start = pos
        self._drag_prev = pos

        if hit_type == "rotation_handle":
            self._mode = InteractionMode.ROTATING
            c = shape.center()
            dx = pos.x() - c.x()
            dy = pos.y() - c.y()
            length = math.sqrt(dx * dx + dy * dy)
            self._rotation_prev_dir = QPointF(dx / length, dy / length) if length > 0.001 else QPointF(0, 1)
        elif hit_type.startswith("control_point:"):
            self._mode = InteractionMode.RESIZING_CORNER
            self._resize_corner = int(hit_type.split(":")[1])
        elif hit_type.startswith("edge:"):
            self._mode = InteractionMode.RESIZING_EDGE
            self._resize_edge = hit_type.split(":")[1]
        elif hit_type == "fill":
            self._mode = InteractionMode.MOVING
            c = shape.center()
            self._drag_offset = QPointF(c.x() - pos.x(), c.y() - pos.y())

    def _do_move(self, pos: QPointF):
        if not self._selected_shape:
            return
        c = self._selected_shape.center()
        target = QPointF(pos.x() + self._drag_offset.x(), pos.y() + self._drag_offset.y())
        dx = target.x() - c.x()
        dy = target.y() - c.y()
        self._selected_shape.move(dx, dy)
        self._drag_prev = pos
        self.shape_changed.emit(self._selected_shape)
        self.log_message.emit(f"MOVE {self._selected_shape.get_state_dict()} delta=({dx:.1f},{dy:.1f})")
        self._validate_shape(self._selected_shape)
        self.update()

    def _do_resize_edge(self, pos: QPointF):
        if not self._selected_shape or not self._resize_edge:
            return
        if isinstance(self._selected_shape, RectangleShape):
            dx = pos.x() - self._drag_prev.x()
            dy = pos.y() - self._drag_prev.y()
            self._selected_shape.resize_edge(self._resize_edge, dx, dy)
            self._drag_prev = pos
        elif isinstance(self._selected_shape, CircleShape):
            r = distance(pos, self._selected_shape._center)
            self._selected_shape._radius = max(r, 5.0)
        self.shape_changed.emit(self._selected_shape)
        self.log_message.emit(f"RESIZE edge={self._resize_edge} {self._selected_shape.get_state_dict()}")
        self._validate_shape(self._selected_shape)
        self.update()

    def _do_resize_corner(self, pos: QPointF):
        if not self._selected_shape or self._resize_corner < 0:
            return
        self._selected_shape.resize_by_control(self._resize_corner, pos)
        self.shape_changed.emit(self._selected_shape)
        self.log_message.emit(f"RESIZE corner={self._resize_corner} {self._selected_shape.get_state_dict()}")
        self._validate_shape(self._selected_shape)
        self.update()

    def _do_rotate(self, pos: QPointF):
        if not self._selected_shape:
            return
        c = self._selected_shape.center()
        dx = pos.x() - c.x()
        dy = pos.y() - c.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return
        curr_dir = QPointF(dx / length, dy / length)
        if self._rotation_prev_dir is not None:
            prev = self._rotation_prev_dir
            cross = prev.x() * curr_dir.y() - prev.y() * curr_dir.x()
            dot = prev.x() * curr_dir.x() + prev.y() * curr_dir.y()
            delta = math.degrees(math.atan2(cross, dot))
            self._selected_shape.rotate_by(delta)
        self._rotation_prev_dir = curr_dir
        self.shape_changed.emit(self._selected_shape)
        self.log_message.emit(f"ROTATE {self._selected_shape.get_state_dict()}")
        self._validate_shape(self._selected_shape)
        self.update()

    def _validate_shape(self, shape: Shape):
        state = shape.get_state_dict()
        c = shape.center()
        if c.x() < -1000 or c.x() > 10000 or c.y() < -1000 or c.y() > 10000:
            self.log_message.emit(f"[WARN] Center out of range: {state.get('center')}")
        corners = state.get("corners", []) or state.get("vertices", [])
        for i, pt in enumerate(corners):
            if pt[0] < -1000 or pt[0] > 10000 or pt[1] < -1000 or pt[1] > 10000:
                self.log_message.emit(f"[WARN] Point {i} out of range: {pt}")
        if isinstance(shape, CircleShape):
            if state.get("radius", 0) < 0:
                self.log_message.emit(f"[WARN] Negative radius: {state.get('radius')}")

    def simulate_mouse_move(self, pos: QPointF):
        event = QMouseEvent(QMouseEvent.Type.MouseMove, pos,
                            self.mapToGlobal(pos.toPoint()),
                            Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier)
        self.mouseMoveEvent(event)

    def simulate_mouse_click(self, pos: QPointF):
        press = QMouseEvent(QMouseEvent.Type.MouseButtonPress, pos,
                            self.mapToGlobal(pos.toPoint()),
                            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
        release = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, pos,
                              self.mapToGlobal(pos.toPoint()),
                              Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                              Qt.KeyboardModifier.NoModifier)
        self.mousePressEvent(press)
        self.mouseReleaseEvent(release)

    def simulate_mouse_drag(self, start: QPointF, end: QPointF, shape_type: str | None = None):
        if shape_type:
            old_tool = self._current_tool
            self._current_tool = shape_type

        press = QMouseEvent(QMouseEvent.Type.MouseButtonPress, start,
                            self.mapToGlobal(start.toPoint()),
                            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
        self.mousePressEvent(press)

        steps = 5
        for i in range(1, steps + 1):
            t = i / steps
            pos = QPointF(start.x() + (end.x() - start.x()) * t,
                          start.y() + (end.y() - start.y()) * t)
            move = QMouseEvent(QMouseEvent.Type.MouseMove, pos,
                               self.mapToGlobal(pos.toPoint()),
                               Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                               Qt.KeyboardModifier.NoModifier)
            self.mouseMoveEvent(move)

        release = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, end,
                              self.mapToGlobal(end.toPoint()),
                              Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                              Qt.KeyboardModifier.NoModifier)
        self.mouseReleaseEvent(release)

        if shape_type:
            self._current_tool = old_tool
