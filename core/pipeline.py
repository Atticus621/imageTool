from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PipelineNodeInfo:
    node_id: str
    name: str
    param_values: dict = field(default_factory=dict)
    port_label_to_name: dict[str, str] = field(default_factory=dict)
