"""ISystem — abstract base for all domain systems."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ISystem(ABC):
    """Every domain system implements this interface.

    Systems are registered with SystemRegistry and initialized in
    dependency order. UI code depends on systems through their
    public API, never through direct imports of core/ modules.
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
