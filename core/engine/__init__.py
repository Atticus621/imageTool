"""Backward-compatibility shim. Re-exports from systems/execution."""

from systems.execution.engine import ExecutionEngine  # noqa: F401
from systems.execution.result import ExecutionResult, ImageSetEntry  # noqa: F401
from systems.execution.topology import topological_sort  # noqa: F401
