"""方程求解节点 - 求解方程。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathExpression


class SolveNode(NodeBase):
    """求解方程节点。"""

    def execute(self) -> bool:
        from sympy import solve, Symbol

        expressions = self._get_input_expressions("expression")
        if not expressions:
            self.set_state(NodeState.ERROR)
            return False

        variable = self.params.get("variable", "x")

        try:
            var = Symbol(variable)
            results = []

            for math_expr in expressions:
                solutions = solve(math_expr.expr, var)
                # 将解列表转换为表达式
                for sol in solutions:
                    results.append(MathExpression(expr=sol))

            self._set_output_expressions("expression", results)
            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"SolveNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
