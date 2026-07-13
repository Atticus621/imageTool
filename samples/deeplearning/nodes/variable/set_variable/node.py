"""设置变量节点 - 设置一个变量值。"""

from core.node_base.node import NodeBase, NodeState


class SetVariableNode(NodeBase):
    """设置变量节点。"""

    def execute(self) -> bool:
        var_name = self.params.get("var_name", "my_var")

        try:
            port = self.input_ports.get("value")
            if port and port.is_connected:
                source = port.connections[0]
                value = source.get_data()
            else:
                value = port.get_data() if port else None

            from core.variable.registry import variable_registry
            variable_registry.set(var_name, value)

            self._set_output_port("value", value)

            from core.logger import logger
            logger.info(f"Set variable '{var_name}' = {value}")

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"SetVariableNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
