"""行列式节点 - 计算矩阵行列式。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathExpression


class DeterminantNode(NodeBase):
    """计算矩阵行列式节点。"""

    def execute(self) -> bool:
        matrices = self._get_input_matrices("matrix")
        if not matrices:
            self.set_state(NodeState.ERROR)
            return False

        try:
            results = []
            for math_matrix in matrices:
                det = math_matrix.matrix.det()
                results.append(MathExpression(expr=det))

            self._set_output_expressions("expression", results)
            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"DeterminantNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
