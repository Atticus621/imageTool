"""BridgeCommandHandler — dispatches network API commands to graph operations.

Extracted from MainWindow._handle_bridge_command() (formerly 67 lines
of business logic embedded in the UI class). Now lives in the blueprint
system where it can be tested independently.
"""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from core.logger import logger
from core.network.bridge import bridge
from systems.blueprint.node_factory import NodeFactory

if TYPE_CHECKING:
    from NodeGraphQt import NodeGraph


class BridgeCommandHandler:
    """Handles network bridge commands for graph operations.

    Takes callables for execution control (execute/stop/loop) so it
    doesn't depend on MainWindow directly.
    """

    def __init__(
        self,
        node_factory: NodeFactory,
        graph_getter: Callable[[], "NodeGraph"],
        on_execute: Callable[[], None],
        on_stop: Callable[[], None],
        on_clear: Callable[[], None],
        on_loop_on: Callable[[], None],
        on_loop_off: Callable[[], None],
    ):
        self._node_factory = node_factory
        self._get_graph = graph_getter
        self._on_execute = on_execute
        self._on_stop = on_stop
        self._on_clear = on_clear
        self._on_loop_on = on_loop_on
        self._on_loop_off = on_loop_off

    def setup(self) -> None:
        """Connect to the bridge's command_received signal."""
        bridge.command_received.connect(self.dispatch)

    def teardown(self) -> None:
        """Disconnect from the bridge."""
        bridge.command_received.disconnect(self.dispatch)

    def dispatch(self, action: str, params: dict) -> None:
        """Route a bridge command to the appropriate handler."""
        request_id = params.get("request_id", "")
        try:
            if action == "list_nodes":
                self._handle_list(request_id)
            elif action == "create_node":
                self._handle_create(request_id, params)
            elif action == "delete_node":
                self._handle_delete(request_id, params)
            elif action == "run":
                self._on_execute()
                bridge.resolve(request_id, {"success": True})
            elif action == "stop":
                self._on_stop()
                bridge.resolve(request_id, {"success": True})
            elif action == "clear":
                self._on_clear()
                bridge.resolve(request_id, {"success": True})
            elif action == "connect":
                self._handle_connect(request_id, params)
            elif action == "loop_on":
                self._on_loop_on()
                self._on_execute()
                bridge.resolve(request_id, {"success": True})
            elif action == "loop_off":
                self._on_loop_off()
                bridge.resolve(request_id, {"success": True})
            else:
                bridge.resolve(
                    request_id,
                    {"success": False, "error": f"Unknown action: {action}"},
                )
        except Exception as e:
            bridge.resolve(request_id, {"success": False, "error": str(e)})

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def _handle_list(self, request_id: str) -> None:
        nodes = []
        for n in self._get_graph().all_nodes():
            nodes.append({
                "name": n.name(),
                "id": getattr(n, "_node_id", ""),
            })
        bridge.resolve(request_id, {"success": True, "data": nodes})

    def _handle_create(self, request_id: str, params: dict) -> None:
        node_id = params.get("node_id")
        pos = params.get("pos", [0, 0])
        node = self._node_factory.create_graph_node(
            self._get_graph(), node_id, pos=tuple(pos)
        )
        if node:
            bridge.resolve(
                request_id,
                {"success": True, "data": {"name": node.name()}},
            )
        else:
            bridge.resolve(
                request_id,
                {"success": False, "error": f"Unknown node type: {node_id}"},
            )

    def _handle_delete(self, request_id: str, params: dict) -> None:
        name = params.get("node_name")
        for n in self._get_graph().all_nodes():
            if n.name() == name:
                self._get_graph().remove_node(n)
                bridge.resolve(request_id, {"success": True})
                return
        bridge.resolve(
            request_id,
            {"success": False, "error": f"Node not found: {name}"},
        )

    def _handle_connect(self, request_id: str, params: dict) -> None:
        from_name = params.get("from_node")
        from_port = params.get("from_port")
        to_name = params.get("to_node")
        to_port = params.get("to_port")

        graph = self._get_graph()
        src_node = graph.get_node_by_name(from_name)
        dst_node = graph.get_node_by_name(to_name)

        if not src_node:
            bridge.resolve(
                request_id,
                {"success": False, "error": f"Source node not found: {from_name}"},
            )
            return
        if not dst_node:
            bridge.resolve(
                request_id,
                {"success": False, "error": f"Target node not found: {to_name}"},
            )
            return

        src_out = src_node.get_output(from_port)
        dst_in = dst_node.get_input(to_port)
        if not src_out:
            bridge.resolve(
                request_id,
                {"success": False, "error": f"Output port not found: {from_port}"},
            )
            return
        if not dst_in:
            bridge.resolve(
                request_id,
                {"success": False, "error": f"Input port not found: {to_port}"},
            )
            return

        src_out.connect_to(dst_in)
        bridge.resolve(request_id, {"success": True})
