"""加载模型节点 - 加载 PyTorch 模型。"""

from core.node_base.node import NodeBase, NodeState


class LoadModelNode(NodeBase):
    """加载 PyTorch 模型节点。"""

    def execute(self) -> bool:
        model_type = self.params.get("model_type", "resnet18")
        model_path = self.params.get("model_path", "")

        try:
            import torch
            import torchvision.models as models

            # 加载预定义模型
            model_map = {
                "resnet18": models.resnet18,
                "resnet50": models.resnet50,
                "vgg16": models.vgg16,
                "mobilenet": models.mobilenet_v2,
            }

            if model_type in model_map:
                model = model_map[model_type](pretrained=True)
            elif model_type == "custom" and model_path:
                model = torch.load(model_path)
            else:
                model = models.resnet18(pretrained=True)

            model.eval()

            # 输出模型
            port = self.output_ports.get("model")
            if port:
                port.set_data(model)

            from core.logger import logger
            logger.info(f"Loaded model: {model_type}")

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"LoadModelNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
