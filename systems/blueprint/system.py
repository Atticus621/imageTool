"""BlueprintSystem — owns node graph operations and API command dispatch.

UI delegates all graph mutations (create, delete, replace, connect) and
network bridge command handling to this system instead of embedding
business logic in widgets.
"""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from core.events import EventEmitter
from core.interfaces import INodeGraphProvider
from core.logger import logger
from core.node_base.registry import node_registry
from systems.base import ISystem
from systems.blueprint.bridge_handler import BridgeCommandHandler
from systems.blueprint.node_factory import NodeFactory

if TYPE_CHECKING:
    from NodeGraphQt import NodeGraph


class BlueprintSystem(ISystem, INodeGraphProvider):
    """System for managing the node graph and its operations.

    Wraps:
    - NodeFactory: graph node CRUD + pipeline conversion
    - BridgeCommandHandler: network API command dispatch
    """

    def __init__(self):
        self._node_factory = NodeFactory(node_registry)
        self._bridge_handler: BridgeCommandHandler | None = None
        self._graph_getter: Callable[[], "NodeGraph"] | None = None

        # Events for UI to react to
        self.on_node_created = EventEmitter()
        self.on_node_deleted = EventEmitter()
        self.on_graph_cleared = EventEmitter()

    # ------------------------------------------------------------------
    # ISystem
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "Blueprint"

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        if self._bridge_handler:
            self._bridge_handler.teardown()
        self._bridge_handler = None

    # ------------------------------------------------------------------
    # Wiring (called by MainWindow after UI is created)
    # ------------------------------------------------------------------

    def wire(
        self,
        graph_getter: Callable[[], "NodeGraph"],
        on_execute: Callable[[], None],
        on_stop: Callable[[], None],
        on_clear: Callable[[], None],
        on_loop_on: Callable[[], None],
        on_loop_off: Callable[[], None],
    ) -> None:
        """Wire the system to the actual UI graph and execution callbacks.

        Called by MainWindow after the NodeGraphWidget and ExecutionEngine
        are created. Separates construction from wiring (DI pattern).
        """
        self._graph_getter = graph_getter
        self._bridge_handler = BridgeCommandHandler(
            self._node_factory,
            graph_getter,
            on_execute,
            on_stop,
            on_clear,
            on_loop_on,
            on_loop_off,
        )
        self._bridge_handler.setup()
        logger.info("BlueprintSystem wired")

    # ------------------------------------------------------------------
    # Public API — node operations
    # ------------------------------------------------------------------

    def create_node(
        self, node_id: str, pos: tuple[float, float] | None = None
    ):
        """Create a graph node of the given type."""
        if self._graph_getter is None:
            raise RuntimeError("BlueprintSystem not wired")
        node = self._node_factory.create_node(self._graph_getter(), node_id, pos)
        if node:
            self.on_node_created.emit(node, node_id)
        return node

    def replace_node(self, old_node, new_node_id: str):
        """Replace a graph node, preserving connections."""
        if self._graph_getter is None:
            raise RuntimeError("BlueprintSystem not wired")
        return self._node_factory.replace_node(
            self._graph_getter(), old_node, new_node_id
        )

    def delete_node(self, node_name: str) -> bool:
        """Delete a graph node by name."""
        if self._graph_getter is None:
            raise RuntimeError("BlueprintSystem not wired")
        for n in self._graph_getter().all_nodes():
            if n.name() == node_name:
                self._graph_getter().remove_node(n)
                self.on_node_deleted.emit(node_name)
                return True
        return False

    def extract_pipeline(self) -> list:
        """Extract PipelineNodeInfo list from the current graph."""
        if self._graph_getter is None:
            return []
        return NodeFactory.extract_pipeline(self._graph_getter())

    def get_category_tree(self) -> dict:
        """Get the category tree for context menu building."""
        return node_registry.get_category_tree()

    def get_meta(self, node_id: str):
        """Get NodeMeta for a node type."""
        return node_registry.get_meta(node_id)

    def get_registry(self):
        """Access the NodeRegistry (for NodeSelectorWindow compatibility)."""
        return node_registry
