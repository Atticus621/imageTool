"""Variable data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VariableType(Enum):
    """Supported variable types."""

    NUMBER = "number"
    STRING = "string"
    BOOL = "bool"
    LIST = "list"


@dataclass
class Variable:
    """A named variable with type information.

    Attributes:
        name: Variable name (identifier).
        value: Current value.
        var_type: Variable type.
        description: Optional description.
    """

    name: str
    value: Any = None
    var_type: VariableType = VariableType.NUMBER
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "var_type": self.var_type.value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Variable:
        return cls(
            name=data.get("name", ""),
            value=data.get("value"),
            var_type=VariableType(data.get("var_type", "number")),
            description=data.get("description", ""),
        )
