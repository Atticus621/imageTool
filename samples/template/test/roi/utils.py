import math
from PySide6.QtCore import QPointF


def distance(p1: QPointF, p2: QPointF) -> float:
    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()
    return math.sqrt(dx * dx + dy * dy)


def rotate_point(point: QPointF, center: QPointF, angle_deg: float) -> QPointF:
    rad = math.radians(angle_deg)
    dx = point.x() - center.x()
    dy = point.y() - center.y()
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    rx = dx * cos_a - dy * sin_a + center.x()
    ry = dx * sin_a + dy * cos_a + center.y()
    return QPointF(rx, ry)


def shapely_rotate_points(points: list, center: QPointF, angle_deg: float) -> list:
    from shapely import affinity
    from shapely.geometry import LineString
    if len(points) < 2:
        return list(points)
    line = LineString([(p.x(), p.y()) for p in points])
    rotated = affinity.rotate(line, angle_deg, origin=(center.x(), center.y()), use_radians=False)
    return [QPointF(x, y) for x, y in rotated.coords]


def _make_shapely_polygon(vertices: list):
    from shapely.geometry import Polygon
    coords = [(v.x(), v.y()) for v in vertices]
    poly = Polygon(coords)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def shapely_centroid(vertices: list) -> QPointF:
    n = len(vertices)
    if n == 0:
        return QPointF(0, 0)
    if n < 3:
        cx = sum(v.x() for v in vertices) / n
        cy = sum(v.y() for v in vertices) / n
        return QPointF(cx, cy)
    try:
        poly = _make_shapely_polygon(vertices)
        c = poly.centroid
        return QPointF(c.x, c.y)
    except Exception:
        cx = sum(v.x() for v in vertices) / n
        cy = sum(v.y() for v in vertices) / n
        return QPointF(cx, cy)


def shapely_contains(vertices: list, point: QPointF) -> bool:
    if len(vertices) < 3:
        return False
    from shapely.geometry import Point
    poly = _make_shapely_polygon(vertices)
    return poly.contains(Point(point.x(), point.y()))


def polar_angle_group_axis(vertices: list) -> tuple:
    if len(vertices) < 2:
        c = shapely_centroid(vertices)
        return c, QPointF(c.x(), c.y() - 1)

    c = shapely_centroid(vertices)
    indexed = []
    for v in vertices:
        dx = v.x() - c.x()
        dy = v.y() - c.y()
        angle = math.atan2(dy, dx)
        indexed.append((angle, v))
    indexed.sort(key=lambda x: x[0])

    n = len(indexed)
    best_split = 0
    best_diff = float('inf')
    for i in range(n):
        diff = abs(i - (n - i))
        if diff < best_diff:
            best_diff = diff
            best_split = i

    group_a = [indexed[j][1] for j in range(best_split)] or [indexed[0][1]]
    group_b = [indexed[j][1] for j in range(best_split, n)] or [indexed[-1][1]]

    a = QPointF(sum(v.x() for v in group_a) / len(group_a),
                sum(v.y() for v in group_a) / len(group_a))
    b = QPointF(sum(v.x() for v in group_b) / len(group_b),
                sum(v.y() for v in group_b) / len(group_b))

    if distance(a, b) < 0.001:
        return c, QPointF(c.x(), c.y() - 1)
    return a, b
