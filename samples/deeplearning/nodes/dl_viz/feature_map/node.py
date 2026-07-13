"""特征图节点 - 可视化卷积层特征图。"""

import numpy as np
from core.node_base.node import NodeBase, NodeState


class FeatureMapNode(NodeBase):
    """可视化卷积层特征图节点。"""

    def execute(self) -> bool:
        port = self.input_ports.get("model")
        if not port or not port.is_connected:
            self.set_state(NodeState.ERROR)
            return False

        source = port.connections[0]
        model = source.get_data()
        layer_name = self.params.get("layer_name", "layer1")
        num_features = self.params.get("num_features", 16)

        if model is None:
            self.set_state(NodeState.ERROR)
            return False

        try:
            import torch
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            # 创建随机输入
            x = torch.randn(1, 3, 224, 224)

            # 注册hook获取特征图
            features = []
            def hook(module, input, output):
                features.append(output.detach())

            # 找到目标层并注册hook
            target_layer = None
            for name, module in model.named_modules():
                if name == layer_name:
                    target_layer = module
                    break

            if target_layer is None:
                info = f"未找到层: {layer_name}"
                out_port = self.output_ports.get("image")
                if out_port:
                    out_port.set_data([info])
                self.set_state(NodeState.ERROR)
                return False

            handle = target_layer.register_forward_hook(hook)

            # 前向传播
            with torch.no_grad():
                model(x)

            handle.remove()

            if not features:
                self.set_state(NodeState.ERROR)
                return False

            # 可视化特征图
            feat = features[0][0]  # 取第一个样本
            num_show = min(num_features, feat.shape[0])

            fig, axes = plt.subplots(4, 4, figsize=(8, 8))
            for i, ax in enumerate(axes.flat):
                if i < num_show:
                    ax.imshow(feat[i].numpy(), cmap='viridis')
                ax.axis('off')

            plt.suptitle(f'Feature Maps - {layer_name}')
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
            logger.error(f"FeatureMapNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
