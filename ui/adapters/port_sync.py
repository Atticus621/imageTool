"""Port name sync handler for SubGraph property changes.

Connects to SubGraph.property_changed and propagates PortInputNode /
PortOutputNode renames back to the parent GroupNode's port labels.
"""

from NodeGraphQt.nodes.port_node import PortInputNode, PortOutputNode

from ui.adapters.node_graph_workarounds import (
    is_port_rename_event,
    sync_port_name_to_group,
)
from core.logger import logger


class PortNameSyncHandler:
    """Connects to a SubGraph's property_changed signal to sync port renames.

    When a PortInputNode or PortOutputNode is renamed inside a SubGraph,
    this handler propagates the new name to the parent GroupNode's port
    (model, view, text label, and layout).

    Usage:
        handler = PortNameSyncHandler()
        handler.connect(sub_graph)
    """

    def connect(self, sub_graph):
        """Connect to sub_graph.property_changed and start syncing.

        Safe to call multiple times on the same SubGraph — old connections
        are disconnected first to prevent duplicate firings.

        Args:
            sub_graph: A NodeGraphQt.SubGraph instance.
        """
        # Prevent duplicate connections
        try:
            sub_graph.property_changed.disconnect(self._on_property_changed)
        except (TypeError, RuntimeError):
            pass
        sub_graph.property_changed.connect(self._on_property_changed)

    def _on_property_changed(self, node, prop_name, value):
        """Handle property changes on nodes inside the SubGraph."""
        if is_port_rename_event(node, prop_name):
            sync_port_name_to_group(node.parent_port, value)
            logger.info(f"Synced port name to: {value}")
