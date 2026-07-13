"""加载数据集节点 - 加载训练/测试数据集。"""

from core.node_base.node import NodeBase, NodeState


class LoadDatasetNode(NodeBase):
    """加载训练/测试数据集节点。"""

    def execute(self) -> bool:
        dataset_type = self.params.get("dataset_type", "cifar10")
        dataset_path = self.params.get("dataset_path", "")

        try:
            from torchvision import datasets, transforms

            transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
            ])

            dataset_map = {
                "cifar10": lambda: datasets.CIFAR10(root='./data', train=True, download=True, transform=transform),
                "mnist": lambda: datasets.MNIST(root='./data', train=True, download=True, transform=transform),
            }

            if dataset_type in dataset_map:
                dataset = dataset_map[dataset_type]()
            else:
                dataset = dataset_map["cifar10"]()

            # 输出数据集信息
            dataset_info = {
                "type": dataset_type,
                "size": len(dataset),
                "classes": getattr(dataset, 'classes', []),
            }

            port = self.output_ports.get("dataset")
            if port:
                port.set_data(dataset_info)

            from core.logger import logger
            logger.info(f"Loaded dataset: {dataset_type}, size: {len(dataset)}")

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"LoadDatasetNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
