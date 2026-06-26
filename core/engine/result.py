from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ImageSetEntry:
    name: str
    images: list


@dataclass
class ExecutionResult:
    success: bool
    input_sets: list[ImageSetEntry] = field(default_factory=list)
    output_sets: list[ImageSetEntry] = field(default_factory=list)
