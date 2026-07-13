import sys
sys.path.insert(0, r'C:\Users\user\Documents\imageTools')

from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

from PySide6.QtCore import QPointF, QRectF
from test.roi.shapes.rectangle import RectangleShape
from test.roi.shapes.circle import CircleShape
from test.roi.shapes.polygon import PolygonShape
from test.roi.shapes.registry import ShapeRegistry
from test.roi.hit_test import HitTestEngine
import math

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f'  PASS: {name}')
    else:
        failed += 1
        print(f'  FAIL: {name}')

print('[Registry]')
check('rect registered', ShapeRegistry.get('rect') is not None)
check('circle registered', ShapeRegistry.get('circle') is not None)
check('polygon registered', ShapeRegistry.get('polygon') is not None)

print('[Rectangle]')
r = RectangleShape(QRectF(100, 100, 200, 150))
c = r.center()
check('center inside', r.contains_point(c))
check('center correct', abs(c.x() - 200) < 1 and abs(c.y() - 175) < 1)
r.move(50, 50)
c = r.center()
check('move works', abs(c.x() - 250) < 1)
check('center inside after move', r.contains_point(c))
r.resize_by_control(0, QPointF(100, 100))
check('resize works', r.contains_point(r.center()))
r.rotate_by(45)
check('center inside after rotate', r.contains_point(r.center()))
for deg in range(0, 360, 10):
    r.rotate_by(10)
check('center inside after full rotation', r.contains_point(r.center()))
r2 = RectangleShape(QRectF(200, 200, 100, 80))
r2.update_from_drag(QPointF(150, 150), QPointF(350, 300))
check('update_from_drag works', abs(r2.center().x() - 250) < 1)

print('[Circle]')
circ = CircleShape(QPointF(400, 300), 50)
check('circle contains center', circ.contains_point(circ.center()))
check('circle edge_hit', circ.edge_hit(QPointF(450, 300)))
circ.move(10, 20)
check('circle move works', abs(circ.center().x() - 410) < 1)
circ.resize_by_control(0, QPointF(460, 320))
check('circle resize works', circ.radius > 40)

print('[Polygon]')
poly = PolygonShape()
for p in [QPointF(100,100), QPointF(200,100), QPointF(200,200), QPointF(100,200)]:
    poly.add_vertex(p)
check('polygon contains center', poly.contains_point(poly.center()))
poly.move(50, 50)
check('polygon move works', abs(poly.center().x() - 200) < 1)
poly2 = PolygonShape()
for p in [QPointF(200,200), QPointF(300,150), QPointF(400,200), QPointF(350,300), QPointF(250,300)]:
    poly2.add_vertex(p)
poly2.rotate_by(30)
check('polygon rotate works', poly2.contains_point(poly2.center()))

print('[Rotation Smooth]')
r3 = RectangleShape(QRectF(200, 200, 100, 80))
jumps = 0
prev_angle = None
for i in range(120):
    r3.rotate_by(3)
    h = r3.rotation_handle_pos()
    dx = h.x() - r3.center().x()
    dy = h.y() - r3.center().y()
    angle = math.degrees(math.atan2(dy, dx))
    if prev_angle is not None:
        diff = angle - prev_angle
        if diff > 180: diff -= 360
        if diff < -180: diff += 360
        if abs(diff) > 20:
            jumps += 1
    prev_angle = angle
check('rect rotation no jumps', jumps == 0)

print('[Hit Test]')
engine = HitTestEngine()
r4 = RectangleShape(QRectF(100, 100, 200, 150))
r4.selected = True
circ2 = CircleShape(QPointF(500, 300), 50)
shape, hit = engine.hit_test(QPointF(200, 175), [r4, circ2])
check('hit test selects rect', shape is r4 and hit == 'fill')

print(f'Results: {passed} passed, {failed} failed')
if failed > 0:
    sys.exit(1)
print('ALL TESTS PASSED')
