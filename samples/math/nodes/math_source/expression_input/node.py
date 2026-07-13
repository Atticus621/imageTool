"""表达式输入节点 - 解析文本为 sympy 表达式。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathExpression


class ExpressionInputNode(NodeBase):
    """输入数学表达式节点。"""

    def execute(self) -> bool:
        from sympy import sympify, symbols, Eq

        expression_text = self.params.get("expression_text", "x**2 + 2*x + 1")
        variables_text = self.params.get("variables", "x")

        try:
            # 解析变量
            var_names = [v.strip() for v in variables_text.split(",") if v.strip()]
            if len(var_names) == 1:
                x = symbols(var_names[0])
                locals_map = {var_names[0]: x}
            else:
                vars_tuple = symbols(var_names)
                locals_map = dict(zip(var_names, vars_tuple))

            # 处理方程 (包含 = 号)
            if "=" in expression_text:
                parts = expression_text.split("=", 1)
                lhs = sympify(parts[0].strip(), locals=locals_map)
                rhs = sympify(parts[1].strip(), locals=locals_map)
                expr = lhs - rhs  # 转换为 f(x) = 0 形式
            else:
                expr = sympify(expression_text, locals=locals_map)

            # 创建 MathExpression
            math_expr = MathExpression(expr=expr)

            # 输出
            self._set_output_expressions("expression", [math_expr])

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"ExpressionInputNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
