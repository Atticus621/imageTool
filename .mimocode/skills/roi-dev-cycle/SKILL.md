---
name: roi-dev-cycle
description: >
  ROI shape development and testing workflow for the imageTools project.
  Covers the full edit→cache-clear→relaunch→test cycle for ROI shapes,
  canvas, hit_test, and command_api modules.
---

# ROI Development Cycle

Standard workflow for developing, debugging, and testing ROI shapes in `test/roi/`.

## Key Files

| Module | Path | Role |
|--------|------|------|
| Canvas | `test/roi/canvas.py` | ROI drawing canvas, mouse events, shape management |
| Base Shape | `test/roi/shapes/base.py` | Shape base class, registry, polymorphic interface |
| Rectangle | `test/roi/shapes/rectangle.py` | 4-corner world-space rectangle |
| Circle | `test/roi/shapes/circle.py` | Center+radius circle |
| Polygon | `test/roi/shapes/polygon.py` | click_add polygon, vertex-based |
| Sector | `test/roi/shapes/sector.py` | 3-step drag_multi sector (center→radius→angle) |
| Capsule | `test/roi/shapes/capsule.py` | Two endpoints + radius stadium shape |
| Ellipse | `test/roi/shapes/ellipse.py` | Parametric ellipse with rotation |
| Hit Test | `test/roi/hit_test.py` | Edge/corner/control-point hit detection |
| State Machine | `test/roi/interactions/state_machine.py` | Drawing/editing state transitions |
| Command API | `test/roi/command_api.py` | TCP server (port 9527) + HTTP server (port 9528) |
| Utils | `test/roi/utils.py` | Drawing helpers, geometry utilities |
| Main | `test/roi/main.py` | Entry point, window setup |

## Architecture Rules

- All shapes store geometry in **world coordinates** (no local-space transforms)
- Rectangle uses `_corners: list[QPointF]` (not `QRectF + _rotation`)
- Shape class attributes: `shape_type`, `tool_label`, `draw_mode`, `has_edges`, `_has_rotation`
- Draw modes: `"drag"` (rect/circle/ellipse/capsule), `"click_add"` (polygon), `"drag_multi"` (sector)
- `ShapeRegistry.register(Class)` at module level for zero-modification extension
- Polymorphic methods: `on_click()`, `on_move()`, `paint_guide()`, `resize_edge()`, `resize_by_control()`
- Rotation: `rotate_by(delta_angle)` on all shapes; use cross/dot for delta calculation
- Port label-to-name mapping: Chinese labels → English meta names via `_port_label_to_name`

## Step-by-Step Workflow

### 1. Edit Shape/Canvas Code

Modify the relevant file(s). Common patterns:
- Adding a new shape: create `shapes/xxx.py` + add entry to `shapes.json` + import in `canvas.py`
- Fixing resize: edit `resize_edge()` or `resize_by_control()` in the shape file
- Fixing hit detection: edit `hit_test.py` (check `has_rotation` tuple + `edge_hit` checks)
- Fixing drawing interaction: edit `on_click()`/`on_move()`/`paint_guide()` in shape file

### 2. Clear Cache & Kill Old Process

```powershell
# Clear Python cache
Remove-Item "C:\Users\user\Documents\imageTools\test\roi\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\user\Documents\imageTools\test\roi\shapes\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\user\Documents\imageTools\test\roi\interactions\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue

# Kill old Python processes
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
```

### 3. Launch GUI

```powershell
Start-Process -FilePath "C:\Users\user\miniconda3\envs\claude-imagetool\python.exe" `
  -ArgumentList "C:\Users\user\Documents\imageTools\test\roi\main.py" `
  -WorkingDirectory "C:\Users\user\Documents\imageTools"
```

### 4. Test

**Manual testing**: Use the GUI to draw/edit/rotate shapes.

**TCP API testing** (from another terminal):
```python
import socket, json

def send(cmd):
    s = socket.socket()
    s.connect(('127.0.0.1', 9527))
    s.send(json.dumps(cmd).encode())
    data = s.recv(65536).decode()
    s.close()
    return json.loads(data)

# Examples:
send({"command": "draw_rect", "params": {"x": 100, "y": 100, "width": 200, "height": 150}})
send({"command": "get_state"})
send({"command": "get_detail", "params": {"index": 0}})
send({"command": "rotate", "params": {"index": 0, "angle": 45}})
send({"command": "resize", "params": {"index": 0, "control_point": 0, "x": 300, "y": 250}})
send({"command": "clear"})
```

**Automated test scripts**:
```powershell
C:\Users\user\miniconda3\envs\claude-imagetool\python.exe "C:\Users\user\Documents\imageTools\test\roi\test_corner.py"
C:\Users\user\miniconda3\envs\claude-imagetool\python.exe "C:\Users\user\Documents\imageTools\test\roi\test_sector.py"
C:\Users\user\miniconda3\envs\claude-imagetool\python.exe "C:\Users\user\Documents\imageTools\test\roi\test_shapes.py"
```

### 5. Debug

- Check `logs/app.log` (UTF-8, rotating) for errors
- Use `get_detail` TCP command to inspect shape internals
- Key debugging info: `_class`, `_draw_mode`, `_has_edges`, `_has_rotation`, `_drawing_step`, `_drawing_complete`

## Common Pitfalls

- **cv2.imread** does NOT support non-ASCII paths on Windows — use `np.fromfile()` + `cv2.imdecode()`
- **Nested relative imports crash**: `from ..utils import X` fails at runtime — use `try: from .X except: from X`
- **Rotation handle caching**: cache `_axis_dir` and `_handle_sign` to prevent flipping
- **Sector angle boundary**: normalize with `% 360`, track previous angle for continuity
- **Control point overlap**: when two points share position, use explicit `control_point` index in resize command
