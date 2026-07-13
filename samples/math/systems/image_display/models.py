"""DisplayInfo — single source of truth for image-to-screen coordinate mapping."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayInfo:
    """Immutable mapping between image pixels and on-screen display pixels."""

    actual_w: int
    actual_h: int
    display_w: int
    display_h: int

    @property
    def scale_x(self) -> float:
        return self.actual_w / self.display_w

    @property
    def scale_y(self) -> float:
        return self.actual_h / self.display_h

    def map_to_image(
        self, display_x: float, display_y: float
    ) -> tuple[int, int] | None:
        if not (0 <= display_x <= self.display_w and 0 <= display_y <= self.display_h):
            return None
        actual_x = int(display_x * self.scale_x)
        actual_y = int(display_y * self.scale_y)
        actual_x = max(0, min(actual_x, self.actual_w - 1))
        actual_y = max(0, min(actual_y, self.actual_h - 1))
        return (actual_x, actual_y)
