from __future__ import annotations
from dataclasses import dataclass, field

from core.logger import logger


@dataclass
class PipelineNodeInfo:
    node_id: str
    name: str
    param_values: dict = field(default_factory=dict)
    port_label_to_name: dict[str, str] = field(default_factory=dict)

    def resolve_port_name(self, label: str) -> str:
        """Resolve a UI port label to the execution port name.

        This is the SINGLE place where port label → name mapping happens.
        All code that needs to translate between UI labels and execution
        port names should call this method.

        Args:
            label: The UI port label (e.g., "标注图像", "检测区域")

        Returns:
            The execution port name (e.g., "annotated", "rois")
        """
        name = self.port_label_to_name.get(label, label)
        if name != label:
            logger.debug(f"[PortResolve] '{label}' -> '{name}' (mapped)")
        else:
            logger.debug(f"[PortResolve] '{label}' -> '{name}' (fallback)")
        return name

    def __str__(self) -> str:
        return (
            f"PipelineNodeInfo(id={self.node_id}, name={self.name}, "
            f"ports={self.port_label_to_name})"
        )
