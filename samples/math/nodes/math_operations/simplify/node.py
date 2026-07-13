"""化简节点 - 化简数学表达式。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathExpression


class SimplifyNode(NodeBase):
    """化简数学表达式节点。"""

    def execute(self) -> bool:
        from sympy import simplify

        expressions = self._get_input_expressions("expression")
        if not expressions:
            self.set_state(NodeState.ERROR)
            return False

        try:
            results = []
            for math_expr in expressions:
                simplified = simplify(math_expr.expr)
                results.append(MathExpression(expr=simplified))

            self._set_output_expressions("expression", results)
            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"SimplifyNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
