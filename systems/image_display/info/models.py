"""PixelInfo — value object for pixel-level image information."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PixelInfo:
    """Immutable snapshot of a single pixel in an image.

    Attributes:
        x: X coordinate (column) in image pixels.
        y: Y coordinate (row) in image pixels.
        channel_values: Channel name → value mapping (e.g. {"B": 128, "G": 200, "R": 55}).
        color_space: The color space of the image (e.g. "bgr", "hsv").
        image_width: Total image width in pixels.
        image_height: Total image height in pixels.
    """

    x: int
    y: int
    channel_values: dict[str, float | int]
    color_space: str
    image_width: int
    image_height: int

    @property
    def position_str(self) -> str:
        return f"({self.x}, {self.y})"

    @property
    def size_str(self) -> str:
        return f"{self.image_width} × {self.image_height}"

    @property
    def channels_str(self) -> str:
        """One-line channel values string, e.g. 'B:128  G:200  R:55'."""
        parts = [f"{name}={val}" for name, val in self.channel_values.items()]
        return "  ".join(parts)
