"""导出图片节点 - 将表达式导出为图片。"""

import numpy as np
from core.node_base.node import NodeBase, NodeState


class ExportImageNode(NodeBase):
    """将表达式导出为图片节点。"""

    def execute(self) -> bool:
        expressions = self._get_input_expressions("expression")
        if not expressions:
            self.set_state(NodeState.ERROR)
            return False

        output_path = self.params.get("output_path", "output.png")
        dpi = self.params.get("dpi", 150)

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from sympy import latex

            fig, ax = plt.subplots(figsize=(8, 2))
            ax.axis('off')

            # 渲染所有表达式
            latex_str = " \\quad ".join([latex(e.expr) for e in expressions])
            ax.text(0.5, 0.5, f"${latex_str}$",
                    ha='center', va='center', fontsize=14,
                    transform=ax.transAxes)

            plt.savefig(output_path, dpi=dpi, bbox_inches='tight',
                       pad_inches=0.1, facecolor='white')
            plt.close()

            from core.logger import logger
            logger.info(f"Exported image to: {output_path}")

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"ExportImageNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
