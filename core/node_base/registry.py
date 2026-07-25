from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from core.logger import logger

if TYPE_CHECKING:
    from .node import NodeMeta, NodeBase


@dataclass
class CategoryNode:
    """Unified category tree node with explicit type contract.

    Attributes:
        subcategories: Child categories (keyed by name).
        items: NodeMeta objects directly in this category.
    """
    subcategories: dict[str, 'CategoryNode'] = field(default_factory=dict)
    items: list = field(default_factory=list)

    def get_items(self) -> list:
        """Get all NodeMeta items in this category (including subcategory items)."""
        result = list(self.items)
        for sub in self.subcategories.values():
            result.extend(sub.get_items())
        return result

    def has_subcategories(self) -> bool:
        return bool(self.subcategories)

    def has_items(self) -> bool:
        return bool(self.items)


class NodeRegistry:
    def __init__(self):
        self._meta_by_id: dict[str, NodeMeta] = {}
        self._classes_by_id: dict[str, type] = {}
        self._lazy_paths: dict[str, Path] = {}
        self._categories: dict[str, list[str]] = {}
        self._tree_config: list[dict] = []
        # Single source of truth: node_id -> (category, subcategory) from yaml
        self._node_categories: dict[str, tuple[str, str]] = {}

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

        cat_info = self._node_categories.get(meta.id)
        if cat_info:
            key = "/".join(cat_info)
        else:
            key = "_unclassified"

        if key not in self._categories:
            self._categories[key] = []
        if meta.id not in self._categories[key]:
            self._categories[key].append(meta.id)

        logger.info(f"Registered node: {meta.id} ({meta.name}) in {key}")

    def register_lazy(self, meta: "NodeMeta", node_py_path: Path):
        self._meta_by_id[meta.id] = meta
        self._lazy_paths[meta.id] = node_py_path

        cat_info = self._node_categories.get(meta.id)
        if cat_info:
            key = "/".join(cat_info)
        else:
            key = "_unclassified"

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

    def get_category(self, node_id: str) -> str:
        """Get the top-level category for a node from yaml config."""
        cat_info = self._node_categories.get(node_id)
        return cat_info[0] if cat_info else ""

    def get_subcategory(self, node_id: str) -> str:
        """Get the subcategory for a node from yaml config."""
        cat_info = self._node_categories.get(node_id)
        return cat_info[1] if cat_info and len(cat_info) > 1 else ""

    def same_category(self, node_id_a: str, node_id_b: str) -> bool:
        """Check if two nodes belong to the same top-level category."""
        return self.get_category(node_id_a) == self.get_category(node_id_b)

    def _load_class_lazy(self, node_id: str) -> type | None:
        py_path = self._lazy_paths.pop(node_id)
        logger.info(f"Lazy loading: {node_id} from {py_path}")
        try:
            import importlib.util
            import sys

            # Build canonical module name
            module_name = f"nodes.{node_id.replace('/', '.')}.node"

            # Already loaded?
            if module_name in sys.modules:
                module = sys.modules[module_name]
                logger.debug("Module %s already in sys.modules, reusing", module_name)
            else:
                # Direct import — no __init__.py needed
                spec = importlib.util.spec_from_file_location(module_name, str(py_path))
                if spec is None:
                    logger.error(f"Cannot create module spec for {py_path}")
                    return None
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
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

    def create_exec_node(self, node_id: str, instance_id: str = None) -> "NodeBase | None":
        """创建执行节点实例（用于 pipeline 执行）。

        注意：这创建的是用于执行的 NodeBase 实例，不是画布上的图节点。
        图节点创建请使用 NodeFactory.create_graph_node()。
        """
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

    def get_category_tree(self) -> dict[str, CategoryNode]:
        """Return category tree built entirely from nodes.yaml.

        Returns:
            dict[str, CategoryNode]: Top-level categories keyed by name.
            Each CategoryNode has .subcategories (dict) and .items (list).
        """
        if self._tree_config:
            tree = self._build_tree_from_config()
        else:
            # No yaml — put everything in "未分类"
            tree = {"未分类": CategoryNode(items=list(self._meta_by_id.values()))}

        return tree

    def _build_tree_from_config(self) -> dict[str, CategoryNode]:
        """Build category tree from nodes.yaml. yaml is the single source of truth."""
        tree: dict[str, CategoryNode] = {}
        yaml_node_ids: set[str] = set()

        # Build node_id → (category, subcategory) mapping from yaml
        self._collect_category_mapping()

        for cat_cfg in self._tree_config:
            self._parse_config_node(cat_cfg, tree, yaml_node_ids)

        # Warn about registered nodes not in yaml
        for meta in self._meta_by_id.values():
            if meta.id not in yaml_node_ids:
                logger.warning(
                    f"Node '{meta.id}' ({meta.name}) not found in nodes.yaml — "
                    f"will appear in '未分类'"
                )
                tree.setdefault("未分类", CategoryNode()).items.append(meta)

        return tree

    def _parse_config_node(self, cfg: dict, parent: dict[str, CategoryNode], yaml_node_ids: set):
        """Recursively parse yaml config nodes into CategoryNode tree."""
        key = cfg.get("key", "")
        name = cfg.get("name", key)
        target = parent.setdefault(name, CategoryNode())

        # Parse nodes at this level
        for n in cfg.get("nodes", []):
            nid = n["id"]
            yaml_node_ids.add(nid)
            # Store category mapping (top-level category is the outermost key)
            # We need to find the top-level category, which is the first key in the path
            meta = self._meta_by_id.get(nid)
            if meta:
                target.items.append(meta)

        # Recurse into subcategories
        for sub_cfg in cfg.get("subcategories", []):
            self._parse_config_node(sub_cfg, target.subcategories, yaml_node_ids)

    def _collect_category_mapping(self):
        """Extract node_id → (category, subcategory) from _tree_config."""
        self._node_categories.clear()

        def _walk(cfg: dict, top_category: str, subcategory: str = ""):
            name = cfg.get("name", cfg.get("key", ""))
            current_top = top_category or name

            for n in cfg.get("nodes", []):
                nid = n["id"]
                self._node_categories[nid] = (current_top, subcategory)

            for sub_cfg in cfg.get("subcategories", []):
                sub_name = sub_cfg.get("name", sub_cfg.get("key", ""))
                _walk(sub_cfg, current_top, sub_name)

        for cat_cfg in self._tree_config:
            _walk(cat_cfg, "")

    def __len__(self):
        return len(self._meta_by_id)

    def __repr__(self):
        return f"NodeRegistry(nodes={len(self)}, categories={len(self._categories)})"


node_registry = NodeRegistry()
