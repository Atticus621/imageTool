"""权重直方图节点 - 绘制权重分布直方图。"""

import numpy as np
from core.node_base.node import NodeBase, NodeState


class WeightHistogramNode(NodeBase):
    """绘制权重分布直方图节点。"""

    def execute(self) -> bool:
        port = self.input_ports.get("model")
        if not port or not port.is_connected:
            self.set_state(NodeState.ERROR)
            return False

        source = port.connections[0]
        model = source.get_data()
        num_bins = self.params.get("num_bins", 50)

        if model is None:
            self.set_state(NodeState.ERROR)
            return False

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            # 收集所有权重
            all_weights = []
            for name, param in model.named_parameters():
                if 'weight' in name:
                    all_weights.append(param.data.cpu().numpy().flatten())

            if not all_weights:
                self.set_state(NodeState.ERROR)
                return False

            all_weights = np.concatenate(all_weights)

            # 创建直方图
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.hist(all_weights, bins=num_bins, color='steelblue', edgecolor='black', alpha=0.7)
            ax.set_xlabel('Weight Value')
            ax.set_ylabel('Frequency')
            ax.set_title('Weight Distribution')
            ax.grid(True, alpha=0.3)

            # 保存为numpy数组（用于显示）
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            plt.close()

            # 输出
            out_port = self.output_ports.get("image")
            if out_port:
                out_port.set_data([img])

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"WeightHistogramNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
