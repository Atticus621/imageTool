"""NodeFactory — encapsulates GraphNode creation, replacement, and conversion.

Owns all operations that bridge NodeGraphQt's graph model and the core
node registry. UI widgets delegate node operations through this factory
instead of manipulating the graph and registry directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.logger import logger
from core.node_base.registry import NodeRegistry
from core.pipeline import PipelineNodeInfo

if TYPE_CHECKING:
    from NodeGraphQt import NodeGraph, BaseNode


class NodeFactory:
    """Creates, replaces, and converts graph nodes.

    Wraps NodeRegistry + NodeGraph interactions so UI code only
    calls simple factory methods.
    """

    def __init__(self, registry: NodeRegistry):
        self._registry = registry

    # ------------------------------------------------------------------
    # Node creation
    # ------------------------------------------------------------------

    def create_node(
        self,
        graph: "NodeGraph",
        node_id: str,
        pos: tuple[float, float] | None = None,
    ) -> "BaseNode | None":
        """Create a GraphNode of the given type on the graph.

        Args:
            graph: The NodeGraphQt graph instance.
            node_id: Registry node ID (e.g. 'image_source/camera').
            pos: Optional (x, y) position.

        Returns:
            The created node, or None if node_id was not found.
        """
        meta = self._registry.get_meta(node_id)
        if meta is None:
            logger.error(f"Node type not found: {node_id}")
            return None

        node = graph.create_node(
            "imagetools.GraphNode",
            name=meta.name,
            pos=pos,
        )
        node.set_node_meta(meta)
        logger.info(f"Created node: {meta.name} ({node_id}) at {pos}")
        return node

    # ------------------------------------------------------------------
    # Node replacement
    # ------------------------------------------------------------------

    def replace_node(
        self,
        graph: "NodeGraph",
        old_node: "BaseNode",
        new_node_id: str,
    ) -> "BaseNode | None":
        """Replace a graph node with one of a different type.

        Preserves port connections where possible.
        Only allows replacement within the same category.
        """
        meta = self._registry.get_meta(new_node_id)
        if meta is None:
            logger.error(f"Node type not found: {new_node_id}")
            return None

        old_meta_id = getattr(old_node, "_node_id", "")
        old_meta = self._registry.get_meta(old_meta_id)

        if old_meta and old_meta.category != meta.category:
            logger.warning(
                f"Cannot replace: category mismatch "
                f"({old_meta.category} != {meta.category})"
            )
            return None

        # Save connections
        input_connections = {}
        for port in old_node.input_ports():
            connected = port.connected_ports()
            if connected:
                input_connections[port.name()] = list(connected)

        output_connections = {}
        for port in old_node.output_ports():
            connected = port.connected_ports()
            if connected:
                output_connections[port.name()] = list(connected)

        pos = old_node.pos()
        graph.remove_node(old_node)

        new_node = self.create_node(graph, new_node_id, pos=(pos.x(), pos.y()))
        if new_node is None:
            return None

        # Restore connections
        new_inputs = new_node.inputs()
        for port_name, src_ports in input_connections.items():
            if port_name in new_inputs:
                for src_port in src_ports:
                    try:
                        src_port.connect_to(new_inputs[port_name], push_undo=False)
                    except Exception as e:
                        logger.warning(
                            f"Failed to restore input connection {port_name}: {e}"
                        )

        new_outputs = new_node.outputs()
        for port_name, dst_ports in output_connections.items():
            if port_name in new_outputs:
                for dst_port in dst_ports:
                    try:
                        new_outputs[port_name].connect_to(dst_port, push_undo=False)
                    except Exception as e:
                        logger.warning(
                            f"Failed to restore output connection {port_name}: {e}"
                        )

        logger.info(f"Replaced node: {old_meta_id} -> {new_node_id}")
        return new_node

    # ------------------------------------------------------------------
    # Pipeline conversion
    # ------------------------------------------------------------------

    @staticmethod
    def to_pipeline_info(node: "BaseNode") -> PipelineNodeInfo:
        """Convert a GraphNode to a PipelineNodeInfo for execution.

        Delegates to GraphNode.to_pipeline_info() as single source of truth.
        """
        return node.to_pipeline_info()

    @staticmethod
    def extract_pipeline(graph: "NodeGraph") -> list[PipelineNodeInfo]:
        """Extract pipeline info from all nodes in the graph."""
        return [
            NodeFactory.to_pipeline_info(n)
            for n in graph.all_nodes()
        ]
