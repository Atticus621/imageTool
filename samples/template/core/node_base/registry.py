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

        key = "/".join(meta.category_path) or "_unclassified"

        if key not in self._categories:
            self._categories[key] = []
        if meta.id not in self._categories[key]:
            self._categories[key].append(meta.id)

        logger.info(f"Registered node: {meta.id} ({meta.name}) in {key}")

    def register_lazy(self, meta: "NodeMeta", node_py_path: Path):
        self._meta_by_id[meta.id] = meta
        self._lazy_paths[meta.id] = node_py_path

        key = "/".join(meta.category_path) or "_unclassified"

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

    def get_category_tree(self) -> dict[str, CategoryNode]:
        """Return category tree with explicit type contract.

        Returns:
            dict[str, CategoryNode]: Top-level categories keyed by name.
            Each CategoryNode has .subcategories (dict) and .items (list).
        """
        if self._tree_config:
            tree = self._build_tree_from_config()
        else:
            tree = self._build_tree_from_meta()

        # Validate meta consistency with yaml config
        if self._tree_config:
            self._validate_meta_consistency()

        return tree

    def _validate_meta_consistency(self):
        """Validate that meta.json categories match nodes.yaml structure.

        Logs warnings for mismatches but does not block startup.
        """
        # Collect all node IDs and their expected (category, subcategory) from yaml
        yaml_locations: dict[str, tuple[str, str]] = {}

        def _collect_locations(cfg: dict, parent_category: str, parent_subcategory: str = ""):
            key = cfg.get("key", "")
            name = cfg.get("name", key)
            current_category = parent_category or name
            current_subcategory = parent_subcategory

            # Nodes at this level
            for n in cfg.get("nodes", []):
                nid = n["id"]
                yaml_locations[nid] = (current_category, current_subcategory)

            # Recurse into subcategories
            for sub_cfg in cfg.get("subcategories", []):
                sub_name = sub_cfg.get("name", sub_cfg.get("key", ""))
                _collect_locations(sub_cfg, current_category, sub_name)

        for cat_cfg in self._tree_config:
            _collect_locations(cat_cfg, "")

        # Check each registered node against yaml
        for meta in self._meta_by_id.values():
            if meta.id not in yaml_locations:
                continue
            yaml_cat, yaml_sub = yaml_locations[meta.id]
            meta_cat = meta.category or ""
            meta_sub = meta.subcategory or ""

            if meta_cat != yaml_cat or meta_sub != yaml_sub:
                logger.warning(
                    f"Category mismatch for '{meta.id}': "
                    f"yaml=({yaml_cat}, {yaml_sub}), "
                    f"meta=({meta_cat}, {meta_sub})"
                )

    def _build_tree_from_config(self) -> dict[str, CategoryNode]:
        tree: dict[str, CategoryNode] = {}
        yaml_node_ids: set[str] = set()

        for cat_cfg in self._tree_config:
            self._parse_config_node(cat_cfg, tree, yaml_node_ids)

        # Append any registered nodes NOT in yaml to their category path
        for meta in self._meta_by_id.values():
            if meta.id in yaml_node_ids:
                continue
            path = meta.category_path or ["_unclassified"]
            current = tree
            for i, segment in enumerate(path):
                if i == len(path) - 1:
                    current.setdefault(segment, CategoryNode()).items.append(meta)
                else:
                    current = current.setdefault(segment, CategoryNode()).subcategories

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
            meta = self._meta_by_id.get(nid)
            if meta:
                target.items.append(meta)

        # Recurse into subcategories
        for sub_cfg in cfg.get("subcategories", []):
            self._parse_config_node(sub_cfg, target.subcategories, yaml_node_ids)

    def _build_tree_from_meta(self) -> dict[str, CategoryNode]:
        tree: dict[str, CategoryNode] = {}
        for meta in self._meta_by_id.values():
            path = meta.category_path or ["_unclassified"]
            current = tree
            for i, segment in enumerate(path):
                if i == len(path) - 1:
                    current.setdefault(segment, CategoryNode()).items.append(meta)
                else:
                    current = current.setdefault(segment, CategoryNode()).subcategories
        return tree

    def __len__(self):
        return len(self._meta_by_id)

    def __repr__(self):
        return f"NodeRegistry(nodes={len(self)}, categories={len(self._categories)})"


node_registry = NodeRegistry()
