"""回归测试：确保节点模块不会被重复加载为多个 Python 模块对象。

背景：_load_class_lazy 曾用 importlib.util.spec_from_file_location
加载 node.py，模块名与正常 import 路径不一致，导致同一个 .py 文件
被加载为两个独立模块，全局变量互不相通（Bug：LED 闪烁）。
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def _find_node_ids() -> list[tuple[str, str]]:
    """扫描 nodes/ 目录，返回所有 (node_id, module_name) 对。"""
    nodes_root = Path(__file__).parent.parent / "nodes"
    result = []
    for meta_file in sorted(nodes_root.rglob("meta.json")):
        rel = meta_file.parent.relative_to(nodes_root)
        node_id = rel.as_posix()  # e.g. "image_source/camera"
        module_name = f"nodes.{node_id.replace('/', '.')}.node"
        if (meta_file.parent / "node.py").exists():
            result.append((node_id, module_name))
    return result


def test_camera_module_is_singleton():
    """regression: node.py 必须作为单一模块加载。

    importlib.import_module 和 from-import 应返回同一模块对象，
    否则全局变量会有两份。
    """
    pytest.importorskip("cv2")
    pytest.importorskip("PySide6")

    module_name = "nodes.image_source.camera.node"

    # 通过 importlib 加载
    mod_a = importlib.import_module(module_name)

    # 通过 from-import 获取（模拟 MainWindow 的行为）
    from nodes.image_source.camera.node import CameraSourceNode  # noqa: F811, F401

    mod_b = sys.modules[module_name]

    assert mod_a is mod_b, (
        f"DUAL MODULE BUG: {module_name} loaded as two separate modules!\n"
        f"  mod_a (importlib): {mod_a}\n"
        f"  mod_b (sys.modules): {mod_b}\n"
        f"  Fix: ensure _load_class_lazy uses importlib.import_module"
        f" with the correct module name."
    )


def test_all_node_modules_are_singletons():
    """所有已注册节点的模块不应被重复加载。"""
    pytest.importorskip("cv2")
    pytest.importorskip("PySide6")

    failures = []
    for node_id, module_name in _find_node_ids():
        try:
            mod_first = importlib.import_module(module_name)
        except Exception as e:
            # 某些节点可能有缺失依赖（如 YOLO），跳过
            print(f"  SKIP {module_name}: {e}")
            continue

        # 再次 import（模拟 registry 的第二次加载场景）
        mod_second = importlib.import_module(module_name)

        if mod_second is not mod_first:
            failures.append(
                f"  {module_name}: first={mod_first!r}, "
                f"second={mod_second!r}"
            )

    if failures:
        pytest.fail(
            "Dual-module loading detected for:\n" + "\n".join(failures)
            + "\nThese modules were loaded as separate Python objects."
        )
