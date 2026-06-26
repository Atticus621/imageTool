import requests
import json
import sys

BASE = "http://127.0.0.1:8765"


def api(method, path, data=None):
    url = BASE + path
    r = requests.request(method, url, json=data, timeout=10)
    result = r.json()
    status = "OK" if result.get("success") else "FAIL"
    print(f"[{status}] {method} {path}")
    print(f"       {json.dumps(result, ensure_ascii=False)}")
    print()
    return result


def main():
    print("=" * 50)
    print("ImageTools API Test")
    print("=" * 50)
    print()

    print("--- System ---")
    api("GET", "/api/v1/system/status")
    api("GET", "/api/v1/system/errors")

    print("--- Create Nodes ---")
    api("POST", "/api/v1/nodes", {"node_id": "image_source/camera", "pos": [100, 200]})
    api("POST", "/api/v1/nodes", {"node_id": "detection/shape_detection/circle", "pos": [400, 200]})

    print("--- List Nodes ---")
    api("GET", "/api/v1/nodes")

    print("--- Connect ---")
    api("POST", "/api/v1/graph/connect", {
        "from_node": "相机源",
        "from_port": "图像输出",
        "to_node": "圆检测",
        "to_port": "图像输入",
    })

    print("--- Loop Run ---")
    api("POST", "/api/v1/graph/loop/on")

    print("--- Check Status ---")
    api("GET", "/api/v1/nodes")

    print("=" * 50)
    print("Done. API docs: http://127.0.0.1:8765/docs")
    print("=" * 50)


if __name__ == "__main__":
    main()
