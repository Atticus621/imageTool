from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MeasurementResult:
    start_point: tuple[int, int]
    end_point: tuple[int, int]
    pixel_distance: float
    real_distance: Optional[float] = None
    unit: str = "px"


class RulerMeasure:
    def __init__(self):
        self._calibration_factor: Optional[float] = None
        self._unit: str = "px"

    def calculate_pixel_distance(self, p1: tuple[int, int], p2: tuple[int, int]) -> float:
        return ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5

    def create_measurement(self, start: tuple[int, int], end: tuple[int, int]) -> MeasurementResult:
        pixel_dist = self.calculate_pixel_distance(start, end)
        real_dist = None
        if self._calibration_factor is not None:
            real_dist = pixel_dist * self._calibration_factor
        return MeasurementResult(
            start_point=start,
            end_point=end,
            pixel_distance=pixel_dist,
            real_distance=real_dist,
            unit=self._unit,
        )

    def set_calibration(self, pixel_per_unit: float, unit: str = "mm"):
        self._calibration_factor = pixel_per_unit
        self._unit = unit

    def clear_calibration(self):
        self._calibration_factor = None
        self._unit = "px"

    def get_real_distance(self, pixel_distance: float) -> Optional[float]:
        if self._calibration_factor is None:
            return None
        return pixel_distance * self._calibration_factor
