"""ISystem — abstract base for all domain systems."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from systems.registry import SystemRegistry


class ISystem(ABC):
    """Every domain system implements this interface.

    Systems are registered with SystemRegistry and initialized in
    dependency order. UI code depends on systems through their
    public API, never through direct imports of core/ modules.

    Subsystem support:
        Override register_subsystems(registry) to register child
        systems via registry.register(child, parent=self.name).
        The default implementation does nothing.

    Auto-wiring:
        Override wire(**kwargs) to receive dependencies from the UI.
        The default implementation stores kwargs as attributes.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique system name used as registry key (e.g. 'ImageDisplay')."""
        ...

    @abstractmethod
    def initialize(self) -> bool:
        """Called once at startup after dependencies are ready.

        Returns True on success. If False is returned the registry
        aborts initialization and calls shutdown() on already-started
        systems in reverse order.
        """
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Called once at shutdown. Must be idempotent."""
        ...

    def wire(self, **kwargs: Any) -> None:
        """Wire the system to UI components.

        Called by MainWindow after UI is created. Override in subclasses
        to receive specific dependencies (e.g., graph_getter).

        The default implementation stores kwargs as attributes for
        backward compatibility.

        Args:
            **kwargs: Dependencies to wire (e.g., graph_getter).
        """
        for key, value in kwargs.items():
            setattr(self, f"_{key}", value)

    def register_subsystems(self, registry: "SystemRegistry") -> None:
        """Register subsystems with the given registry.

        Called by SystemRegistry.initialize_all() before any system's
        initialize() is invoked. Override in parent systems that own
        subsystems to call registry.register(child, parent=self.name).

        Default implementation does nothing.
        """
        pass
