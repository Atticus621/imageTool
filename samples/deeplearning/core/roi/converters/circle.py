"""圆形 ROI 转换器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

from ..converter import IROIConverter, converter_registry

if TYPE_CHECKING:
    from ..data import ROIData


class CircleConverter(IROIConverter):
    """圆形 ROI 转换器。

    data 格式: (center_x, center_y, radius)
    """

    type_id = "circle"

    def to_mask(self, roi: ROIData, image_size: tuple[int, int]) -> np.ndarray:
        w, h = image_size
        mask = np.zeros((h, w), dtype=np.uint8)
        cx, cy, r = roi.data
        cv2.circle(mask, (int(cx), int(cy)), int(r), 1, -1)
        return mask.astype(bool)

    def to_dict(self, roi: ROIData) -> dict:
        cx, cy, r = roi.data
        return {
            "roi_type": self.type_id,
            "data": [cx, cy, r],
            "image_size": list(roi.image_size) if roi.image_size else None,
            "trace_id": roi.trace_id,
            "metadata": roi.metadata,
        }

    def from_dict(self, data: dict) -> ROIData:
        from ..data import ROIData as RD

        d = data["data"]
        image_size = tuple(data["image_size"]) if data.get("image_size") else None
        return RD(
            roi_type=self.type_id,
            data=(d[0], d[1], d[2]),
            image_size=image_size,
            trace_id=data.get("trace_id", ""),
            metadata=data.get("metadata", {}),
        )

    def validate(self, roi: ROIData) -> list[str]:
        warnings = []
        cx, cy, r = roi.data
        if r <= 0:
            warnings.append(f"Invalid radius: {r} (must be > 0)")
        if roi.image_size:
            w, h = roi.image_size
            if cx < 0 or cy < 0 or cx > w or cy > h:
                warnings.append(f"Center ({cx}, {cy}) outside image ({w}x{h})")
        return warnings

    def bbox(self, roi: ROIData) -> tuple[int, int, int, int]:
        cx, cy, r = roi.data
        return (int(cx - r), int(cy - r), int(2 * r), int(2 * r))


converter_registry.register(CircleConverter())
