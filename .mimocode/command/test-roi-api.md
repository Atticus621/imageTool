---
description: Send a TCP command to the ROI CommandAPI server (port 9527) and print the result. Usage: /test-roi-api <command> [params_json]
agent: main
---

# Test ROI CommandAPI

Send a JSON command to the ROI TCP server on port 9527.

## Usage

The first argument is the command name, the optional second argument is a JSON params string.

Examples:
- `get_state` — get all shapes state
- `get_canvas_info` — get canvas dimensions
- `get_detail 0` — get detail of shape at index 0
- `draw_rect {"x":100,"y":100,"width":200,"height":150}` — draw a rectangle
- `draw_circle {"cx":300,"cy":300,"r":80}` — draw a circle
- `rotate 0 45` — rotate shape at index 0 by 45 degrees
- `resize 0 0 300 250` — resize shape at index 0, control_point 0, to (300,250)
- `delete 0` — delete shape at index 0
- `clear` — clear all shapes
- `click 200 200` — simulate click at (200,200)
- `drag 200 200 300 300` — simulate drag from (200,200) to (300,300)
- `select 0` — select shape at index 0

## Implementation

Run this Python script with the command and params:

```python
import socket, json, sys

command = "$ARGUMENTS"
# Parse: first word is command name, rest is optional JSON params
parts = command.split(None, 1)
cmd_name = parts[0] if parts else "get_state"
params = json.loads(parts[1]) if len(parts) > 1 else {}

# Handle shorthand: "rotate 0 45" → {"index": 0, "angle": 45}
# Handle shorthand: "resize 0 0 300 250" → {"index": 0, "control_point": 0, "x": 300, "y": 250}
# Handle shorthand: "get_detail 0" → {"index": 0}
# Handle shorthand: "delete 0" → {"index": 0}
# Handle shorthand: "select 0" → {"index": 0}
# Handle shorthand: "click 200 200" → {"x": 200, "y": 200}
# Handle shorthand: "drag 200 200 300 300" → {"x1": 200, "y1": 200, "x2": 300, "y2": 300}

cmd = {"command": cmd_name, "params": params}

s = socket.socket()
s.settimeout(5)
try:
    s.connect(('127.0.0.1', 9527))
    s.send(json.dumps(cmd).encode())
    data = s.recv(65536).decode()
    result = json.loads(data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
finally:
    s.close()
```

Report: the full JSON response from the server, or the error if connection failed.
