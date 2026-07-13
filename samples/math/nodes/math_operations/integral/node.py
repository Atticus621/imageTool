"""积分节点 - 对表达式积分。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathExpression


class IntegralNode(NodeBase):
    """对表达式积分节点。"""

    def execute(self) -> bool:
        from sympy import integrate, Symbol, sympify

        expressions = self._get_input_expressions("expression")
        if not expressions:
            self.set_state(NodeState.ERROR)
            return False

        variable = self.params.get("variable", "x")
        lower_bound = self.params.get("lower_bound", "")
        upper_bound = self.params.get("upper_bound", "")

        try:
            var = Symbol(variable)
            results = []

            for math_expr in expressions:
                if lower_bound and upper_bound:
                    # 定积分
                    lower = sympify(lower_bound)
                    upper = sympify(upper_bound)
                    integrated = integrate(math_expr.expr, (var, lower, upper))
                else:
                    # 不定积分
                    integrated = integrate(math_expr.expr, var)

                results.append(MathExpression(expr=integrated))

            self._set_output_expressions("expression", results)
            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"IntegralNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
