"""权重统计节点 - 统计所有层的权重分布。"""

from core.node_base.node import NodeBase, NodeState


class WeightStatsNode(NodeBase):
    """统计所有层的权重分布节点。"""

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
            lines = []
            lines.append("权重分布统计")
            lines.append("=" * 60)

            total_params = 0
            for name, param in model.named_parameters():
                if 'weight' in name:
                    w = param.data
                    total_params += w.numel()
                    lines.append(f"\n{name}:")
                    lines.append(f"  Shape: {list(w.shape)}")
                    lines.append(f"  Mean: {w.mean():.6f}")
                    lines.append(f"  Std: {w.std():.6f}")
                    lines.append(f"  Min: {w.min():.6f}")
                    lines.append(f"  Max: {w.max():.6f}")

            lines.append(f"\n总参数量: {total_params:,}")

            stats_text = "\n".join(lines)

            # 输出
            out_port = self.output_ports.get("text")
            if out_port:
                out_port.set_data([stats_text])

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"WeightStatsNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
