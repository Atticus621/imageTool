"""Backward-compatible re-export of NodeGraphWidget and GraphNode.

All code has moved to the ui.node_graph package.  This module exists so
existing imports (``from ui.node_graph_widget import NodeGraphWidget``)
continue to work without changes.
"""

from ui.node_graph.widget import NodeGraphWidget
from ui.node_graph.graph_node import GraphNode

__all__ = ["NodeGraphWidget", "GraphNode"]
