"""Execution result data classes — pure Python, no Qt dependency."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ImageSetEntry:
    """A named collection of images from one pipeline port."""
    name: str
    images: list


@dataclass
class ExecutionResult:
    """Result of a pipeline execution."""
    success: bool
    input_sets: list[ImageSetEntry] = field(default_factory=list)
    output_sets: list[ImageSetEntry] = field(default_factory=list)
    custom_sets: list[ImageSetEntry] = field(default_factory=list)
    streaming_image_index: int = -1
    streaming_total_images: int = 0
