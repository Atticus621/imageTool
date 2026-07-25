"""Set Variable node — writes a value to the global variable registry."""

from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class SetVariableNode(NodeBase):
    """Sets a global variable value from input."""

    NODE_ID = "variable/set"
    NODE_NAME = "设置变量"
    NODE_DESCRIPTION = "将输入值设置为全局变量"
    NODE_INPUTS = [
        {"name": "value", "type": "any", "label": "值"},
    ]
    NODE_OUTPUTS = [
        {"name": "value", "type": "any", "label": "值"},
    ]
    NODE_PARAMS = [
        {
            "name": "var_name",
            "type": "text",
            "label": "变量名",
            "default": "my_var",
        },
    ]

    def execute(self) -> bool:
        from core.variable import variable_registry

        var_name = self.params.get("var_name", "my_var")
        if not var_name:
            logger.warning(f"[{self.meta.name}] Variable name is empty")
            self.set_state(NodeState.ERROR)
            return False

        # Get input value
        port = self.input_ports.get("value")
        value = port.get_data() if port else None

        # Set variable
        variable_registry.set(var_name, value)

        # Pass through
        self._set_output_port("value", value)

        logger.info(f"[{self.meta.name}] Set variable '{var_name}' = {value}")
        self.set_state(NodeState.SUCCESS)
        return True
