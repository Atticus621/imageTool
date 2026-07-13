"""模型摘要节点 - 显示模型结构摘要。"""

from core.node_base.node import NodeBase, NodeState


class ModelSummaryNode(NodeBase):
    """显示模型结构摘要节点。"""

    def execute(self) -> bool:
        port = self.input_ports.get("model")
        if not port or not port.is_connected:
            self.set_state(NodeState.ERROR)
            return False

        source = port.connections[0]
        model = source.get_data()

        if model is None:
            self.set_state(NodeState.ERROR)
            return False

        try:
            # 生成模型摘要
            lines = []
            lines.append(f"模型类型: {type(model).__name__}")
            lines.append(f"参数数量: {sum(p.numel() for p in model.parameters()):,}")
            lines.append(f"可训练参数: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")
            lines.append("")
            lines.append("层结构:")
            lines.append("-" * 50)

            for name, module in model.named_children():
                params = sum(p.numel() for p in module.parameters())
                lines.append(f"  {name}: {type(module).__name__} ({params:,} params)")

            summary_text = "\n".join(lines)

            # 输出
            out_port = self.output_ports.get("text")
            if out_port:
                out_port.set_data([summary_text])

            from core.logger import logger
            logger.info(f"Generated model summary for {type(model).__name__}")

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"ModelSummaryNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
