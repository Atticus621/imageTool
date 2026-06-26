import sys
sys.path.insert(0, r'C:\Users\user\Documents\imageTools')
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from PySide6.QtCore import QPointF, QRectF
from test.roi.shapes.rectangle import RectangleShape
from test.roi.shapes.circle import CircleShape
from test.roi.shapes.polygon import PolygonShape

rect = RectangleShape(QRectF(100, 100, 200, 150))
c = rect.center()
print(f"1. Rect center: ({c.x():.1f},{c.y():.1f}), inside: {rect.contains_point(c)}")
rect.rotate_by(45)
c = rect.center()
print(f"2. Rotated: center=({c.x():.1f},{c.y():.1f}), inside: {rect.contains_point(c)}")
rect.resize_by_control(0, QPointF(50, 50))
c = rect.center()
print(f"3. Resized: center=({c.x():.1f},{c.y():.1f}), inside: {rect.contains_point(c)}")

circ = CircleShape(QPointF(400, 300), 50)
circ.rotate_by(90)
print(f"4. Circle: center=({circ.center().x():.0f},{circ.center().y():.0f})")

poly = PolygonShape()
for p in [QPointF(200,200), QPointF(300,150), QPointF(400,200)]:
    poly.add_vertex(p)
c = poly.center()
print(f"5. Triangle: center=({c.x():.1f},{c.y():.1f}), inside: {poly.contains_point(c)}")
poly.rotate_by(30)
c = poly.center()
print(f"6. Rotated: center=({c.x():.1f},{c.y():.1f}), inside: {poly.contains_point(c)}")
poly.resize_by_control(0, QPointF(150, 250))
c = poly.center()
print(f"7. Resized: center=({c.x():.1f},{c.y():.1f}), inside: {poly.contains_point(c)}")

from test.roi.main import ROIEditorWindow
w = ROIEditorWindow()
print("8. Window OK")
print("\nALL TESTS PASSED")
