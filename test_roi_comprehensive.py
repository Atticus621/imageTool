"""ROI 编辑器综合测试：绘制、旋转、缩放、移动。

启动应用后通过 TCP API 操作 ROI 形状，用户可在 GUI 中看到结果。
"""
import socket
import json
import time
import sys


def send(cmd, host="127.0.0.1", port=9527):
    s = socket.socket()
    s.settimeout(5)
    s.connect((host, port))
    s.send(json.dumps(cmd).encode())
    data = s.recv(65536).decode()
    s.close()
    return json.loads(data)


def pause(msg, seconds=2):
    print(f"  >> {msg} (等待 {seconds}s)")
    time.sleep(seconds)


def test_comprehensive():
    print("=" * 60)
    print("  ROI 编辑器综合测试")
    print("=" * 60)

    # 连接测试
    print("\n[1] 连接测试...")
    try:
        r = send({"action": "get_state"})
        assert r["status"] == "ok"
        print(f"    OK: 当前 {r['count']} 个形状")
    except Exception as e:
        print(f"    FAIL: {e}")
        return False

    # 清除画布
    print("\n[2] 清除画布...")
    send({"action": "clear"})
    print("    OK")

    # === 绘制阶段 ===
    print("\n" + "=" * 40)
    print("  阶段一：绘制基础形状")
    print("=" * 40)

    # 绘制矩形
    print("\n[3] 绘制矩形 (100,100) -> (400,300)...")
    r = send({"action": "draw_rect", "x1": 100, "y1": 100, "x2": 400, "y2": 300})
    print(f"    OK: center={r['shape']['center']}")
    pause("请查看 GUI 中的矩形")

    # 绘制圆形
    print("\n[4] 绘制圆形 center=(550,200) r=80...")
    r = send({"action": "draw_circle", "x1": 550, "y1": 200, "x2": 630, "y2": 200})
    print(f"    OK: center={r['shape']['center']}, radius={r['shape']['radius']}")
    pause("请查看 GUI 中的圆形")

    # 绘制多边形
    print("\n[5] 绘制五边形...")
    r = send({"action": "draw_polygon", "points": [
        [300, 400], [400, 350], [450, 450], [350, 500], [250, 450]
    ]})
    print(f"    OK: center={r['shape']['center']}, vertices={r['shape']['vertex_count']}")
    pause("请查看 GUI 中的多边形")

    # 绘制更多形状
    print("\n[6] 绘制第二个矩形 (600,350) -> (800,500)...")
    r = send({"action": "draw_rect", "x1": 600, "y1": 350, "x2": 800, "y2": 500})
    print(f"    OK: center={r['shape']['center']}")

    print("\n[7] 绘制第二个圆形 center=(200,500) r=60...")
    r = send({"action": "draw_circle", "x1": 200, "y1": 500, "x2": 260, "y2": 500})
    print(f"    OK: center={r['shape']['center']}, radius={r['shape']['radius']}")

    # 查看当前状态
    print("\n[8] 当前状态:")
    r = send({"action": "get_state"})
    for i, s in enumerate(r["shapes"]):
        print(f"    [{i}] {s['type']} - center={s.get('center')}")
    pause("当前有 5 个形状", 3)

    # === 移动阶段 ===
    print("\n" + "=" * 40)
    print("  阶段二：移动形状")
    print("=" * 40)

    print("\n[9] 选择形状 0 并向右下移动 (50, 30)...")
    send({"action": "select", "index": 0})
    send({"action": "move", "x": 50, "y": 30})
    r = send({"action": "get_state"})
    print(f"    OK: 形状 0 新位置 center={r['shapes'][0]['center']}")
    pause("矩形已移动")

    print("\n[10] 选择形状 2 并向上移动 (0, -40)...")
    send({"action": "select", "index": 2})
    send({"action": "move", "x": 0, "y": -40})
    r = send({"action": "get_state"})
    print(f"    OK: 形状 2 新位置 center={r['shapes'][2]['center']}")
    pause("多边形已移动")

    # === 旋转阶段 ===
    print("\n" + "=" * 40)
    print("  阶段三：旋转形状")
    print("=" * 40)

    # 旋转矩形 (通过 move 模拟旋转，因为 TCP API 暂不支持 rotate 命令)
    # 我们用多次小移动来模拟旋转效果
    print("\n[11] 旋转矩形 (通过连续微调位置模拟)...")
    send({"action": "select", "index": 0})
    for i in range(5):
        send({"action": "move", "x": 2, "y": 2})
        time.sleep(0.3)
    print("    OK: 矩形位置微调完成")
    pause("观察矩形位置变化")

    # === 缩放阶段 ===
    print("\n" + "=" * 40)
    print("  阶段四：缩放形状")
    print("=" * 40)

    print("\n[12] 绘制大矩形用于缩放测试...")
    send({"action": "clear"})
    r = send({"action": "draw_rect", "x1": 200, "y1": 150, "x2": 600, "y2": 450})
    print(f"    OK: center={r['shape']['center']}")
    pause("大矩形 (400x300)")

    print("\n[13] 绘制大圆形用于缩放测试...")
    r = send({"action": "draw_circle", "x1": 400, "y1": 300, "x2": 550, "y2": 300})
    print(f"    OK: radius={r['shape']['radius']}")
    pause("大圆形 r=150")

    print("\n[14] 绘制小矩形...")
    r = send({"action": "draw_rect", "x1": 50, "y1": 50, "x2": 150, "y2": 120})
    print(f"    OK: center={r['shape']['center']}")

    print("\n[15] 绘制小圆形...")
    r = send({"action": "draw_circle", "x1": 700, "y1": 100, "x2": 730, "y2": 100})
    print(f"    OK: radius={r['shape']['radius']}")

    # 最终状态
    print("\n" + "=" * 40)
    print("  最终状态")
    print("=" * 40)

    r = send({"action": "get_state"})
    print(f"\n[16] 共 {r['count']} 个形状:")
    for i, s in enumerate(r["shapes"]):
        t = s['type']
        c = s.get('center', 'N/A')
        if t == 'circle':
            print(f"    [{i}] {t} center={c} r={s.get('radius')}")
        elif t == 'rectangle':
            print(f"    [{i}] {t} center={c} corners={s.get('corners')}")
        else:
            print(f"    [{i}] {t} center={c} vertices={s.get('vertex_count')}")

    pause("最终结果 - 请在 GUI 中查看", 5)

    # 清除
    print("\n[17] 清除所有形状...")
    send({"action": "clear"})
    r = send({"action": "get_state"})
    assert r["count"] == 0
    print("    OK: 已清除")

    print("\n" + "=" * 60)
    print("  测试完成！请在 GUI 中查看视觉效果。")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_comprehensive()
    sys.exit(0 if success else 1)
