import sys
sys.path.insert(0, r'C:\Users\user\Documents\imageTools')
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from PySide6.QtCore import QPointF, QRectF
from test.roi.shapes.rectangle import RectangleShape

print('[Corner Resize - No Rotation]')
r = RectangleShape(QRectF(100, 100, 200, 150))
print(f'  Before: corners={[(round(p.x()),round(p.y())) for p in r._corners]}')
print(f'  Center: ({r.center().x():.0f},{r.center().y():.0f}), inside={r.contains_point(r.center())}')

# Drag corner 0 (top-left) to new position
r.resize_by_control(0, QPointF(50, 50))
print(f'  After drag corner 0 to (50,50): corners={[(round(p.x()),round(p.y())) for p in r._corners]}')
print(f'  Center: ({r.center().x():.0f},{r.center().y():.0f}), inside={r.contains_point(r.center())}')

print('\n[Corner Resize - With Rotation]')
r2 = RectangleShape(QRectF(200, 200, 100, 80))
r2.rotate_by(45)
print(f'  Before rotate: corners={[(round(p.x()),round(p.y())) for p in r2._corners]}')
print(f'  Center: ({r2.center().x():.0f},{r2.center().y():.0f}), inside={r2.contains_point(r2.center())}')

# Try to drag corner 0
c0 = r2._corners[0]
print(f'  Corner 0: ({c0.x():.0f},{c0.y():.0f})')
r2.resize_by_control(0, QPointF(c0.x() - 20, c0.y() - 20))
print(f'  After drag corner 0: corners={[(round(p.x()),round(p.y())) for p in r2._corners]}')
c = r2.center()
print(f'  Center: ({c.x():.0f},{c.y():.0f}), inside={r2.contains_point(c)}')

print('\n[Corner Resize - Multiple Operations]')
r3 = RectangleShape(QRectF(100, 100, 200, 150))
for i in range(5):
    r3.resize_by_control(0, QPointF(100 - i*10, 100 - i*10))
    c = r3.center()
    inside = r3.contains_point(c)
    w = r3.bounding_rect().width()
    h = r3.bounding_rect().height()
    print(f'  Step {i}: center=({c.x():.0f},{c.y():.0f}) w={w:.0f} h={h:.0f} inside={inside}')
    if not inside:
        print(f'  BUG: center outside shape!')

print('\n[Corner Resize - Drag Past Opposite]')
r4 = RectangleShape(QRectF(100, 100, 200, 150))
print(f'  Before: corners={[(round(p.x()),round(p.y())) for p in r4._corners]}')
# Drag corner 0 past the opposite corner (corner 2)
r4.resize_by_control(0, QPointF(350, 300))
print(f'  After drag past opposite: corners={[(round(p.x()),round(p.y())) for p in r4._corners]}')
c = r4.center()
print(f'  Center: ({c.x():.0f},{c.y():.0f}), inside={r4.contains_point(c)}')

print('\nDone')
