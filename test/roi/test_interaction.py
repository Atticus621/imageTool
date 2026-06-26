import sys
sys.path.insert(0, r'C:\Users\user\Documents\imageTools')
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QKeyEvent
from test.roi.canvas import ROICanvas
from test.roi.interactions.state_machine import InteractionMode

canvas = ROICanvas()
errors = []

def check(name, condition):
    if condition:
        print(f'  PASS {name}')
    else:
        errors.append(name)
        print(f'  FAIL {name}')

def sim_draw(canvas, x1, y1, x2, y2, tool='rect'):
    old = canvas._current_tool
    canvas._current_tool = tool
    canvas.simulate_mouse_drag(QPointF(x1, y1), QPointF(x2, y2))
    canvas._current_tool = old

def sim_delete(canvas):
    e = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
    canvas.keyPressEvent(e)

print('[Drawing]')
canvas.set_tool('rect')
sim_draw(canvas, 50, 50, 250, 200)
check('draw rect 1', len(canvas.shapes) == 1)
sim_draw(canvas, 300, 100, 500, 250)
check('draw rect 2', len(canvas.shapes) == 2)
sim_draw(canvas, 100, 300, 200, 400)
check('draw rect 3', len(canvas.shapes) == 3)
canvas.set_tool('circle')
sim_draw(canvas, 600, 300, 650, 300, 'circle')
check('draw circle', len(canvas.shapes) == 4)

print('[Mode]')
check('IDLE after draws', canvas._mode == InteractionMode.IDLE)

print('[Select]')
canvas.set_tool('select')
canvas.simulate_mouse_click(QPointF(150, 125))
check('selected', canvas.selected_shape is not None)
check('selected type', canvas.selected_shape.get_state_dict()['type'] == 'rectangle')

print('[Move]')
old_center = canvas.selected_shape.center()
canvas.simulate_mouse_drag(QPointF(150, 125), QPointF(200, 175))
new_center = canvas.selected_shape.center()
check('moved', abs(new_center.x() - old_center.x()) > 10)

print('[Resize Corner]')
canvas.simulate_mouse_drag(QPointF(50, 50), QPointF(30, 30))
check('resized', canvas.selected_shape is not None)

print('[Delete]')
sim_delete(canvas)
check('deleted', len(canvas.shapes) == 3)

print('[Overlap Click]')
canvas.simulate_mouse_click(QPointF(350, 175))
check('overlap select', canvas.selected_shape is not None)

print('[Rotate]')
canvas.simulate_mouse_drag(QPointF(400, 70), QPointF(450, 120))
check('rotated', canvas.selected_shape is not None)

print(f'\nShapes: {len(canvas.shapes)}')
for i, s in enumerate(canvas.shapes):
    st = s.get_state_dict()
    print(f'  {i}: {st["type"]} center={st["center"]}')

print(f'\nErrors: {len(errors)}')
for e in errors:
    print(f'  {e}')
if not errors:
    print('ALL TESTS PASSED')
else:
    sys.exit(1)
