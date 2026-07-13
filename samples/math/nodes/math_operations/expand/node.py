"""展开节点 - 展开数学表达式。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathExpression


class ExpandNode(NodeBase):
    """展开数学表达式节点。"""

    def execute(self) -> bool:
        from sympy import expand

        expressions = self._get_input_expressions("expression")
        if not expressions:
            self.set_state(NodeState.ERROR)
            return False

        try:
            results = []
            for math_expr in expressions:
                expanded = expand(math_expr.expr)
                results.append(MathExpression(expr=expanded))

            self._set_output_expressions("expression", results)
            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"ExpandNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
