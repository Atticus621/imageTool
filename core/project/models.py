"""Project file data models.

Defines the structure for project serialization/deserialization.
All models are dataclasses for easy JSON conversion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ProjectMetadata:
    """Project metadata information."""

    name: str = "未命名项目"
    description: str = ""
    author: str = ""
    created_at: str = ""
    modified_at: str = ""
    app_version: str = "0.1.0"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.modified_at:
            self.modified_at = now

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "app_version": self.app_version,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectMetadata:
        return cls(
            name=data.get("name", "未命名项目"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
            app_version=data.get("app_version", "0.1.0"),
            tags=data.get("tags", []),
        )


@dataclass
class NodePosition:
    """Node position on the graph canvas."""

    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: dict) -> NodePosition:
        return cls(x=data.get("x", 0.0), y=data.get("y", 0.0))


@dataclass
class NodeData:
    """Serialized node data."""

    id: str = ""
    instance_id: str = ""
    name: str = ""
    position: NodePosition = field(default_factory=NodePosition)
    param_values: dict[str, Any] = field(default_factory=dict)
    optional_port_states: dict[str, bool] = field(default_factory=dict)
    is_placeholder: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "name": self.name,
            "position": self.position.to_dict(),
            "param_values": dict(self.param_values),
            "optional_port_states": dict(self.optional_port_states),
            "is_placeholder": self.is_placeholder,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NodeData:
        return cls(
            id=data.get("id", ""),
            instance_id=data.get("instance_id", ""),
            name=data.get("name", ""),
            position=NodePosition.from_dict(data.get("position", {})),
            param_values=data.get("param_values", {}),
            optional_port_states=data.get("optional_port_states", {}),
            is_placeholder=data.get("is_placeholder", False),
        )


@dataclass
class ConnectionData:
    """Serialized connection data."""

    from_node: str = ""
    from_port: str = ""
    to_node: str = ""
    to_port: str = ""

    def to_dict(self) -> dict:
        return {
            "from_node": self.from_node,
            "from_port": self.from_port,
            "to_node": self.to_node,
            "to_port": self.to_port,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ConnectionData:
        return cls(
            from_node=data.get("from_node", ""),
            from_port=data.get("from_port", ""),
            to_node=data.get("to_node", ""),
            to_port=data.get("to_port", ""),
        )


@dataclass
class ROISerializedData:
    """Serialized ROI data (for embedding in project file)."""

    node_id: str = ""
    roi_type: str = ""
    data: Any = None
    image_size: tuple[int, int] = (0, 0)
    trace_id: str = ""
    metadata: dict = field(default_factory=dict)
    mask_base64: str = ""
    mask_shape: list[int] = field(default_factory=list)
    mask_dtype: str = ""

    def to_dict(self) -> dict:
        d = {
            "node_id": self.node_id,
            "roi_type": self.roi_type,
            "image_size": list(self.image_size),
            "trace_id": self.trace_id,
            "metadata": dict(self.metadata),
        }
        if self.roi_type == "mask" and self.mask_base64:
            d["mask_base64"] = self.mask_base64
            d["mask_shape"] = self.mask_shape
            d["mask_dtype"] = self.mask_dtype
        else:
            d["data"] = self.data
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ROISerializedData:
        return cls(
            node_id=data.get("node_id", ""),
            roi_type=data.get("roi_type", ""),
            data=data.get("data"),
            image_size=tuple(data.get("image_size", [0, 0])),
            trace_id=data.get("trace_id", ""),
            metadata=data.get("metadata", {}),
            mask_base64=data.get("mask_base64", ""),
            mask_shape=data.get("mask_shape", []),
            mask_dtype=data.get("mask_dtype", ""),
        )


@dataclass
class ExecutionConfig:
    """Execution configuration."""

    loop_mode: bool = False
    auto_execute: bool = False

    def to_dict(self) -> dict:
        return {
            "loop_mode": self.loop_mode,
            "auto_execute": self.auto_execute,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ExecutionConfig:
        return cls(
            loop_mode=data.get("loop_mode", False),
            auto_execute=data.get("auto_execute", False),
        )


@dataclass
class DisplayData:
    """Serialized display configuration."""

    displays: dict[str, str] = field(default_factory=dict)  # display_id -> display_name
    node_displays: dict[str, str] = field(default_factory=dict)  # node_name -> display_id

    def to_dict(self) -> dict:
        return {
            "displays": dict(self.displays),
            "node_displays": dict(self.node_displays),
        }

    @classmethod
    def from_dict(cls, data: dict) -> DisplayData:
        return cls(
            displays=data.get("displays", {}),
            node_displays=data.get("node_displays", {}),
        )


@dataclass
class ProjectData:
    """Top-level project data container."""

    version: str = "1.0.0"
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    nodes: list[NodeData] = field(default_factory=list)
    connections: list[ConnectionData] = field(default_factory=list)
    rois: list[ROISerializedData] = field(default_factory=list)
    execution_config: ExecutionConfig = field(default_factory=ExecutionConfig)
    display_config: DisplayData = field(default_factory=DisplayData)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "metadata": self.metadata.to_dict(),
            "nodes": [n.to_dict() for n in self.nodes],
            "connections": [c.to_dict() for c in self.connections],
            "rois": [r.to_dict() for r in self.rois],
            "execution_config": self.execution_config.to_dict(),
            "display_config": self.display_config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectData:
        return cls(
            version=data.get("version", "1.0.0"),
            metadata=ProjectMetadata.from_dict(data.get("metadata", {})),
            nodes=[NodeData.from_dict(n) for n in data.get("nodes", [])],
            connections=[ConnectionData.from_dict(c) for c in data.get("connections", [])],
            rois=[ROISerializedData.from_dict(r) for r in data.get("rois", [])],
            execution_config=ExecutionConfig.from_dict(data.get("execution_config", {})),
            display_config=DisplayData.from_dict(data.get("display_config", {})),
        )
