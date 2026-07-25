"""Generate meta.json for nodes that only have class attrs."""
import json
import re
from pathlib import Path

nodes_root = Path("D:/doucuments/code/imageTool/nodes")

nodes_to_create = [
    "detection/ocr/text_detect",
    "detection/qrcode/qr_detect",
    "processing/arithmetic/mask_ops",
    "processing/preprocess/morphology",
    "processing/statistics/histogram",
    "variable/get_variable",
    "variable/math",
    "variable/set_variable",
]


def extract_str(content, name):
    m = re.search(rf'{name}\s*=\s*"""(.*?)"""', content, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(rf"{name}\s*=\s*'(.*?)'", content)
    if m:
        return m.group(1).strip()
    m = re.search(rf'{name}\s*=\s*"(.*?)"', content)
    if m:
        return m.group(1).strip()
    return ""


def extract_list(content, name):
    m = re.search(rf"{name}\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if m:
        try:
            return eval(m.group(1))
        except Exception:
            return []
    return []


for nid in nodes_to_create:
    node_dir = nodes_root / nid
    node_py = node_dir / "node.py"
    meta_path = node_dir / "meta.json"

    if meta_path.exists():
        print(f"  SKIP (exists): {nid}")
        continue

    content = node_py.read_text(encoding="utf-8")

    meta = {
        "id": extract_str(content, "NODE_ID"),
        "name": extract_str(content, "NODE_NAME"),
        "description": extract_str(content, "NODE_DESCRIPTION"),
        "version": "1.0.0",
        "icon": "",
        "inputs": extract_list(content, "NODE_INPUTS"),
        "outputs": extract_list(content, "NODE_OUTPUTS"),
        "optional_ports": extract_list(content, "NODE_OPTIONAL_PORTS"),
        "params": extract_list(content, "NODE_PARAMS"),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=4)
        f.write("\n")

    print(f"  Created: {nid}/meta.json")

print("Done")
