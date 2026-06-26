from PySide6.QtCore import QPointF

try:
    from .utils import distance
except ImportError:
    from utils import distance


class HitTestEngine:
    CP_RADIUS = 8.0
    HANDLE_RADIUS = 10.0

    def __init__(self):
        self._cycle_index = 0
        self._last_click_pos = None

    def reset_cycle(self):
        self._cycle_index = 0
        self._last_click_pos = None

    def hit_test(self, pos: QPointF, shapes: list) -> tuple:
        if self._last_click_pos is None or distance(pos, self._last_click_pos) > 10:
            self._cycle_index = 0
        else:
            self._cycle_index += 1
        self._last_click_pos = pos

        try:
            from .shapes.rectangle import RectangleShape
            from .shapes.circle import CircleShape
            from .shapes.polygon import PolygonShape
        except ImportError:
            from shapes.rectangle import RectangleShape
            from shapes.circle import CircleShape
            from shapes.polygon import PolygonShape

        candidates = []
        for shape in reversed(shapes):
            has_rotation = isinstance(shape, (RectangleShape, PolygonShape))
            if has_rotation and shape.selected:
                if shape.rotation_hit(pos):
                    return (shape, "rotation_handle")

            for i, cp in enumerate(shape.control_points()):
                if distance(pos, cp) < self.CP_RADIUS:
                    return (shape, f"control_point:{i}")

            if isinstance(shape, RectangleShape):
                edge = shape.find_hit_edge(pos)
                if edge:
                    candidates.append((shape, f"edge:{edge}"))

            if isinstance(shape, CircleShape) and shape.edge_hit(pos):
                candidates.append((shape, "edge:circumference"))

            if shape.contains_point(pos):
                candidates.append((shape, "fill"))

        if not candidates:
            return (None, None)

        idx = self._cycle_index % len(candidates)
        return candidates[idx]
