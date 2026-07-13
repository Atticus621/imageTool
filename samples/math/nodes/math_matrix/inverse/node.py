"""逆矩阵节点 - 计算矩阵的逆。"""

from core.node_base.node import NodeBase, NodeState
from core.math_data import MathMatrix


class InverseNode(NodeBase):
    """计算矩阵的逆节点。"""

    def execute(self) -> bool:
        matrices = self._get_input_matrices("matrix")
        if not matrices:
            self.set_state(NodeState.ERROR)
            return False

        try:
            results = []
            for math_matrix in matrices:
                inv = math_matrix.matrix.inv()
                results.append(MathMatrix(matrix=inv))

            self._set_output_matrices("matrix", results)
            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"InverseNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
