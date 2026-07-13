from enum import Enum
from typing import Any


class PortType(Enum):
    IMAGE = "image"
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    ROI = "roi"
    ANY = "any"


class PortDirection(Enum):
    INPUT = "input"
    OUTPUT = "output"


class PortDefinition:
    def __init__(self, name: str, port_type: PortType, direction: PortDirection,
                 multi: bool = False, label: str = None, count_param: str = ""):
        self.name = name
        self.port_type = port_type
        self.direction = direction
        self.multi = multi
        self.label = label or name
        self.count_param = count_param

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.port_type.value,
            "direction": self.direction.value,
            "multi": self.multi,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict, direction: PortDirection) -> "PortDefinition":
        return cls(
            name=d["name"],
            port_type=PortType(d.get("type", "image")),
            direction=direction,
            multi=d.get("multi", False),
            label=d.get("label"),
            count_param=d.get("count_param", ""),
        )

    def __repr__(self):
        return f"PortDefinition({self.direction.value}:{self.name}:{self.port_type.value})"


class Port:
    def __init__(self, definition: PortDefinition):
        self.definition = definition
        self.connections: list["Port"] = []
        self.data: Any = None

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def port_type(self) -> PortType:
        return self.definition.port_type

    @property
    def direction(self) -> PortDirection:
        return self.definition.direction

    @property
    def is_connected(self) -> bool:
        return len(self.connections) > 0

    def can_connect(self, other: "Port") -> bool:
        """Check if this port can connect to another port based on type.

        Rules:
        - ANY can connect to anything.
        - Same types can connect.
        - ROI can only connect to ROI or ANY.
        - Other types cannot connect to ROI.
        """
        if self.port_type == PortType.ANY or other.port_type == PortType.ANY:
            return True
        if self.port_type == other.port_type:
            return True
        # ROI is exclusive: only connects to ROI or ANY
        if self.port_type == PortType.ROI or other.port_type == PortType.ROI:
            return False
        return True

    def connect(self, other: "Port"):
        if other not in self.connections:
            self.connections.append(other)
        if self not in other.connections:
            other.connections.append(self)

    def disconnect(self, other: "Port"):
        if other in self.connections:
            self.connections.remove(other)
        if self in other.connections:
            other.connections.remove(self)

    def disconnect_all(self):
        for c in list(self.connections):
            c.connections.remove(self)
        self.connections.clear()

    def get_data(self) -> Any:
        return self.data

    def set_data(self, data: Any):
        self.data = data

    def __repr__(self):
        return f"Port({self.direction.value}:{self.name}, connected={self.is_connected})"
