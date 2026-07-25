"""Plugin scanner — discovers nodes under the nodes/ directory.

Supports two formats:
  1. meta.json + node.py  (legacy, still works)
  2. node.py only          (new: metadata declared as class attributes on a NodeBase subclass)

__init__.py files are NOT required anywhere under nodes/.
The scanner also auto-creates missing __init__.py for backward compat
with any code that still does importlib.import_module().
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from core.logger import logger
from core.node_base.node import NodeMeta, NodeBase
from core.node_base.registry import node_registry


class PluginScanner:
    def __init__(self, nodes_root: str | Path | None = None) -> None:
        if nodes_root is None:
            nodes_root = Path(__file__).parent.parent.parent / "nodes"
        self.nodes_root = Path(nodes_root)

    def scan(self) -> int:
        if not self.nodes_root.exists():
            logger.warning(f"Nodes directory not found: {self.nodes_root}")
            return 0

        self._ensure_init_files()

        count = 0
        seen: set[Path] = set()

        # Pass 1: legacy meta.json + node.py
        for meta_file in self.nodes_root.rglob("meta.json"):
            try:
                self._load_from_meta_json(meta_file)
                seen.add(meta_file.parent)
                count += 1
            except Exception as e:
                logger.error(f"Failed to load node from {meta_file}: {e}")

        # Pass 2: standalone node.py (no meta.json) — class-attribute metadata
        for node_py in self.nodes_root.rglob("node.py"):
            node_dir = node_py.parent
            if node_dir in seen:
                continue
            if (node_dir / "meta.json").exists():
                continue
            try:
                self._load_from_class(node_py)
                count += 1
            except Exception as e:
                logger.error(f"Failed to load node from {node_py}: {e}")

        logger.info(f"Plugin scan complete: {count} nodes registered")
        return count

    # ── Legacy: meta.json ──────────────────────────────────────────────

    def _load_from_meta_json(self, meta_path: Path) -> None:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        node_dir = str(meta_path.parent)
        meta = NodeMeta.from_json(data, node_dir)

        node_py = meta_path.parent / "node.py"
        if node_py.exists():
            node_registry.register_lazy(meta, node_py)
        else:
            node_registry.register(meta)

    # ── New: class-attribute metadata ──────────────────────────────────

    def _load_from_class(self, node_py: Path) -> None:
        """Load a node from a standalone node.py using class-level NODE_* attributes."""
        module = self._import_module_direct(node_py)
        node_cls = self._find_node_class(module)
        if node_cls is None:
            logger.warning(f"No NodeBase subclass found in {node_py}")
            return

        node_dir = str(node_py.parent)
        meta = node_cls.build_meta(node_dir)
        if meta is None:
            logger.warning(f"Node class in {node_py} has no NODE_ID set")
            return

        node_registry.register_lazy(meta, node_py)
        logger.info(f"Registered (class): {meta.id} ({meta.name})")

    # ── Direct module import (no __init__.py needed) ───────────────────

    def _import_module_direct(self, py_path: Path):
        """Import a .py file directly, bypassing the package __init__.py chain."""
        import importlib.util

        # Derive module name from relative path: nodes/foo/bar/node.py → nodes.foo.bar.node
        try:
            rel = py_path.relative_to(self.nodes_root.parent)
        except ValueError:
            rel = py_path
        module_name = str(rel.with_suffix("")).replace("\\", ".").replace("/", ".")

        if module_name in sys.modules:
            return sys.modules[module_name]

        spec = importlib.util.spec_from_file_location(module_name, str(py_path))
        if spec is None:
            raise ImportError(f"Cannot create module spec for {py_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _find_node_class(module) -> type | None:
        """Find a NodeBase subclass in a module (not NodeBase itself).

        Prefers classes with a non-empty NODE_ID (concrete node classes)
        over base/abstract classes that may appear in the module namespace
        due to Python's import system adding already-loaded modules.
        """
        fallback = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, NodeBase)
                and attr is not NodeBase
                and hasattr(attr, "execute")
            ):
                if getattr(attr, "NODE_ID", ""):
                    return attr
                if fallback is None:
                    fallback = attr
        return fallback

    # ── Backward compat: ensure __init__.py exist ──────────────────────

    def _ensure_init_files(self) -> None:
        """Create missing __init__.py files under nodes/ for backward compat.

        Some code paths still use ``importlib.import_module()`` which requires
        __init__.py.  We create empty ones where needed so both old and new
        code work.
        """
        for dirpath in self.nodes_root.rglob("*"):
            if dirpath.is_dir():
                init_file = dirpath / "__init__.py"
                if not init_file.exists():
                    init_file.write_text("", encoding="utf-8")
