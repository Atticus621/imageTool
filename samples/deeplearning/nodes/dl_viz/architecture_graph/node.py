"""架构图节点 - 绘制模型架构图。"""

from core.node_base.node import NodeBase, NodeState


class ArchitectureGraphNode(NodeBase):
    """绘制模型架构图节点。"""

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
            # 生成架构描述
            lines = []
            lines.append(f"模型架构: {type(model).__name__}")
            lines.append("=" * 50)
            lines.append("")

            # 构建层级图
            indent = 0
            for name, module in model.named_children():
                lines.append(f"{'  ' * indent}[{name}] {type(module).__name__}")

                # 显示子模块
                for subname, submod in module.named_children():
                    lines.append(f"{'  ' * (indent+1)}├── {subname}: {type(submod).__name__}")

            arch_text = "\n".join(lines)

            # 输出
            out_port = self.output_ports.get("text")
            if out_port:
                out_port.set_data([arch_text])

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"ArchitectureGraphNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
