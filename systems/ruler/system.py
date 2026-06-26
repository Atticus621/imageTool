"""RulerSystem — manages ruler measurement lifecycle and calibration.

Wraps RulerMeasure with proper system lifecycle. UI code gets a
RulerSystem reference instead of creating RulerMeasure directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.events import EventEmitter
from systems.base import ISystem
from systems.ruler.measure import MeasurementResult, RulerMeasure

if TYPE_CHECKING:
    from systems.image_display.system import ImageDisplaySystem


class RulerSystem(ISystem):
    """System for ruler measurement on displayed images.

    Depends on ImageDisplaySystem for coordinate mapping.
    Wraps RulerMeasure with calibration management and lifecycle.
    """

    def __init__(self, image_display: "ImageDisplaySystem"):
        self._image_display = image_display
        self._measure = RulerMeasure()
        self.on_measurement_added = EventEmitter()
        self.on_measurement_cleared = EventEmitter()

    # ------------------------------------------------------------------
    # ISystem
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "Ruler"

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        self._measure.clear_calibration()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_measurement(
        self, start: tuple[int, int], end: tuple[int, int]
    ) -> MeasurementResult:
        """Create a measurement from image-pixel start/end coordinates."""
        return self._measure.create_measurement(start, end)

    def calculate_pixel_distance(
        self, p1: tuple[int, int], p2: tuple[int, int]
    ) -> float:
        """Calculate Euclidean pixel distance between two points."""
        return self._measure.calculate_pixel_distance(p1, p2)

    def set_calibration(self, pixel_per_unit: float, unit: str = "mm") -> None:
        """Set calibration for real-world distance conversion."""
        self._measure.set_calibration(pixel_per_unit, unit)

    def clear_calibration(self) -> None:
        """Remove calibration, back to pixel-only measurements."""
        self._measure.clear_calibration()

    def map_screen_to_image(
        self, display_x: float, display_y: float
    ) -> tuple[int, int] | None:
        """Map a screen coordinate to image pixel via ImageDisplaySystem."""
        return self._image_display.map_to_image(display_x, display_y)

    def get_display_info(self):
        """Get current DisplayInfo from ImageDisplaySystem."""
        return self._image_display.get_current_display_info()
