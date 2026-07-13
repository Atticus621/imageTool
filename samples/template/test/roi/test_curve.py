import sys
sys.path.insert(0, r'C:\Users\user\Documents\imageTools')

from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

from PySide6.QtCore import QPointF
from test.roi.shapes.curve import CurveShape
from test.roi.shapes.registry import ShapeRegistry

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name}")
        failed += 1


def test_curve_creation():
    print("\n--- test_curve_creation ---")
    curve = CurveShape()
    check("shape_type", curve.shape_type == "curve")
    check("draw_mode", curve.draw_mode == "click_add")
    check("vertex_count zero", curve.vertex_count == 0)


def test_curve_add_vertex():
    print("\n--- test_curve_add_vertex ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    check("1 vertex", curve.vertex_count == 1)
    curve.add_vertex(QPointF(200, 200))
    check("2 vertices", curve.vertex_count == 2)
    curve.add_vertex(QPointF(300, 100))
    check("3 vertices", curve.vertex_count == 3)


def test_curve_auto_handles():
    print("\n--- test_curve_auto_handles ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.add_vertex(QPointF(200, 200))
    check("handles_out computed", curve._handles_out[0].x() != 0 or curve._handles_out[0].y() != 0)
    check("handles_in computed", curve._handles_in[1].x() != 0 or curve._handles_in[1].y() != 0)


def test_curve_center():
    print("\n--- test_curve_center ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.add_vertex(QPointF(200, 200))
    c = curve.center()
    check("center x", 140 < c.x() < 160)
    check("center y", 140 < c.y() < 160)


def test_curve_bounding_rect():
    print("\n--- test_curve_bounding_rect ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.add_vertex(QPointF(200, 300))
    br = curve.bounding_rect()
    check("width > 0", br.width() > 0)
    check("height > 0", br.height() > 0)


def test_curve_move():
    print("\n--- test_curve_move ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.add_vertex(QPointF(200, 200))
    c_before = curve.center()
    curve.move(50, 50)
    c_after = curve.center()
    check("move dx", abs(c_after.x() - c_before.x() - 50) < 1)
    check("move dy", abs(c_after.y() - c_before.y() - 50) < 1)


def test_curve_control_points():
    print("\n--- test_curve_control_points ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.add_vertex(QPointF(200, 200))
    curve.selected = True
    cps = curve.control_points()
    check("control points >= 2", len(cps) >= 2)


def test_curve_resize_anchor():
    print("\n--- test_curve_resize_anchor ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.add_vertex(QPointF(200, 200))
    curve.resize_by_control(0, QPointF(150, 150))
    check("anchor moved x", abs(curve._anchors[0].x() - 150) < 1)
    check("anchor moved y", abs(curve._anchors[0].y() - 150) < 1)


def test_curve_resize_handle():
    print("\n--- test_curve_resize_handle ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.add_vertex(QPointF(200, 200))
    n = len(curve._anchors)
    curve.resize_by_control(n + 1, QPointF(250, 250))
    check("handle moved", abs(curve._handles_out[0].x() - 150) < 1)


def test_curve_preview():
    print("\n--- test_curve_preview ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.set_preview_point(QPointF(200, 200))
    check("preview set", curve._preview_point is not None)
    curve.set_preview_point(None)
    check("preview cleared", curve._preview_point is None)


def test_curve_state_dict():
    print("\n--- test_curve_state_dict ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.add_vertex(QPointF(200, 200))
    state = curve.get_state_dict()
    check("type", state["type"] == "curve")
    check("anchor_count", state["anchor_count"] == 2)
    check("anchors len", len(state["anchors"]) == 2)
    check("handles_in len", len(state["handles_in"]) == 2)
    check("handles_out len", len(state["handles_out"]) == 2)


def test_curve_sample_curve():
    print("\n--- test_curve_sample_curve ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.add_vertex(QPointF(200, 200))
    sampled = curve._sample_curve(steps=10)
    check("sampled points >= 10", len(sampled) >= 10)


def test_curve_contains_point():
    print("\n--- test_curve_contains_point ---")
    curve = CurveShape()
    curve.add_vertex(QPointF(100, 100))
    curve.add_vertex(QPointF(200, 100))
    curve.add_vertex(QPointF(200, 200))
    curve.add_vertex(QPointF(100, 200))
    curve.add_vertex(QPointF(100, 100))
    result = curve.contains_point(QPointF(150, 150))
    check("contains_point returns bool", isinstance(result, bool))


def test_curve_registry():
    print("\n--- test_curve_registry ---")
    cls = ShapeRegistry.get("curve")
    check("registered", cls is CurveShape)


if __name__ == "__main__":
    test_curve_creation()
    test_curve_add_vertex()
    test_curve_auto_handles()
    test_curve_center()
    test_curve_bounding_rect()
    test_curve_move()
    test_curve_control_points()
    test_curve_resize_anchor()
    test_curve_resize_handle()
    test_curve_preview()
    test_curve_state_dict()
    test_curve_sample_curve()
    test_curve_contains_point()
    test_curve_registry()

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
