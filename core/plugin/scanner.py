import json
from pathlib import Path

from core.logger import logger
from core.node_base.node import NodeMeta
from core.node_base.registry import node_registry


class PluginScanner:
    def __init__(self, nodes_root: str | Path = None):
        if nodes_root is None:
            nodes_root = Path(__file__).parent.parent.parent / "nodes"
        self.nodes_root = Path(nodes_root)

    def scan(self) -> int:
        if not self.nodes_root.exists():
            logger.warning(f"Nodes directory not found: {self.nodes_root}")
            return 0

        count = 0
        for meta_file in self.nodes_root.rglob("meta.json"):
            try:
                self._load_node_lazy(meta_file)
                count += 1
            except Exception as e:
                logger.error(f"Failed to load node from {meta_file}: {e}")

        logger.info(f"Plugin scan complete: {count} nodes registered")
        return count

    def _load_node_lazy(self, meta_path: Path):
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        node_dir = str(meta_path.parent)
        meta = NodeMeta.from_json(data, node_dir)

        node_py = meta_path.parent / "node.py"
        if node_py.exists():
            node_registry.register_lazy(meta, node_py)
        else:
            node_registry.register(meta)
