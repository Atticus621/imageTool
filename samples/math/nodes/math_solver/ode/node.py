"""微分方程节点 - 求解常微分方程。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathExpression


class ODENode(NodeBase):
    """求解常微分方程节点。"""

    def execute(self) -> bool:
        from sympy import symbols, Function, dsolve

        expressions = self._get_input_expressions("expression")
        if not expressions:
            self.set_state(NodeState.ERROR)
            return False

        function_name = self.params.get("function", "y")
        independent_var = self.params.get("independent_var", "x")

        try:
            x = symbols(independent_var)
            y = Function(function_name)

            results = []
            for math_expr in expressions:
                solution = dsolve(math_expr.expr, y(x))
                results.append(MathExpression(expr=solution.rhs))

            self._set_output_expressions("expression", results)
            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"ODENode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
