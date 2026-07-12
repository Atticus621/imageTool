"""Math node — evaluates mathematical expressions with variables."""

from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class MathNode(NodeBase):
    """Evaluates a mathematical expression using global variables."""

    NODE_ID = "variable/math"
    NODE_NAME = "表达式计算"
    NODE_CATEGORY = "变量"
    NODE_DESCRIPTION = "计算数学表达式，支持引用全局变量"
    NODE_INPUTS = []
    NODE_OUTPUTS = [
        {"name": "result", "type": "number", "label": "结果"},
    ]
    NODE_PARAMS = [
        {
            "name": "expression",
            "type": "text",
            "label": "表达式",
            "default": "0",
        },
    ]

    def execute(self) -> bool:
        from core.variable import expression_engine

        expression = self.params.get("expression", "0")
        if not expression:
            logger.warning(f"[{self.meta.name}] Expression is empty")
            self.set_state(NodeState.ERROR)
            return False

        try:
            result = expression_engine.evaluate(expression)
            self._set_output_port("result", result)
            logger.info(f"[{self.meta.name}] '{expression}' = {result}")
            self.set_state(NodeState.SUCCESS)
            return True
        except Exception as e:
            logger.error(f"[{self.meta.name}] Expression error: {e}")
            self.set_state(NodeState.ERROR)
            return False
