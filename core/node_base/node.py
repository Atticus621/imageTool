from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from core.logger import logger
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
    source_param: str = ""
    depends_on: str = ""
    depends_value: Any = None
    group: str = ""

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
                source_param=p.get("source_param", ""),
                depends_on=p.get("depends_on", ""),
                depends_value=p.get("depends_value"),
                group=p.get("group", ""),
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

        for p in meta.params:
            if p.default is not None:
                self.params[p.name] = p.default

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
        return [data]

    def _set_output_images(self, port_name: str, images: list):
        port = self.output_ports.get(port_name)
        if port:
            port.set_data(images)

    def set_state(self, state: NodeState):
        self.state = state
        logger.info(f"Node {self.meta.name} state -> {state.value}")
