"""函数绘图节点 - 绘制函数图像。"""

import numpy as np
from core.node_base.node import NodeBase, NodeState


class GraphPlotNode(NodeBase):
    """绘制函数图像节点。"""

    def execute(self) -> bool:
        expressions = self._get_input_expressions("expression")
        if not expressions:
            self.set_state(NodeState.ERROR)
            return False

        variable = self.params.get("variable", "x")
        x_min = self.params.get("x_min", -10.0)
        x_max = self.params.get("x_max", 10.0)
        num_points = self.params.get("num_points", 500)

        try:
            from sympy import lambdify, Symbol

            var = Symbol(variable)
            x_vals = np.linspace(x_min, x_max, num_points)

            images = []
            for math_expr in expressions:
                # 将 sympy 表达式转换为 numpy 函数
                f = lambdify(var, math_expr.expr, modules=['numpy'])
                y_vals = f(x_vals)

                # 创建图像数据 (x, y 坐标对)
                image_data = np.column_stack([x_vals, y_vals])
                images.append(image_data)

            port = self.output_ports.get("image")
            if port:
                port.set_data(images)

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"GraphPlotNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
