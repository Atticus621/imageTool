"""Test that angle unwrapping prevents jumps when crossing the atan2 ±180° boundary."""
import math
from PySide6.QtCore import QPointF
from shapes.sector import SectorShape

print('=== Test _unwrap_angle ===')
s = SectorShape(QPointF(200, 200), 100, 0, 90)

# Test 1: Crossing atan2 +180/-180 boundary clockwise (170° -> 190°)
result = s._unwrap_angle(-170.0, 170.0)  # -170 is atan2 for 190°
print(f'Cross +180 CW: prev=170, new_atan2=-170 -> unwrapped={result} (expected ~190)')
assert abs(result - 190.0) < 0.01, f'Expected ~190, got {result}'

# Test 2: Crossing atan2 +180/-180 boundary counter-clockwise
result = s._unwrap_angle(170.0, -170.0)
print(f'Cross +180 CCW: prev=-170, new_atan2=170 -> unwrapped={result} (expected ~-190)')
assert abs(result - (-190.0)) < 0.01, f'Expected ~-190, got {result}'

# Test 3: No crossing, small movement
result = s._unwrap_angle(45.0, 30.0)
print(f'No cross: prev=30, new=45 -> unwrapped={result} (expected 45)')
assert abs(result - 45.0) < 0.01

# Test 4: No crossing, just negative values
result = s._unwrap_angle(-45.0, -90.0)
print(f'Negative: prev=-90, new=-45 -> unwrapped={result} (expected -45)')
assert abs(result - (-45.0)) < 0.01

print()
print('=== Test resize_by_control crossing boundary ===')
# Simulate dragging start angle control point across +180 boundary
s = SectorShape(QPointF(200, 200), 100, 170, 200)  # start=170°, end=200°
print(f'Before: start_angle={s.start_angle}, start_raw={s._start_angle_raw}')
print(f'        end_angle={s.end_angle}, end_raw={s._end_angle_raw}')

# Drag start angle to 190° (which is -170 in atan2). Position: left side of center
x = 200 + 100 * math.cos(math.radians(190))
y = 200 - 100 * math.sin(math.radians(190))
s.resize_by_control(2, QPointF(x, y))
print(f'After drag to 190°: start_angle={s.start_angle:.1f}, start_raw={s._start_angle_raw:.1f}')
# start_angle should be 190 (or close), and raw should be continuous (near 190, not -170)
assert 185 < s._start_angle < 195, f'Expected start_angle ~190, got {s.start_angle}'
assert 185 < s._start_angle_raw < 195, f'Expected raw ~190, got {s._start_angle_raw}'

# Now drag end angle to 170° (crossing back CCW)
x2 = 200 + 100 * math.cos(math.radians(170))
y2 = 200 - 100 * math.sin(math.radians(170))
s.resize_by_control(3, QPointF(x2, y2))
print(f'After drag end to 170°: end_angle={s.end_angle:.1f}, end_raw={s._end_angle_raw:.1f}')
# end should be 170, but raw should be continuous from 200 (so 170, not -190)
assert 165 < s._end_angle < 175, f'Expected end_angle ~170, got {s.end_angle}'
assert 165 < s._end_angle_raw < 175, f'Expected raw ~170 (continuous from 200), got {s._end_angle_raw}'

print()
print('=== Test that span stays small after crossing ===')
span = s._end_angle_raw - s._start_angle_raw
print(f'Span: {span:.1f}° (should be small, not ~±340°)')
# Span should be small, not ~340° or ~-340°
assert abs(span) < 30, f'Span should be small, got {span}'

print()
print('ALL UNWRAP TESTS PASSED')
