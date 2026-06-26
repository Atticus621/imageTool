from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from core.logger import logger

if TYPE_CHECKING:
    from .node import NodeMeta, NodeBase


class NodeRegistry:
    def __init__(self):
        self._meta_by_id: dict[str, NodeMeta] = {}
        self._classes_by_id: dict[str, type] = {}
        self._lazy_paths: dict[str, Path] = {}
        self._categories: dict[str, list[str]] = {}
        self._tree_config: list[dict] = []

    def load_tree_config(self, path: str | Path):
        path = Path(path)
        if not path.exists():
            logger.warning(f"Node tree config not found: {path}")
            return
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self._tree_config = data.get("categories", [])
        logger.info(f"Loaded node tree config: {path}")

    def register(self, meta: "NodeMeta", node_class: type = None):
        self._meta_by_id[meta.id] = meta

        if node_class is not None:
            self._classes_by_id[meta.id] = node_class

        category = meta.category
        subcategory = meta.subcategory
        if subcategory:
            key = f"{category}/{subcategory}"
        else:
            key = category

        if key not in self._categories:
            self._categories[key] = []
        if meta.id not in self._categories[key]:
            self._categories[key].append(meta.id)

        logger.info(f"Registered node: {meta.id} ({meta.name}) in {key}")

    def register_lazy(self, meta: "NodeMeta", node_py_path: Path):
        self._meta_by_id[meta.id] = meta
        self._lazy_paths[meta.id] = node_py_path

        category = meta.category
        subcategory = meta.subcategory
        if subcategory:
            key = f"{category}/{subcategory}"
        else:
            key = category

        if key not in self._categories:
            self._categories[key] = []
        if meta.id not in self._categories[key]:
            self._categories[key].append(meta.id)

        logger.info(f"Registered node (lazy): {meta.id} ({meta.name}) in {key}")

    def get_meta(self, node_id: str) -> "NodeMeta | None":
        return self._meta_by_id.get(node_id)

    def get_class(self, node_id: str) -> type | None:
        cls = self._classes_by_id.get(node_id)
        if cls is None and node_id in self._lazy_paths:
            cls = self._load_class_lazy(node_id)
        return cls

    def _load_class_lazy(self, node_id: str) -> type | None:
        py_path = self._lazy_paths.pop(node_id)
        logger.info(f"Lazy loading: {node_id} from {py_path}")
        try:
            module_name = f"nodes.{node_id.replace('/', '.')}"
            spec = importlib.util.spec_from_file_location(module_name, py_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and attr_name not in ("NodeBase",)
                        and hasattr(attr, "execute")):
                    self._classes_by_id[node_id] = attr
                    return attr

            logger.warning(f"No node class found in {py_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to lazy load {node_id}: {e}")
            return None

    def create_node(self, node_id: str, instance_id: str = None) -> "NodeBase | None":
        meta = self.get_meta(node_id)
        cls = self.get_class(node_id)
        if meta is None:
            logger.error(f"Node type not found: {node_id}")
            return None
        if cls is None:
            logger.error(f"Node class not found: {node_id}")
            return None
        return cls(meta, instance_id)

    def get_all_meta(self) -> list["NodeMeta"]:
        return list(self._meta_by_id.values())

    def get_categories(self) -> dict[str, list[str]]:
        return dict(self._categories)

    def get_category_tree(self) -> dict:
        if self._tree_config:
            return self._build_tree_from_config()
        return self._build_tree_from_meta()

    def _build_tree_from_config(self) -> dict:
        tree: dict = {}
        for cat_cfg in self._tree_config:
            cat_key = cat_cfg["key"]
            cat_name = cat_cfg.get("name", cat_key)
            tree[cat_name] = {}

            subcats = cat_cfg.get("subcategories", [])
            nodes_cfg = cat_cfg.get("nodes", [])

            if subcats:
                for sub_cfg in subcats:
                    sub_key = sub_cfg["key"]
                    sub_name = sub_cfg.get("name", sub_key)
                    node_ids = [n["id"] for n in sub_cfg.get("nodes", [])]
                    metas = []
                    for nid in node_ids:
                        meta = self._meta_by_id.get(nid)
                        if meta:
                            metas.append(meta)
                    if metas:
                        tree[cat_name][sub_name] = metas
            elif nodes_cfg:
                node_ids = [n["id"] for n in nodes_cfg]
                metas = []
                for nid in node_ids:
                    meta = self._meta_by_id.get(nid)
                    if meta:
                        metas.append(meta)
                if metas:
                    tree[cat_name]["_items"] = metas

        return tree

    def _build_tree_from_meta(self) -> dict:
        tree: dict = {}
        for meta in self._meta_by_id.values():
            cat = meta.category
            subcat = meta.subcategory
            if cat not in tree:
                tree[cat] = {}
            if subcat:
                if subcat not in tree[cat]:
                    tree[cat][subcat] = []
                if meta not in tree[cat][subcat]:
                    tree[cat][subcat].append(meta)
            else:
                if "_items" not in tree[cat]:
                    tree[cat]["_items"] = []
                tree[cat]["_items"].append(meta)
        return tree

    def __len__(self):
        return len(self._meta_by_id)

    def __repr__(self):
        return f"NodeRegistry(nodes={len(self)}, categories={len(self._categories)})"


node_registry = NodeRegistry()
