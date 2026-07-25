"""GraphNode — custom NodeGraphQt node for ImageTool pipeline nodes."""

from NodeGraphQt import BaseNode

from core.logger import logger
from core.pipeline import PipelineNodeInfo
from ui.theme import PORT_COLORS


class GraphNode(BaseNode):
    """Custom node that holds ImageTool pipeline metadata, parameters, and state.

    Acts as the bridge between the NodeGraphQt visual graph and the
    ImageTool node registry / execution system.
    """

    __identifier__ = "imagetools"
    NODE_NAME = "GraphNode"

    def __init__(self):
        super().__init__()
        self._node_id = ""
        self._input_image_count = 0
        self._output_image_count = 0
        self._state = "idle"
        self._param_values = {}

    # ── metadata setup ──────────────────────────────────────────────────

    def set_node_meta(self, meta):
        """Configure this node from a NodeMeta definition.

        Creates input/output ports, sets parameter defaults, and
        registers optional ports with initial visibility.
        """
        self._node_id = meta.id
        self.NODE_NAME = meta.name
        self.set_name(meta.name)

        self._port_label_to_name = {}
        self._port_count_groups: dict[str, list[str]] = {}
        self._optional_ports: dict[str, str] = {}

        for pdef in meta.inputs:
            port_name = pdef.label or pdef.name
            self.add_input(port_name, multi_input=True, display_name=True)
            self._port_label_to_name[port_name] = pdef.name
            # Set port color based on type
            port = self.get_input(port_name)
            if port and pdef.port_type.value in PORT_COLORS:
                hex_color = PORT_COLORS[pdef.port_type.value]
                r = int(hex_color[1:3], 16)
                g = int(hex_color[3:5], 16)
                b = int(hex_color[5:7], 16)
                port.color = (r, g, b, 255)
            if pdef.count_param:
                group = self._port_count_groups.setdefault(pdef.count_param, [])
                group.append(port_name)

        for pdef in meta.outputs:
            port_name = pdef.label or pdef.name
            self.add_output(port_name, multi_output=True, display_name=True)
            self._port_label_to_name[port_name] = pdef.name
            # Set port color based on type
            port = self.get_output(port_name)
            if port and pdef.port_type.value in PORT_COLORS:
                hex_color = PORT_COLORS[pdef.port_type.value]
                r = int(hex_color[1:3], 16)
                g = int(hex_color[3:5], 16)
                b = int(hex_color[5:7], 16)
                port.color = (r, g, b, 255)

        for p in meta.params:
            if p.default is not None:
                self._param_values[p.name] = p.default
                self.create_property(p.name, p.default)

        for opc in meta.optional_ports:
            port_label = opc.label or opc.name
            if opc.direction == "input":
                self.add_input(port_label, multi_input=True, display_name=True)
                port = self.get_input(port_label)
                if port:
                    port.set_visible(opc.default, push_undo=False)
            else:
                self.add_output(port_label, multi_output=True, display_name=True)
                port = self.get_output(port_label)
                if port:
                    port.set_visible(opc.default, push_undo=False)
            self._optional_ports[opc.name] = port_label
            self._port_label_to_name[port_label] = opc.name
            opt_key = f"_opt_{opc.name}"
            self._param_values[opt_key] = opc.default
            self.create_property(opt_key, opc.default)

        self._apply_port_count_visibility()

    # ── port visibility ──────────────────────────────────────────────────

    def _apply_port_count_visibility(self):
        if not hasattr(self, '_port_count_groups'):
            return
        all_ports = self.inputs()
        for count_param, port_labels in self._port_count_groups.items():
            count = int(self._param_values.get(count_param, len(port_labels)))
            for i, label in enumerate(port_labels):
                if label in all_ports:
                    all_ports[label].set_visible(i < count, push_undo=False)

    def sync_port_visibility(self):
        self._apply_port_count_visibility()

    def set_optional_port_visible(self, opc_name: str, visible: bool):
        port_label = self._optional_ports.get(opc_name)
        if not port_label:
            logger.warning(
                f"Optional port '{opc_name}' not found. "
                f"Available: {list(self._optional_ports.keys())}"
            )
            return
        port = self.get_input(port_label) or self.get_output(port_label)
        if port:
            port.set_visible(visible, push_undo=False)
            self._param_values[f"_opt_{opc_name}"] = visible
        else:
            logger.warning(
                f"[GraphNode] Port object not found for "
                f"'{opc_name}' (label='{port_label}')"
            )

    # ── state & visual ───────────────────────────────────────────────────

    def update_state_color(self, state: str):
        self._state = state
        from ui.theme import NODE_IDLE, NODE_RUNNING, NODE_SUCCESS, NODE_ERROR
        colors = {
            "idle": NODE_IDLE,
            "running": NODE_RUNNING,
            "success": NODE_SUCCESS,
            "error": NODE_ERROR,
        }
        self.set_color(*colors.get(state, NODE_IDLE))

    # ── serialization helpers ────────────────────────────────────────────

    def to_pipeline_info(self) -> PipelineNodeInfo:
        return PipelineNodeInfo(
            node_id=self._node_id,
            name=self.name(),
            param_values=dict(self._param_values),
            port_label_to_name=dict(getattr(self, "_port_label_to_name", {})),
        )

    def get_input_image_count(self) -> int:
        return sum(1 for p in self.input_ports() if not p.connected_ports())

    def get_output_image_count(self) -> int:
        return sum(1 for p in self.output_ports() if not p.connected_ports())
