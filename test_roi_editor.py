"""ROI 编辑器 TCP API 自动化测试脚本。

使用前：设置环境变量 IMAGETOOL_ROI_EDITOR=1 并启动 main.py。
"""
import socket
import json
import sys


def send(cmd, host="127.0.0.1", port=9527):
    s = socket.socket()
    s.settimeout(5)
    s.connect((host, port))
    s.send(json.dumps(cmd).encode())
    data = s.recv(65536).decode()
    s.close()
    return json.loads(data)


def test_roi_editor():
    print("=== ROI Editor TCP API Test ===\n")

    # 1. 测试连接
    print("[1] Testing connection...")
    try:
        result = send({"action": "get_state"})
        assert result["status"] == "ok", f"Unexpected: {result}"
        print(f"    OK: {result['count']} shapes")
    except Exception as e:
        print(f"    FAIL: {e}")
        return False

    # 2. 绘制矩形
    print("[2] Drawing rectangle...")
    result = send({"action": "draw_rect", "x1": 100, "y1": 100, "x2": 400, "y2": 300})
    assert result["status"] == "ok", f"Unexpected: {result}"
    print(f"    OK: {result['shape']}")

    # 3. 绘制圆形
    print("[3] Drawing circle...")
    result = send({"action": "draw_circle", "x1": 500, "y1": 200, "x2": 600, "y2": 200})
    assert result["status"] == "ok", f"Unexpected: {result}"
    print(f"    OK: {result['shape']}")

    # 4. 绘制多边形
    print("[4] Drawing polygon...")
    result = send({"action": "draw_polygon", "points": [[200, 400], [350, 350], [400, 500], [250, 550]]})
    assert result["status"] == "ok", f"Unexpected: {result}"
    print(f"    OK: {result['shape']}")

    # 5. 获取状态
    print("[5] Getting state...")
    result = send({"action": "get_state"})
    assert result["status"] == "ok"
    assert result["count"] == 3
    print(f"    OK: {result['count']} shapes")
    for i, s in enumerate(result["shapes"]):
        print(f"    [{i}] {s['type']} - center={s.get('center')}")

    # 6. 选择并移动
    print("[6] Selecting and moving shape 0...")
    result = send({"action": "select", "index": 0})
    assert result["status"] == "ok"
    result = send({"action": "move", "x": 50, "y": 50})
    assert result["status"] == "ok"
    print("    OK")

    # 7. 删除形状
    print("[7] Deleting shape 2...")
    result = send({"action": "select", "index": 2})
    assert result["status"] == "ok"
    result = send({"action": "delete"})
    assert result["status"] == "ok"
    print("    OK")

    # 8. 验证删除后状态
    print("[8] Verifying state after delete...")
    result = send({"action": "get_state"})
    assert result["count"] == 2
    print(f"    OK: {result['count']} shapes remaining")

    # 9. 切换工具
    print("[9] Setting tool to circle...")
    result = send({"action": "set_tool", "tool": "circle"})
    assert result["status"] == "ok"
    print("    OK")

    # 10. 清除所有
    print("[10] Clearing all...")
    result = send({"action": "clear"})
    assert result["status"] == "ok"
    result = send({"action": "get_state"})
    assert result["count"] == 0
    print("    OK: 0 shapes")

    print("\n=== All tests passed! ===")
    return True


if __name__ == "__main__":
    success = test_roi_editor()
    sys.exit(0 if success else 1)
