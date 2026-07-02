from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from core.logger import logger
from core.image_data import ImageData
from .port import Port, PortDefinition, PortDirection, PortType


class NodeState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class ParamType(Enum):
    FILE_LIST = "file_list"
    COMBO = "combo"
    INT_SLIDER = "int_slider"
    FLOAT_SLIDER = "float_slider"
    TEXT = "text"
    CHECKBOX = "checkbox"
    CHANNEL_RANGE = "channel_range"


@dataclass
class ParamOption:
    value: Any
    label: str = ""

    def __post_init__(self):
        if not self.label:
            self.label = str(self.value)


@dataclass
class ParamDefinition:
    name: str
    param_type: ParamType
    label: str = ""
    default: Any = None
    options: list[ParamOption] = field(default_factory=list)
    min_val: float | int | None = None
    max_val: float | int | None = None
    step: float | int | None = None
    filters: str = ""
    multi: bool = False
    depends_on: str = ""

    def __post_init__(self):
        if not self.label:
            self.label = self.name


@dataclass
class NodeMeta:
    id: str
    name: str
    category: str
    subcategory: str = ""
    description: str = ""
    version: str = "1.0.0"
    icon: str = ""
    inputs: list[PortDefinition] = field(default_factory=list)
    outputs: list[PortDefinition] = field(default_factory=list)
    params: list[ParamDefinition] = field(default_factory=list)
    node_dir: str = ""

    @classmethod
    def from_json(cls, data: dict, node_dir: str = "") -> NodeMeta:
        from core.logger import logger

        inputs = []
        for p in data.get("inputs", []):
            inputs.append(PortDefinition.from_dict(p, PortDirection.INPUT))

        outputs = []
        for p in data.get("outputs", []):
            outputs.append(PortDefinition.from_dict(p, PortDirection.OUTPUT))

        params = []
        for p in data.get("params", []):
            options = [ParamOption(**o) for o in p.get("options", [])]
            param_type_str = p.get("type", "text")
            try:
                param_type = ParamType(param_type_str)
            except ValueError:
                logger.warning(f"Unknown param type '{param_type_str}', defaulting to TEXT")
                param_type = ParamType.TEXT

            params.append(ParamDefinition(
                name=p["name"],
                param_type=param_type,
                label=p.get("label", ""),
                default=p.get("default"),
                options=options,
                min_val=p.get("min"),
                max_val=p.get("max"),
                step=p.get("step"),
                filters=p.get("filters", ""),
                multi=p.get("multi", False),
                depends_on=p.get("depends_on", ""),
            ))

        return cls(
            id=data["id"],
            name=data["name"],
            category=data.get("category", ""),
            subcategory=data.get("subcategory", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            icon=data.get("icon", ""),
            inputs=inputs,
            outputs=outputs,
            params=params,
            node_dir=node_dir,
        )


class NodeBase:
    # ── Class-level metadata (optional — alternative to meta.json) ──
    # Set these on your subclass to define the node without a meta.json file.
    NODE_ID: str = ""             # e.g. "processing/image_operations/mask_ops"
    NODE_NAME: str = ""           # e.g. "掩码操作"
    NODE_CATEGORY: str = ""       # e.g. "图像运算"
    NODE_SUBCATEGORY: str = ""    # optional
    NODE_DESCRIPTION: str = ""
    NODE_VERSION: str = "1.0.0"
    NODE_INPUTS: list[dict] = []  # [{"name":"x", "type":"image", "label":"X"}, ...]
    NODE_OUTPUTS: list[dict] = []
    NODE_PARAMS: list[dict] = []  # [{"name":"p", "type":"combo", "default":...}, ...]

    @classmethod
    def build_meta(cls, node_dir: str = "") -> NodeMeta | None:
        """Build a NodeMeta from class-level attributes. Returns None if NODE_ID is empty."""
        if not cls.NODE_ID:
            return None
        return NodeMeta.from_json({
            "id": cls.NODE_ID,
            "name": cls.NODE_NAME or cls.__name__,
            "category": cls.NODE_CATEGORY,
            "subcategory": cls.NODE_SUBCATEGORY,
            "description": cls.NODE_DESCRIPTION,
            "version": cls.NODE_VERSION,
            "inputs": cls.NODE_INPUTS,
            "outputs": cls.NODE_OUTPUTS,
            "params": cls.NODE_PARAMS,
        }, node_dir)

    def __init__(self, meta: NodeMeta, instance_id: str = None):
        self.meta = meta
        self.instance_id = instance_id or f"{meta.id}_{id(self)}"
        self.state = NodeState.IDLE
        self.params: dict[str, Any] = {}

        self.input_ports: dict[str, Port] = {}
        self.output_ports: dict[str, Port] = {}

        for pdef in meta.inputs:
            self.input_ports[pdef.name] = Port(pdef)
        for pdef in meta.outputs:
            self.output_ports[pdef.name] = Port(pdef)

        import copy
        for p in meta.params:
            if p.default is not None:
                val = p.default
                if isinstance(val, list):
                    val = copy.copy(val)
                self.params[p.name] = val

        logger.debug(f"Node created: {self.meta.name} ({self.instance_id})")

    def get_input_port(self, name: str) -> Port | None:
        return self.input_ports.get(name)

    def get_output_port(self, name: str) -> Port | None:
        return self.output_ports.get(name)

    def get_unconnected_input_count(self) -> int:
        return sum(1 for p in self.input_ports.values() if not p.is_connected)

    def get_unconnected_output_count(self) -> int:
        return sum(1 for p in self.output_ports.values() if not p.is_connected)

    def execute(self) -> bool:
        raise NotImplementedError("Subclass must implement execute()")

    def _get_input_images(self, port_name: str) -> list:
        """Return a list of raw numpy arrays from the given input port.

        Automatically unwraps ImageData instances so existing processing
        nodes continue to receive plain np.ndarray (backward compatible).
        """
        items = self._get_input_images_raw(port_name)
        result = []
        for item in items:
            if isinstance(item, ImageData):
                result.append(item.array)
            else:
                result.append(item)
        return result

    def _get_input_images_raw(self, port_name: str) -> list:
        """Return raw port data including ImageData wrappers.

        Use this when you need color space metadata in addition to
        the pixel array (e.g. color conversion nodes).
        """
        import numpy as np
        port = self.input_ports.get(port_name)
        if not port:
            return []

        data = port.get_data()
        if data is not None:
            if isinstance(data, np.ndarray):
                return [data]
            if isinstance(data, list):
                return data
            if isinstance(data, ImageData):
                return [data]
            return [data]

        if not port.is_connected:
            return []
        source = port.connections[0]
        data = source.get_data()
        if data is None:
            return []
        if isinstance(data, np.ndarray):
            return [data]
        if isinstance(data, list):
            return data
        if isinstance(data, ImageData):
            return [data]
        return [data]

    def _set_output_images(self, port_name: str, images: list):
        port = self.output_ports.get(port_name)
        if port:
            port.set_data(images)

    def set_state(self, state: NodeState):
        self.state = state
        logger.info(f"Node {self.meta.name} state -> {state.value}")
