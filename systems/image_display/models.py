"""DisplayInfo — single source of truth for image-to-screen coordinate mapping.

This is the core fix for the ruler measurement bug. Previously coordinate
mapping logic was distributed across ImageViewerWidget.map_to_image() and
ImageSetWidget.get_image_info() in the UI layer, with pixel ratio bugs.
Now it lives in one pure, testable dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayInfo:
    """Immutable mapping between image pixels and on-screen display pixels.

    Computed once when an image is loaded/displayed. Used by ruler overlay
    and any other widget that needs to map screen clicks to image coordinates.
    """

    actual_w: int
    actual_h: int
    display_w: int
    display_h: int

    @property
    def scale_x(self) -> float:
        """Scale factor: image pixels per display pixel (horizontal)."""
        return self.actual_w / self.display_w

    @property
    def scale_y(self) -> float:
        """Scale factor: image pixels per display pixel (vertical)."""
        return self.actual_h / self.display_h

    def map_to_image(
        self, display_x: float, display_y: float
    ) -> tuple[int, int] | None:
        """Convert a display-space coordinate (within the pixmap bounds)
        to image-space pixel coordinates.

        Args:
            display_x: X position within the displayed pixmap (0 to display_w).
            display_y: Y position within the displayed pixmap (0 to display_h).

        Returns:
            (image_x, image_y) tuple, or None if the coordinate is outside
            the display bounds.
        """
        if not (0 <= display_x <= self.display_w and 0 <= display_y <= self.display_h):
            return None

        actual_x = int(display_x * self.scale_x)
        actual_y = int(display_y * self.scale_y)
        actual_x = max(0, min(actual_x, self.actual_w - 1))
        actual_y = max(0, min(actual_y, self.actual_h - 1))
        return (actual_x, actual_y)
