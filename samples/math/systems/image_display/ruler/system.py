"""RulerSystem — stub for ruler measurement lifecycle."""

from __future__ import annotations

from core.events import EventEmitter
from systems.base import ISystem
from systems.image_display.ruler.measure import MeasurementResult, RulerMeasure


class RulerSystem(ISystem):
    """System for ruler measurement on displayed images."""

    def __init__(self, image_display=None):
        self._image_display = image_display
        self._measure = RulerMeasure()
        self.on_measurement_added = EventEmitter()
        self.on_measurement_cleared = EventEmitter()

    @property
    def name(self) -> str:
        return "Ruler"

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        self._measure.clear_calibration()

    def create_measurement(
        self, start: tuple[int, int], end: tuple[int, int]
    ) -> MeasurementResult:
        return self._measure.create_measurement(start, end)

    def calculate_pixel_distance(
        self, p1: tuple[int, int], p2: tuple[int, int]
    ) -> float:
        return self._measure.calculate_pixel_distance(p1, p2)

    def set_calibration(self, pixel_per_unit: float, unit: str = "mm") -> None:
        self._measure.set_calibration(pixel_per_unit, unit)

    def clear_calibration(self) -> None:
        self._measure.clear_calibration()
