"""求导节点 - 对表达式求导。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathExpression


class DerivativeNode(NodeBase):
    """对表达式求导节点。"""

    def execute(self) -> bool:
        from sympy import diff, Symbol

        expressions = self._get_input_expressions("expression")
        if not expressions:
            self.set_state(NodeState.ERROR)
            return False

        variable = self.params.get("variable", "x")
        order = self.params.get("order", 1)

        try:
            var = Symbol(variable)
            results = []
            for math_expr in expressions:
                derived = diff(math_expr.expr, var, order)
                results.append(MathExpression(expr=derived))

            self._set_output_expressions("expression", results)
            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"DerivativeNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
