"""特征值节点 - 计算矩阵特征值。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathExpression


class EigenvaluesNode(NodeBase):
    """计算矩阵特征值节点。"""

    def execute(self) -> bool:
        matrices = self._get_input_matrices("matrix")
        if not matrices:
            self.set_state(NodeState.ERROR)
            return False

        try:
            results = []
            for math_matrix in matrices:
                eigenvals = math_matrix.matrix.eigenvals()
                for val, mult in eigenvals.items():
                    results.append(MathExpression(expr=val))

            self._set_output_expressions("expression", results)
            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"EigenvaluesNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
