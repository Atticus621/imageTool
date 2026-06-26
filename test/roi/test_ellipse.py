import sys
sys.path.insert(0, r'C:\Users\user\Documents\imageTools')
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from PySide6.QtCore import QPointF, QRectF
from test.roi.shapes.ellipse import EllipseShape
import math

print('[Ellipse - Basic]')
e = EllipseShape(QPointF(200, 200), 100, 60)
print(f'  Center: ({e.center().x():.0f},{e.center().y():.0f})')
print(f'  rx={e.rx:.0f}, ry={e.ry:.0f}')
print(f'  Center inside: {e.contains_point(e.center())}')

print('\n[Ellipse - Control Points]')
cps = e.control_points()
print(f'  N: ({cps[0].x():.0f},{cps[0].y():.0f})')
print(f'  E: ({cps[1].x():.0f},{cps[1].y():.0f})')
print(f'  S: ({cps[2].x():.0f},{cps[2].y():.0f})')
print(f'  W: ({cps[3].x():.0f},{cps[3].y():.0f})')

print('\n[Ellipse - Resize by Control]')
e.resize_by_control(0, QPointF(200, 150))
print(f'  After resize N to y=150: rx={e.rx:.0f}, ry={e.ry:.0f}')
assert abs(e.ry - 50) < 1, f"Expected ry=50, got {e.ry}"
e.resize_by_control(1, QPointF(320, 200))
print(f'  After resize E to x=320: rx={e.rx:.0f}, ry={e.ry:.0f}')
assert abs(e.rx - 120) < 1, f"Expected rx=120, got {e.rx}"

print('\n[Ellipse - Edge Hit]')
e2 = EllipseShape(QPointF(200, 200), 100, 60)
assert e2.edge_hit(QPointF(300, 200)), "Edge at (300,200) should hit"
assert e2.edge_hit(QPointF(200, 140)), "Edge at (200,140) should hit"
assert not e2.edge_hit(QPointF(200, 200)), "Center should not hit edge"

print('\n[Ellipse - Rotation]')
e3 = EllipseShape(QPointF(200, 200), 100, 60)
e3.rotate_by(45)
print(f'  Rotation: {e3._rotation_deg:.1f}°')
assert e3.contains_point(QPointF(200, 200)), "Center should be inside after rotation"
cps_rot = e3.control_points()
print(f'  Rotated N: ({cps_rot[0].x():.0f},{cps_rot[0].y():.0f})')

print('\n[Ellipse - Move]')
e4 = EllipseShape(QPointF(200, 200), 100, 60)
e4.move(50, 30)
assert abs(e4.center().x() - 250) < 1
assert abs(e4.center().y() - 230) < 1
print(f'  After move: center=({e4.center().x():.0f},{e4.center().y():.0f})')

print('\n[Ellipse - Update from Drag]')
e5 = EllipseShape(QPointF(0, 0), 0, 0)
e5.update_from_drag(QPointF(100, 100), QPointF(250, 180))
print(f'  center=({e5.center().x():.0f},{e5.center().y():.0f}) rx={e5.rx:.0f} ry={e5.ry:.0f}')
assert abs(e5.rx - 150) < 1
assert abs(e5.ry - 80) < 1

print('\n[Ellipse - Rotation Preservation on Resize]')
e6 = EllipseShape(QPointF(200, 200), 100, 60)
e6.rotate_by(30)
angle_before = e6._rotation_deg
e6.resize_by_control(0, QPointF(200, 150))
angle_after = e6._rotation_deg
assert abs(angle_before - angle_after) < 0.01, f"Rotation changed: {angle_before} -> {angle_after}"
print(f'  Rotation preserved: {angle_after:.1f}°')

print('\nDone - ALL TESTS PASSED')
