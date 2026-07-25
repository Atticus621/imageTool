"""ROI 可视化测试 — 绘制形状并保持显示。"""
import socket
import json
import time

def send(cmd):
    s = socket.socket()
    s.settimeout(5)
    s.connect(('127.0.0.1', 9527))
    s.send(json.dumps(cmd).encode())
    data = s.recv(65536).decode()
    s.close()
    return json.loads(data)

print("绘制 ROI 形状...")

# 清除
send({"action": "clear"})

# 绘制矩形
r = send({"action": "draw_rect", "x1": 100, "y1": 100, "x2": 400, "y2": 300})
print(f"矩形: {r['shape']['center']}")

# 绘制圆形
r = send({"action": "draw_circle", "x1": 550, "y1": 200, "x2": 630, "y2": 200})
print(f"圆形: {r['shape']['center']} r={r['shape']['radius']}")

# 绘制多边形
r = send({"action": "draw_polygon", "points": [[200, 400], [350, 350], [400, 500], [250, 550]]})
print(f"多边形: {r['shape']['center']}")

# 绘制小矩形
r = send({"action": "draw_rect", "x1": 600, "y1": 350, "x2": 750, "y2": 480})
print(f"小矩形: {r['shape']['center']}")

# 绘制小圆形
r = send({"action": "draw_circle", "x1": 150, "y1": 450, "x2": 190, "y2": 450})
print(f"小圆形: {r['shape']['center']} r={r['shape']['radius']}")

# 移动矩形
send({"action": "select", "index": 0})
send({"action": "move", "x": 30, "y": 20})
print("矩形已移动")

# 获取最终状态
r = send({"action": "get_state"})
print(f"\n共 {r['count']} 个形状:")
for i, s in enumerate(r["shapes"]):
    print(f"  [{i}] {s['type']} center={s.get('center')}")

print("\n形状已绘制，请在 GUI 窗口中查看！")
print("（形状保持显示，不会自动清除）")
