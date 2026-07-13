"""导出HTML节点 - 将可视化结果导出为HTML报告。"""

from core.node_base.node import NodeBase, NodeState


class ExportHTMLNode(NodeBase):
    """将可视化结果导出为HTML报告节点。"""

    def execute(self) -> bool:
        port = self.input_ports.get("text")
        if not port or not port.is_connected:
            self.set_state(NodeState.ERROR)
            return False

        source = port.connections[0]
        data = source.get_data()

        if data is None:
            self.set_state(NodeState.ERROR)
            return False

        output_path = self.params.get("output_path", "report.html")

        try:
            # 处理输入
            if isinstance(data, list):
                content = "\n".join(str(d) for d in data)
            else:
                content = str(data)

            # 生成HTML
            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Deep Learning Visualization Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1b2e; color: #e8e8f0; }}
        h1 {{ color: #00b4d8; }}
        pre {{ background: #222338; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        .content {{ white-space: pre-wrap; font-family: monospace; }}
    </style>
</head>
<body>
    <h1>Deep Learning Visualization Report</h1>
    <div class="content">{content}</div>
</body>
</html>"""

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            from core.logger import logger
            logger.info(f"Exported HTML to: {output_path}")

            self.set_state(NodeState.SUCCESS)
            return True

        except Exception as e:
            from core.logger import logger
            logger.error(f"ExportHTMLNode failed: {e}")
            self.set_state(NodeState.ERROR)
            return False
