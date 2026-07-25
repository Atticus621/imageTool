"""Get Variable node — reads a value from the global variable registry."""

from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class GetVariableNode(NodeBase):
    """Gets a global variable value."""

    NODE_ID = "variable/get"
    NODE_NAME = "获取变量"
    NODE_DESCRIPTION = "从全局变量中读取值"
    NODE_INPUTS = []
    NODE_OUTPUTS = [
        {"name": "value", "type": "any", "label": "值"},
    ]
    NODE_PARAMS = [
        {
            "name": "var_name",
            "type": "combo",
            "label": "变量名",
            "default": "",
            "options": [],  # Populated dynamically
        },
    ]

    def execute(self) -> bool:
        from core.variable import variable_registry

        var_name = self.params.get("var_name", "")
        if not var_name:
            logger.warning(f"[{self.meta.name}] No variable selected")
            self.set_state(NodeState.ERROR)
            return False

        value = variable_registry.get(var_name)
        self._set_output_port("value", value)

        logger.info(f"[{self.meta.name}] Got variable '{var_name}' = {value}")
        self.set_state(NodeState.SUCCESS)
        return True

    @classmethod
    def build_meta(cls, node_dir: str = ""):
        """Build meta with dynamic variable options."""
        from core.variable import variable_registry
        from core.node_base.node import NodeMeta, ParamType, ParamDefinition

        # Get current variables for options
        variables = variable_registry.list()
        options = [{"value": v.name, "label": v.name} for v in variables]

        meta = NodeMeta(
            id=cls.NODE_ID,
            name=cls.NODE_NAME,
            description=cls.NODE_DESCRIPTION,
            inputs=[],
            outputs=[{"name": "value", "type": "any", "label": "值"}],
            params=[
                ParamDefinition(
                    name="var_name",
                    param_type=ParamType.COMBO,
                    label="变量名",
                    default="",
                    options=options,
                ),
            ],
        )
        return meta
