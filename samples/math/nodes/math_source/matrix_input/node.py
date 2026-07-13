"""矩阵输入节点 - 解析文本为 sympy Matrix。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathMatrix


class MatrixInputNode(NodeBase):
    """输入矩阵节点。"""

    def execute(self) -> bool:
        from sympy import Matrix, sympify

        matrix_text = self.params.get("matrix_text", "1,2;3,4")
        rows = self.params.get("rows", 2)
        cols = self.params.get("cols", 2)

        try:
            # 解析矩阵文本
            row_strs = matrix_text.split(";")
            matrix_data = []
            for row_str in row_strs[:rows]:
                col_strs = row_str.split(",")
                row = [sympify(c.strip()) for c in col_strs[:cols]]
                matrix_data.append(row)

            # 创建矩阵
            matrix = Matrix(matrix_data)

            # 创建 MathMatrix
            math_matrix = MathMatrix(matrix=matrix)

            # 输出
            self._set_output_matrices("matrix", [math_matrix])

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"MatrixInputNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
