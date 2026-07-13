"""矩形 ROI 转换器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ..converter import IROIConverter, converter_registry

if TYPE_CHECKING:
    from ..data import ROIData


class RectangleConverter(IROIConverter):
    """矩形 ROI 转换器。

    data 格式: (x, y, width, height)
    """

    type_id = "rectangle"

    def to_mask(self, roi: ROIData, image_size: tuple[int, int]) -> np.ndarray:
        w, h = image_size
        mask = np.zeros((h, w), dtype=np.uint8)
        x, y, rw, rh = roi.data
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(w, int(x + rw)), min(h, int(y + rh))
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 1
        return mask.astype(bool)

    def to_dict(self, roi: ROIData) -> dict:
        x, y, w, h = roi.data
        return {
            "roi_type": self.type_id,
            "data": [x, y, w, h],
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
            data=(d[0], d[1], d[2], d[3]),
            image_size=image_size,
            trace_id=data.get("trace_id", ""),
            metadata=data.get("metadata", {}),
        )

    def validate(self, roi: ROIData) -> list[str]:
        warnings = []
        x, y, w, h = roi.data
        if w <= 0 or h <= 0:
            warnings.append(f"Invalid rectangle size: {w}x{h} (must be > 0)")
        return warnings

    def bbox(self, roi: ROIData) -> tuple[int, int, int, int]:
        x, y, w, h = roi.data
        return (int(x), int(y), int(w), int(h))


converter_registry.register(RectangleConverter())
