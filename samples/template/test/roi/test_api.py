import socket
import json
import time

HOST = "127.0.0.1"
PORT = 9527


def send(cmd: dict) -> dict:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(json.dumps(cmd).encode('utf-8'))
        data = s.recv(65536).decode('utf-8')
        return json.loads(data)


def check(name, condition, detail=""):
    if condition:
        print(f"  PASS: {name} {detail}")
        return True
    else:
        print(f"  FAIL: {name} {detail}")
        return False


def get_shapes():
    r = send({"action": "get_state"})
    return r.get("shapes", [])


passed = 0
failed = 0


def run_check(name, condition, detail=""):
    global passed, failed
    if check(name, condition, detail):
        passed += 1
    else:
        failed += 1


print("[1. Clear]")
r = send({"action": "clear"})
run_check("clear", r.get("status") == "ok")
run_check("empty canvas", len(get_shapes()) == 0)

print("\n[2. Draw Rectangle]")
r = send({"action": "draw_rect", "x1": 100, "y1": 100, "x2": 300, "y2": 250})
run_check("draw_rect status", r.get("status") == "ok")
shapes = get_shapes()
run_check("rect exists", len(shapes) == 1)
run_check("rect type", shapes[0].get("type") == "rectangle")

print("\n[3. Draw Circle]")
r = send({"action": "draw_circle", "x1": 400, "y1": 200, "x2": 500, "y2": 200})
run_check("draw_circle status", r.get("status") == "ok")
shapes = get_shapes()
run_check("circle exists", len(shapes) == 2)
run_check("circle type", shapes[1].get("type") == "circle")

print("\n[4. Draw Ellipse]")
r = send({"action": "draw_ellipse", "x1": 550, "y1": 100, "x2": 700, "y2": 250})
run_check("draw_ellipse status", r.get("status") == "ok")
shapes = get_shapes()
run_check("ellipse exists", len(shapes) == 3)
run_check("ellipse type", shapes[2].get("type") == "ellipse")

print("\n[5. Draw Capsule]")
r = send({"action": "draw_capsule", "x1": 100, "y1": 350, "x2": 400, "y2": 350})
run_check("draw_capsule status", r.get("status") == "ok")
shapes = get_shapes()
run_check("capsule exists", len(shapes) == 4)
run_check("capsule type", shapes[3].get("type") == "capsule")

print("\n[6. Draw Polygon]")
r = send({"action": "draw_polygon", "points": [[500, 300], [600, 350], [550, 450], [450, 400]]})
run_check("draw_polygon status", r.get("status") == "ok")
shapes = get_shapes()
run_check("polygon exists", len(shapes) == 5)
run_check("polygon type", shapes[4].get("type") == "polygon")

print("\n[7. Draw Sector]")
r = send({"action": "draw_sector", "cx": 700, "cy": 400, "r": 80})
run_check("draw_sector status", r.get("status") == "ok")
shapes = get_shapes()
run_check("sector exists", len(shapes) == 6)
run_check("sector type", shapes[5].get("type") == "sector")

print("\n[8. Select & Move]")
r = send({"action": "select", "index": 0})
run_check("select rect", r.get("status") == "ok")
old_center = shapes[0].get("center")
r = send({"action": "move", "x": 200, "y": 200})
run_check("move status", r.get("status") == "ok")
new_shapes = get_shapes()
new_center = new_shapes[0].get("center")
run_check("center changed", old_center != new_center, f"{old_center} -> {new_center}")

print("\n[9. Select & Rotate]")
r = send({"action": "select", "index": 0})
run_check("select for rotate", r.get("status") == "ok")
r = send({"action": "rotate", "index": 0, "angle": 45})
run_check("rotate status", r.get("status") == "ok")

print("\n[10. Select & Resize]")
r = send({"action": "select", "index": 1})
run_check("select circle for resize", r.get("status") == "ok")
r = send({"action": "resize", "index": 1, "control_point": 0, "x": 400, "y": 100})
run_check("resize status", r.get("status") == "ok")

print("\n[11. Delete]")
r = send({"action": "select", "index": 2})
run_check("select for delete", r.get("status") == "ok")
r = send({"action": "delete"})
run_check("delete status", r.get("status") == "ok")
shapes = get_shapes()
run_check("shape deleted", len(shapes) == 5)

print("\n[12. Final State]")
shapes = get_shapes()
for i, s in enumerate(shapes):
    print(f"  [{i}] {s}")

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed > 0:
    print("SOME TESTS FAILED")
else:
    print("ALL TESTS PASSED")
