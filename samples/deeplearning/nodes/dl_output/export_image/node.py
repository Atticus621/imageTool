"""导出图片节点 - 将可视化结果导出为图片。"""

from core.node_base.node import NodeBase, NodeState


class ExportImageNode(NodeBase):
    """将可视化结果导出为图片节点。"""

    def execute(self) -> bool:
        port = self.input_ports.get("image")
        if not port or not port.is_connected:
            self.set_state(NodeState.ERROR)
            return False

        source = port.connections[0]
        data = source.get_data()

        if data is None:
            self.set_state(NodeState.ERROR)
            return False

        output_path = self.params.get("output_path", "output.png")
        dpi = self.params.get("dpi", 150)

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np

            # 处理不同类型的输入
            if isinstance(data, list):
                data = data[0] if data else None

            if data is None:
                self.set_state(NodeState.ERROR)
                return False

            if isinstance(data, str):
                # 文本数据
                fig, ax = plt.subplots(figsize=(8, 2))
                ax.axis('off')
                ax.text(0.5, 0.5, data, ha='center', va='center', fontsize=12)
                plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
                plt.close()
            elif isinstance(data, np.ndarray):
                # 图像数据
                plt.figure(figsize=(8, 6))
                plt.imshow(data)
                plt.axis('off')
                plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
                plt.close()
            else:
                # 其他数据
                fig, ax = plt.subplots(figsize=(8, 2))
                ax.axis('off')
                ax.text(0.5, 0.5, str(data), ha='center', va='center', fontsize=10)
                plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
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
