"""层检查器节点 - 检查指定层的详细信息。"""

from core.node_base.node import NodeBase, NodeState


class LayerInspectorNode(NodeBase):
    """检查指定层的详细信息节点。"""

    def execute(self) -> bool:
        port = self.input_ports.get("model")
        if not port or not port.is_connected:
            self.set_state(NodeState.ERROR)
            return False

        source = port.connections[0]
        model = source.get_data()
        layer_name = self.params.get("layer_name", "layer1")

        if model is None:
            self.set_state(NodeState.ERROR)
            return False

        try:
            # 查找层
            target_layer = None
            for name, module in model.named_modules():
                if name == layer_name:
                    target_layer = module
                    break

            if target_layer is None:
                info = f"未找到层: {layer_name}"
            else:
                lines = []
                lines.append(f"层名称: {layer_name}")
                lines.append(f"层类型: {type(target_layer).__name__}")
                lines.append("")

                # 参数信息
                lines.append("参数:")
                for pname, param in target_layer.named_parameters():
                    lines.append(f"  {pname}: shape={list(param.shape)}, dtype={param.dtype}")

                # 权重统计
                if hasattr(target_layer, 'weight'):
                    w = target_layer.weight.data
                    lines.append("")
                    lines.append("权重统计:")
                    lines.append(f"  均值: {w.mean():.6f}")
                    lines.append(f"  标准差: {w.std():.6f}")
                    lines.append(f"  最小值: {w.min():.6f}")
                    lines.append(f"  最大值: {w.max():.6f}")

                info = "\n".join(lines)

            # 输出
            out_port = self.output_ports.get("text")
            if out_port:
                out_port.set_data([info])

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"LayerInspectorNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
