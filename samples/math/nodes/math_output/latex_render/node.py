"""LaTeX 渲染节点 - 将表达式渲染为 LaTeX 格式。"""

from core.node_base.node import NodeBase, NodeState


class LatexRenderNode(NodeBase):
    """将表达式渲染为 LaTeX 格式节点。"""

    def execute(self) -> bool:
        expressions = self._get_input_expressions("expression")
        if not expressions:
            self.set_state(NodeState.ERROR)
            return False

        try:
            latex_strings = []
            for math_expr in expressions:
                latex_strings.append(math_expr.latex)

            port = self.output_ports.get("string")
            if port:
                port.set_data(latex_strings)

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"LatexRenderNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
