"""获取变量节点 - 获取一个变量值。"""

from core.node_base.node import NodeBase, NodeState


class GetVariableNode(NodeBase):
    """获取变量节点。"""

    def execute(self) -> bool:
        var_name = self.params.get("var_name", "my_var")

        try:
            from core.variable.registry import variable_registry
            value = variable_registry.get(var_name)

            self._set_output_port("value", value)

            from core.logger import logger
            logger.info(f"Got variable '{var_name}' = {value}")

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"GetVariableNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
