import sys
sys.path.insert(0, r'C:\Users\user\Documents\imageTools')
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from PySide6.QtCore import QPointF, QRectF
from test.roi.shapes.sector import SectorShape
import math

print('[Sector - Basic]')
s = SectorShape(QPointF(200, 200), 100, 0, 90)
print(f'  Center: ({s.center().x():.0f},{s.center().y():.0f})')
print(f'  Radius: {s.radius:.0f}')
print(f'  Start angle: {s.start_angle:.0f}°')
print(f'  End angle: {s.end_angle:.0f}°')

print('\n[Sector - Contains Point]')
assert s.contains_point(QPointF(200, 200)), "Center should be inside"
assert s.contains_point(QPointF(250, 200)), "Point on 0° should be inside"
assert s.contains_point(QPointF(200, 150)), "Point on 90° should be inside"
assert not s.contains_point(QPointF(150, 200)), "Point on 180° should be outside"
assert not s.contains_point(QPointF(200, 250)), "Point on 270° should be outside"

print('\n[Sector - Control Points]')
cps = s.control_points()
print(f'  Center: ({cps[0].x():.0f},{cps[0].y():.0f})')
print(f'  Radius: ({cps[1].x():.0f},{cps[1].y():.0f})')
print(f'  Start: ({cps[2].x():.0f},{cps[2].y():.0f})')
print(f'  End: ({cps[3].x():.0f},{cps[3].y():.0f})')

print('\n[Sector - Edge Hit]')
assert s.edge_hit(QPointF(300, 200)), "Edge at (300,200) should hit"
assert s.edge_hit(QPointF(200, 100)), "Edge at (200,100) should hit"
assert not s.edge_hit(QPointF(200, 200)), "Center should not hit edge"

print('\n[Sector - Resize by Control]')
s.resize_by_control(1, QPointF(250, 200))
print(f'  After resize radius to 50: radius={s.radius:.0f}')
assert abs(s.radius - 50) < 1, f"Expected radius=50, got {s.radius}"

s.resize_by_control(2, QPointF(200, 150))
print(f'  After resize start to 90°: start={s.start_angle:.0f}°')

s.resize_by_control(3, QPointF(150, 200))
print(f'  After resize end to 180°: end={s.end_angle:.0f}°')

print('\n[Sector - Move]')
s2 = SectorShape(QPointF(200, 200), 100, 0, 90)
s2.move(50, 30)
assert abs(s2.center().x() - 250) < 1
assert abs(s2.center().y() - 230) < 1
print(f'  After move: center=({s2.center().x():.0f},{s2.center().y():.0f})')

print('\n[Sector - Different Angles]')
s4 = SectorShape(QPointF(200, 200), 100, 45, 135)
assert s4.contains_point(QPointF(200, 150)), "90° should be inside"
assert not s4.contains_point(QPointF(250, 200)), "0° should be outside"
print(f'  45-135° sector: 90° inside, 0° outside')

s5 = SectorShape(QPointF(200, 200), 100, 270, 90)
assert s5.contains_point(QPointF(200, 250)), "270° should be inside"
assert s5.contains_point(QPointF(200, 150)), "90° should be inside"
assert not s5.contains_point(QPointF(150, 200)), "180° should be outside"
print(f'  270-90° sector: 270° and 90° inside, 180° outside')

print('\nDone - ALL TESTS PASSED')
