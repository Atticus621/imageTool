"""PortConfig — 可选端口配置数据类。

用于定义节点的可选输入/输出端口，支持在编辑器中动态启用/禁用。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PortConfig:
    """可选端口配置。

    Attributes:
        name: 端口标识符（用于内部引用，如 "roi", "forbidden"）
        label: 显示名称（如 "ROI 输入", "禁止区域"）
        port_type: 端口类型（"roi", "image" 等）
        direction: 方向（"input" 或 "output"）
        default: 默认是否启用
        group: 所属参数门（"input", "output", "advanced"）
    """

    name: str
    label: str = ""
    port_type: str = "roi"
    direction: str = "input"
    default: bool = False
    group: str = "input"

    def __post_init__(self):
        if not self.label:
            self.label = self.name

    @classmethod
    def from_dict(cls, data: dict) -> PortConfig:
        """从字典创建 PortConfig。"""
        return cls(
            name=data["name"],
            label=data.get("label", ""),
            port_type=data.get("port_type", "roi"),
            direction=data.get("direction", "input"),
            default=data.get("default", False),
            group=data.get("group", "input"),
        )
