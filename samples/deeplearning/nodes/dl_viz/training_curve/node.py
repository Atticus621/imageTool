"""训练曲线节点 - 绘制训练损失/准确率曲线。"""

import numpy as np
from core.node_base.node import NodeBase, NodeState


class TrainingCurveNode(NodeBase):
    """绘制训练损失/准确率曲线节点。"""

    def execute(self) -> bool:
        port = self.input_ports.get("data")
        if not port or not port.is_connected:
            # 使用示例数据
            epochs = 10
            train_loss = [1.0 / (i + 1) for i in range(epochs)]
            val_loss = [1.2 / (i + 1) for i in range(epochs)]
            train_acc = [0.5 + 0.05 * i for i in range(epochs)]
            val_acc = [0.45 + 0.05 * i for i in range(epochs)]
        else:
            source = port.connections[0]
            data = source.get_data()
            if data is None:
                self.set_state(NodeState.ERROR)
                return False
            # 从数据中提取
            epochs = data.get('epochs', 10)
            train_loss = data.get('train_loss', [1.0 / (i + 1) for i in range(epochs)])
            val_loss = data.get('val_loss', [1.2 / (i + 1) for i in range(epochs)])
            train_acc = data.get('train_acc', [0.5 + 0.05 * i for i in range(epochs)])
            val_acc = data.get('val_acc', [0.45 + 0.05 * i for i in range(epochs)])

        metric = self.params.get("metric", "loss")

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

            epochs_range = range(1, len(train_loss) + 1)

            # 损失曲线
            if metric in ("loss", "both"):
                ax1.plot(epochs_range, train_loss, 'b-', label='Train Loss')
                ax1.plot(epochs_range, val_loss, 'r--', label='Val Loss')
                ax1.set_xlabel('Epoch')
                ax1.set_ylabel('Loss')
                ax1.set_title('Training Loss')
                ax1.legend()
                ax1.grid(True, alpha=0.3)

            # 准确率曲线
            if metric in ("accuracy", "both"):
                ax2.plot(epochs_range, train_acc, 'b-', label='Train Acc')
                ax2.plot(epochs_range, val_acc, 'r--', label='Val Acc')
                ax2.set_xlabel('Epoch')
                ax2.set_ylabel('Accuracy')
                ax2.set_title('Training Accuracy')
                ax2.legend()
                ax2.grid(True, alpha=0.3)

            plt.tight_layout()

            # 保存为numpy数组
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
            logger.error(f"TrainingCurveNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
