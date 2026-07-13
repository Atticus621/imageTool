"""Execution system — pipeline execution engine and supporting types."""

from systems.execution.engine import ExecutionEngine
from systems.execution.result import ExecutionResult, ImageSetEntry
from systems.execution.topology import topological_sort
from systems.execution.worker import ExecutionWorker

__all__ = [
    "ExecutionEngine",
    "ExecutionResult",
    "ExecutionWorker",
    "ImageSetEntry",
    "topological_sort",
]
