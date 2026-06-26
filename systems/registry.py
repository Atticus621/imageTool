"""SystemRegistry — lightweight IoC container for domain systems.

Handles registration, dependency ordering, initialization and shutdown.
"""

from __future__ import annotations

from collections import defaultdict, deque

from core.logger import logger
from systems.base import ISystem


class SystemRegistry:
    """Manages lifecycle of all domain systems.

    Usage:
        registry = SystemRegistry()
        registry.register(ImageDisplaySystem(), depends_on=[])
        registry.register(BlueprintSystem(), depends_on=["ImageDisplay"])
        registry.initialize_all()
        # ... app runs ...
        registry.shutdown_all()
    """

    def __init__(self):
        self._systems: dict[str, ISystem] = {}
        self._deps: dict[str, list[str]] = {}
        self._initialized: list[str] = []  # order of successful init

    def register(self, system: ISystem, depends_on: list[str] | None = None) -> None:
        """Register a system with optional dependencies.

        Args:
            system: The system instance to register.
            depends_on: List of system names that must initialize first.
        """
        name = system.name
        if name in self._systems:
            raise ValueError(f"System '{name}' is already registered")
        self._systems[name] = system
        self._deps[name] = depends_on or []

    def get(self, name: str) -> ISystem:
        """Retrieve a registered system by name.

        Raises KeyError if not found.
        """
        if name not in self._systems:
            raise KeyError(
                f"System '{name}' not registered. Available: {list(self._systems.keys())}"
            )
        return self._systems[name]

    def initialize_all(self) -> None:
        """Initialize all registered systems in dependency order.

        Systems without dependencies are initialized first.
        Cyclic dependencies are detected and reported.
        """
        order = self._topological_order()
        self._initialized = []
        for name in order:
            system = self._systems[name]
            logger.info(f"[SystemRegistry] Initializing: {name}")
            try:
                ok = system.initialize()
                if not ok:
                    logger.error(f"[SystemRegistry] {name}.initialize() returned False")
                    self.shutdown_all()
                    raise RuntimeError(f"System '{name}' failed to initialize")
                self._initialized.append(name)
            except Exception:
                logger.exception(f"[SystemRegistry] {name}.initialize() raised")
                self.shutdown_all()
                raise

    def shutdown_all(self) -> None:
        """Shutdown systems in reverse initialization order."""
        for name in reversed(self._initialized):
            try:
                logger.info(f"[SystemRegistry] Shutting down: {name}")
                self._systems[name].shutdown()
            except Exception:
                logger.exception(f"[SystemRegistry] Error shutting down {name}")
        self._initialized = []

    def _topological_order(self) -> list[str]:
        """Kahn's algorithm. Returns system names in dependency order."""
        in_degree: dict[str, int] = {name: 0 for name in self._systems}
        graph: dict[str, list[str]] = defaultdict(list)

        for name, deps in self._deps.items():
            for dep in deps:
                if dep not in self._systems:
                    raise KeyError(
                        f"System '{name}' depends on unknown system '{dep}'"
                    )
                graph[dep].append(name)
                in_degree[name] += 1

        queue = deque(n for n, d in in_degree.items() if d == 0)
        result: list[str] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._systems):
            remaining = set(self._systems) - set(result)
            raise RuntimeError(
                f"Circular dependency detected among systems: {remaining}"
            )

        return result
