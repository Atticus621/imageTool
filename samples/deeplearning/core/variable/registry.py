"""Variable registry — global variable storage."""

from __future__ import annotations

from typing import Any

from core.events import EventEmitter
from core.logger import logger

from .variable import Variable, VariableType


class VariableRegistry:
    """Central registry for global variables.

    Variables can be read/written by any node during execution.
    Supports events for UI updates when variables change.
    """

    def __init__(self):
        self._variables: dict[str, Variable] = {}
        self.on_changed = EventEmitter()

    def get(self, name: str) -> Any:
        """Get a variable value by name.

        Args:
            name: Variable name.

        Returns:
            Variable value, or None if not found.
        """
        var = self._variables.get(name)
        return var.value if var else None

    def set(self, name: str, value: Any, var_type: VariableType = None) -> None:
        """Set a variable value.

        Args:
            name: Variable name.
            value: New value.
            var_type: Optional type override.
        """
        if name not in self._variables:
            if var_type is None:
                var_type = self._infer_type(value)
            self._variables[name] = Variable(name, value, var_type)
            logger.info(f"[VariableRegistry] Created variable: {name} = {value}")
        else:
            self._variables[name].value = value
            if var_type is not None:
                self._variables[name].var_type = var_type

        self.on_changed.emit(name, value)

    def get_variable(self, name: str) -> Variable | None:
        """Get a Variable object by name."""
        return self._variables.get(name)

    def list(self) -> list[Variable]:
        """List all variables."""
        return list(self._variables.values())

    def delete(self, name: str) -> bool:
        """Delete a variable by name.

        Returns:
            True if deleted, False if not found.
        """
        if name in self._variables:
            del self._variables[name]
            logger.info(f"[VariableRegistry] Deleted variable: {name}")
            self.on_changed.emit(name, None)
            return True
        return False

    def clear(self) -> None:
        """Clear all variables."""
        self._variables.clear()
        logger.info("[VariableRegistry] Cleared all variables")

    def _infer_type(self, value: Any) -> VariableType:
        """Infer variable type from value."""
        if isinstance(value, bool):
            return VariableType.BOOL
        elif isinstance(value, (int, float)):
            return VariableType.NUMBER
        elif isinstance(value, list):
            return VariableType.LIST
        else:
            return VariableType.STRING


# Singleton instance
variable_registry = VariableRegistry()
