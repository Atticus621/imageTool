"""Clipboard manager for copy/paste of graph nodes."""

from core.logger import logger


class ClipboardManager:
    """Manages copy/paste clipboard state for GraphNode instances.

    Stores serialized node data with relative positions so pasted nodes
    preserve their layout relative to the paste cursor.
    """

    def __init__(self):
        self._data: list[dict] = []

    def copy_nodes(self, nodes: list) -> None:
        """Copy selected nodes to the clipboard.

        Args:
            nodes: List of GraphNode instances to copy.
        """
        if not nodes:
            return
        min_x = min(n.x_pos() for n in nodes)
        min_y = min(n.y_pos() for n in nodes)

        self._data = []
        for n in nodes:
            self._data.append({
                "node_id": getattr(n, "_node_id", ""),
                "params": dict(getattr(n, "_param_values", {})),
                "dx": n.x_pos() - min_x,
                "dy": n.y_pos() - min_y,
            })
        logger.info(f"Copied {len(self._data)} node(s) to clipboard")

    def paste_entries(self):
        """Return clipboard entries for pasting.

        Returns:
            list[dict]: Clipboard entries, or empty list if nothing copied.
        """
        return list(self._data)

    @property
    def is_empty(self) -> bool:
        return len(self._data) == 0

    def clear(self):
        self._data.clear()
